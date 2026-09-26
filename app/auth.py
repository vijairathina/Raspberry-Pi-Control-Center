import time
import secrets
from functools import wraps
from collections import defaultdict
from flask import session, request, redirect, url_for, jsonify, current_app, abort
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import get_db

# In-memory sliding window rate limiter for login attempts
# IP -> list of timestamps
_login_attempts = defaultdict(list)
RATE_LIMIT_WINDOW = 60 # seconds
MAX_ATTEMPTS = 5

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    attempts = [t for t in _login_attempts[ip] if now - t < RATE_LIMIT_WINDOW]
    _login_attempts[ip] = attempts
    return len(attempts) >= MAX_ATTEMPTS

def record_login_attempt(ip: str):
    _login_attempts[ip].append(time.time())

def clear_login_attempts(ip: str):
    if ip in _login_attempts:
        del _login_attempts[ip]

def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(24)
    return session["_csrf_token"]

def validate_csrf_token():
    token = request.headers.get("X-CSRFToken") or request.form.get("csrf_token")
    expected = session.get("_csrf_token")
    if not token or not expected or not secrets.compare_digest(token, expected):
        return False
    return True

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Authentication required"}), 401
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def audit_log(action: str, details: str = "", success: bool = True):
    try:
        username = session.get("username", "system")
        ip = request.remote_addr or "127.0.0.1"
        conn = get_db()
        with conn:
            conn.execute(
                "INSERT INTO audit_logs (username, action, details, ip_address, success) VALUES (?, ?, ?, ?, ?)",
                (username, action, details, ip, 1 if success else 0)
            )
    except Exception as e:
        print(f"Error writing audit log: {e}")
