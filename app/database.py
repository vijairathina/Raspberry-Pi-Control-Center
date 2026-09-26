import sqlite3
import os
import threading
from werkzeug.security import generate_password_hash
from app.config import config

_local = threading.local()

def get_db():
    if not hasattr(_local, "connection") or _local.connection is None:
        db_path = config["database"]["path"]
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        _local.connection = conn
    return _local.connection

def close_db():
    if hasattr(_local, "connection") and _local.connection is not None:
        try:
            _local.connection.close()
        except Exception:
            pass
        _local.connection = None

def init_db():
    conn = get_db()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                success INTEGER DEFAULT 1
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                resolved INTEGER DEFAULT 0,
                resolved_at TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                target TEXT,
                schedule_type TEXT NOT NULL,
                schedule_value TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                last_run TIMESTAMP,
                last_status TEXT
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS automation_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                trigger_metric TEXT NOT NULL,
                trigger_operator TEXT NOT NULL,
                trigger_value REAL NOT NULL,
                action_type TEXT NOT NULL,
                action_target TEXT,
                enabled INTEGER DEFAULT 0,
                last_triggered TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS connectivity_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                gateway_latency REAL,
                dns_latency REAL,
                internet_latency REAL,
                packet_loss REAL,
                status TEXT
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)

        # Seed default admin user if not exists
        admin_user = config["defaults"].get("admin_username", "admin")
        default_pw = config["defaults"].get("admin_default_password", "admin")
        cursor = conn.execute("SELECT id FROM users WHERE username = ?", (admin_user,))
        if not cursor.fetchone():
            pw_hash = generate_password_hash(default_pw)
            conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (admin_user, pw_hash))

        # Seed default settings if not exists
        for k, v in config["defaults"].items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))
