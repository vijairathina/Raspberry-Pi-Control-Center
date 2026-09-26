import os
from datetime import datetime
from app.database import get_db

APP_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "app.log")

class AuditLogger:
    @staticmethod
    def get_audit_logs(limit: int = 100, search: str = "") -> list[dict]:
        conn = get_db()
        if search:
            q = f"%{search}%"
            cursor = conn.execute("""
                SELECT id, timestamp, username, action, details, ip_address, success
                FROM audit_logs
                WHERE username LIKE ? OR action LIKE ? OR details LIKE ?
                ORDER BY id DESC LIMIT ?
            """, (q, q, q, limit))
        else:
            cursor = conn.execute("""
                SELECT id, timestamp, username, action, details, ip_address, success
                FROM audit_logs
                ORDER BY id DESC LIMIT ?
            """, (limit,))
        return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def get_alerts(resolved: bool | None = None, limit: int = 100) -> list[dict]:
        conn = get_db()
        if resolved is None:
            cursor = conn.execute("""
                SELECT id, timestamp, type, message, severity, resolved, resolved_at
                FROM alerts ORDER BY id DESC LIMIT ?
            """, (limit,))
        else:
            cursor = conn.execute("""
                SELECT id, timestamp, type, message, severity, resolved, resolved_at
                FROM alerts WHERE resolved = ? ORDER BY id DESC LIMIT ?
            """, (1 if resolved else 0, limit))
        return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def resolve_alert(alert_id: int) -> bool:
        conn = get_db()
        with conn:
            conn.execute("""
                UPDATE alerts SET resolved = 1, resolved_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (alert_id,))
        return True

    @staticmethod
    def log_app_event(level: str, message: str):
        # Ensure data dir exists
        os.makedirs(os.path.dirname(APP_LOG_FILE), exist_ok=True)
        # Sanitize sensitive patterns
        sanitized = message.replace("password=", "password=***").replace("passwd=", "passwd=***")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level.upper()}] {sanitized}\n"
        try:
            with open(APP_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass

    @staticmethod
    def read_app_logs(lines: int = 100, level_filter: str = "") -> list[str]:
        if not os.path.exists(APP_LOG_FILE):
            return ["Application log initialized. No entries yet."]
        try:
            with open(APP_LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
            
            if level_filter:
                target = f"[{level_filter.upper()}]"
                all_lines = [l for l in all_lines if target in l]

            return all_lines[-lines:]
        except Exception as e:
            return [f"Error reading app log: {e}"]

    @staticmethod
    def clear_app_logs():
        try:
            if os.path.exists(APP_LOG_FILE):
                with open(APP_LOG_FILE, "w", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Log cleared by administrator.\n")
            return True
        except Exception:
            return False
