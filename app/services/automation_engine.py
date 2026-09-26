import time
import threading
from datetime import datetime
import psutil
from app.database import get_db
from app.services.system_service import SystemService
from app.services.service_manager import ServiceManager
from app.services.wifi_manager import WifiManager
from app.services.diagnostics import DiagnosticsService

_engine_running = False
_engine_thread = None

class AutomationEngine:
    @staticmethod
    def start_background_loop():
        global _engine_running, _engine_thread
        if _engine_running:
            return
        _engine_running = True
        _engine_thread = threading.Thread(target=AutomationEngine._loop, daemon=True)
        _engine_thread.start()

    @staticmethod
    def _loop():
        while _engine_running:
            try:
                AutomationEngine.evaluate_rules()
            except Exception as e:
                print(f"Automation engine loop error: {e}")
            time.sleep(15) # Check every 15s

    @staticmethod
    def evaluate_rules():
        conn = get_db()
        cursor = conn.execute("SELECT * FROM automation_rules WHERE enabled = 1")
        rules = cursor.fetchall()
        if not rules:
            return

        # Fetch current system telemetry
        temp = SystemService.get_cpu_temp()
        cpu_pct = psutil.cpu_percent(interval=None)
        ram_pct = psutil.virtual_memory().percent
        disk_pct = psutil.disk_usage("/" if psutil.WINDOWS is False else "C:\\").percent

        wifi_conn = WifiManager.get_current_connection()
        wifi_connected = wifi_conn.get("connected", False) and wifi_conn.get("ssid") != "Disconnected"

        metrics = {
            "cpu_temp": temp,
            "cpu_percent": cpu_pct,
            "ram_percent": ram_pct,
            "disk_percent": disk_pct,
            "wifi_disconnected": 1 if not wifi_connected else 0,
        }

        for r in rules:
            rule_id = r["id"]
            metric = r["trigger_metric"]
            op = r["trigger_operator"]
            target_val = r["trigger_value"]
            action_type = r["action_type"]
            action_target = r["action_target"]

            current_val = metrics.get(metric)
            if current_val is None:
                continue

            triggered = False
            if op == ">" and current_val > target_val:
                triggered = True
            elif op == "<" and current_val < target_val:
                triggered = True
            elif op == "==" and current_val == target_val:
                triggered = True

            if triggered:
                # Cooldown check: do not trigger more than once every 5 minutes per rule
                last_trig = r["last_triggered"]
                if last_trig:
                    try:
                        last_dt = datetime.strptime(last_trig, "%Y-%m-%d %H:%M:%S")
                        if (datetime.now() - last_dt).total_seconds() < 300:
                            continue
                    except Exception:
                        pass

                # Execute action
                AutomationEngine._trigger_action(r["name"], action_type, action_target, f"{metric} reached {current_val}")
                with conn:
                    conn.execute("UPDATE automation_rules SET last_triggered = CURRENT_TIMESTAMP WHERE id = ?", (rule_id,))

    @staticmethod
    def _trigger_action(rule_name: str, action_type: str, action_target: str, reason: str):
        conn = get_db()
        with conn:
            if action_type == "create_alert":
                conn.execute("""
                    INSERT INTO alerts (type, message, severity)
                    VALUES (?, ?, 'warning')
                """, (rule_name, f"Automation triggered: {reason}"))
            elif action_type == "restart_service" and action_target:
                ServiceManager.control_service(action_target, "restart")
                conn.execute("""
                    INSERT INTO alerts (type, message, severity)
                    VALUES (?, ?, 'normal')
                """, (rule_name, f"Automatically restarted service {action_target} due to: {reason}"))
            elif action_type == "reconnect_wifi":
                WifiManager.connect_network(action_target or "Home WiFi")
                conn.execute("""
                    INSERT INTO alerts (type, message, severity)
                    VALUES (?, ?, 'normal')
                """, (rule_name, f"Wi-Fi reconnect initiated due to: {reason}"))

    @staticmethod
    def list_rules() -> list[dict]:
        conn = get_db()
        cursor = conn.execute("SELECT * FROM automation_rules ORDER BY id ASC")
        return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def add_rule(name: str, metric: str, op: str, value: float, action_type: str, action_target: str) -> tuple[bool, str]:
        allowed_metrics = {"cpu_temp", "cpu_percent", "ram_percent", "disk_percent", "wifi_disconnected"}
        if metric not in allowed_metrics:
            return False, "Invalid trigger metric"

        conn = get_db()
        with conn:
            conn.execute("""
                INSERT INTO automation_rules (name, trigger_metric, trigger_operator, trigger_value, action_type, action_target, enabled)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (name, metric, op, value, action_type, action_target))
        return True, "Automation rule created"

    @staticmethod
    def toggle_rule(rule_id: int, enabled: bool) -> bool:
        conn = get_db()
        with conn:
            conn.execute("UPDATE automation_rules SET enabled = ? WHERE id = ?", (1 if enabled else 0, rule_id))
        return True

    @staticmethod
    def delete_rule(rule_id: int) -> bool:
        conn = get_db()
        with conn:
            conn.execute("DELETE FROM automation_rules WHERE id = ?", (rule_id,))
        return True
