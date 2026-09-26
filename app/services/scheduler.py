import time
import threading
from datetime import datetime
from app.database import get_db
from app.services.service_manager import ServiceManager
from app.services.system_service import SystemService
from app.services.bluetooth_manager import BluetoothManager
from app.services.wifi_manager import WifiManager

_scheduler_running = False
_scheduler_thread = None

class TaskScheduler:
    @staticmethod
    def start_background_loop():
        global _scheduler_running, _scheduler_thread
        if _scheduler_running:
            return
        _scheduler_running = True
        _scheduler_thread = threading.Thread(target=TaskScheduler._loop, daemon=True)
        _scheduler_thread.start()

    @staticmethod
    def _loop():
        while _scheduler_running:
            try:
                TaskScheduler.check_and_run_tasks()
            except Exception as e:
                print(f"Scheduler loop error: {e}")
            time.sleep(30) # Check every 30 seconds

    @staticmethod
    def check_and_run_tasks():
        conn = get_db()
        cursor = conn.execute("SELECT * FROM scheduled_tasks WHERE enabled = 1")
        tasks = cursor.fetchall()
        now = datetime.now()
        current_hm = now.strftime("%H:%M")
        current_day = now.strftime("%a")

        for t in tasks:
            task_id = t["id"]
            name = t["name"]
            task_type = t["task_type"]
            target = t["target"]
            schedule_type = t["schedule_type"] # 'daily', 'weekly', 'interval'
            schedule_value = t["schedule_value"] # e.g. '02:00', 'Sun 04:00', or '60' (minutes)

            should_run = False
            last_run_str = t["last_run"]
            
            if schedule_type == "daily":
                # Check if current time matches HH:MM and hasn't run today
                if current_hm == schedule_value:
                    if not last_run_str or not last_run_str.startswith(now.strftime("%Y-%m-%d")):
                        should_run = True
            elif schedule_type == "weekly":
                # Check day and HH:MM
                parts = schedule_value.split()
                if len(parts) == 2 and parts[0] == current_day and parts[1] == current_hm:
                    if not last_run_str or not last_run_str.startswith(now.strftime("%Y-%m-%d")):
                        should_run = True

            if should_run:
                status_msg = TaskScheduler.execute_task_action(task_type, target)
                with conn:
                    conn.execute("""
                        UPDATE scheduled_tasks 
                        SET last_run = CURRENT_TIMESTAMP, last_status = ? 
                        WHERE id = ?
                    """, (status_msg, task_id))
                    conn.execute("""
                        INSERT INTO audit_logs (username, action, details, ip_address, success)
                        VALUES ('scheduler', ?, ?, '127.0.0.1', 1)
                    """, (f"Scheduled task executed: {name}", status_msg))

    @staticmethod
    def execute_task_action(task_type: str, target: str) -> str:
        try:
            if task_type == "restart_service" and target:
                success, msg = ServiceManager.control_service(target, "restart")
                return msg
            elif task_type == "start_service" and target:
                success, msg = ServiceManager.control_service(target, "start")
                return msg
            elif task_type == "stop_service" and target:
                success, msg = ServiceManager.control_service(target, "stop")
                return msg
            elif task_type == "reboot":
                success, msg = SystemService.reboot()
                return msg
            elif task_type == "maintenance":
                # Run safe cleanup / updates check
                SystemService.check_updates()
                return "Completed routine maintenance and package update check"
            elif task_type == "bluetooth_toggle":
                turn_on = (target.lower() == "on")
                success, msg = BluetoothManager.set_power(turn_on)
                return msg
            elif task_type == "wifi_reconnect":
                WifiManager.connect_network(target)
                return f"Reconnected Wi-Fi ({target})"
            return f"Unknown task action: {task_type}"
        except Exception as e:
            return f"Task execution failed: {e}"

    @staticmethod
    def list_tasks() -> list[dict]:
        conn = get_db()
        cursor = conn.execute("SELECT * FROM scheduled_tasks ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def add_task(name: str, task_type: str, target: str, schedule_type: str, schedule_value: str) -> tuple[bool, str]:
        allowed_types = {"restart_service", "start_service", "stop_service", "reboot", "maintenance", "bluetooth_toggle", "wifi_reconnect"}
        if task_type not in allowed_types:
            return False, "Invalid task type"

        if not name:
            return False, "Task name cannot be empty"

        conn = get_db()
        with conn:
            conn.execute("""
                INSERT INTO scheduled_tasks (name, task_type, target, schedule_type, schedule_value, enabled)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (name, task_type, target, schedule_type, schedule_value))

        return True, "Task scheduled successfully"

    @staticmethod
    def delete_task(task_id: int) -> bool:
        conn = get_db()
        with conn:
            conn.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
        return True

    @staticmethod
    def toggle_task(task_id: int, enabled: bool) -> bool:
        conn = get_db()
        with conn:
            conn.execute("UPDATE scheduled_tasks SET enabled = ? WHERE id = ?", (1 if enabled else 0, task_id))
        return True
