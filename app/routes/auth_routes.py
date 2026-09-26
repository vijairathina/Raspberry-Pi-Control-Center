from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import get_db
from app.auth import is_rate_limited, record_login_attempt, clear_login_attempts, generate_csrf_token, validate_csrf_token, audit_log, login_required

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))

    ip = request.remote_addr or "127.0.0.1"

    if request.method == "POST":
        if is_rate_limited(ip):
            flash("Too many failed attempts. Please wait 60 seconds.", "danger")
            return render_template("login.html", csrf_token=generate_csrf_token()), 429

        # Validate CSRF
        if not validate_csrf_token():
            flash("Invalid or expired session security token.", "danger")
            return render_template("login.html", csrf_token=generate_csrf_token()), 400

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password_hash"], password):
            clear_login_attempts(ip)
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["_csrf_token"] = generate_csrf_token()

            with conn:
                conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))

            audit_log("User Login", f"Successful login for user '{username}'", success=True)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))
        else:
            record_login_attempt(ip)
            audit_log("User Login Failed", f"Failed attempt for username '{username}'", success=False)
            flash("Invalid username or password.", "danger")

    return render_template("login.html", csrf_token=generate_csrf_token())

@auth_bp.route("/logout")
def logout():
    username = session.get("username", "user")
    audit_log("User Logout", f"User '{username}' logged out", success=True)
    session.clear()
    return redirect(url_for("auth.login"))

@auth_bp.route("/api/auth/change-password", methods=["POST"])
@login_required
def change_password():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    old_pw = data.get("current_password", "")
    new_pw = data.get("new_password", "")

    if len(new_pw) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters"}), 400

    conn = get_db()
    cursor = conn.execute("SELECT password_hash FROM users WHERE id = ?", (session["user_id"],))
    user = cursor.fetchone()

    if not user or not check_password_hash(user["password_hash"], old_pw):
        return jsonify({"success": False, "message": "Incorrect current password"}), 400

    new_hash = generate_password_hash(new_pw)
    with conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, session["user_id"]))

    audit_log("Password Change", "Admin password changed successfully", success=True)
    return jsonify({"success": True, "message": "Password updated successfully"})
