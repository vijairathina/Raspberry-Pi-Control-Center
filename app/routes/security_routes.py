import json
from flask import Blueprint, render_template, request, jsonify, Response
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.database import get_db
from app.services.audit_logger import AuditLogger
from app.services.system_service import SystemService
from app.config import config

security_bp = Blueprint("security", __name__)

@security_bp.route("/security")
@login_required
def index():
    audit_logs = AuditLogger.get_audit_logs(limit=50)
    return render_template("security.html", audit_logs=audit_logs, csrf_token=generate_csrf_token())

@security_bp.route("/settings")
@login_required
def settings():
    conn = get_db()
    cursor = conn.execute("SELECT key, value FROM settings")
    settings_dict = {row["key"]: row["value"] for row in cursor.fetchall()}
    updates = SystemService.check_updates()
    return render_template("settings.html", 
                           settings=settings_dict, 
                           updates=updates,
                           ha_config=config.get("home_assistant", {}),
                           net_config=config.get("internet_monitor", {}),
                           csrf_token=generate_csrf_token())

@security_bp.route("/api/ha/test", methods=["POST"])
@login_required
def api_test_ha():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    from app.services.ha_service import HomeAssistantService
    success, msg = HomeAssistantService.test_connection()
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@security_bp.route("/api/ha/send-test", methods=["POST"])
@login_required
def api_send_ha_test():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    from app.services.ha_service import HomeAssistantService
    success, msg = HomeAssistantService.send_notification(
        "Raspberry Pi Control Center",
        "Test notification from your Raspberry Pi Control Center console."
    )
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@security_bp.route("/api/internet/check-now", methods=["POST"])
@login_required
def api_check_internet_now():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    from app.services.diagnostics import DiagnosticsService
    res = DiagnosticsService.check_internet_resilient()
    return jsonify({"success": True, "data": res, "message": f"Status: {res['status'].upper()} via {res['host']} in {res['attempts']} attempt(s)"})

@security_bp.route("/logs")
@login_required
def app_logs_view():
    lines = AuditLogger.read_app_logs(lines=100)
    return render_template("logs.html", initial_logs="".join(lines), csrf_token=generate_csrf_token())

@security_bp.route("/api/security/audit-logs")
@login_required
def api_audit_logs():
    q = request.args.get("q", "")
    limit = int(request.args.get("limit", 100))
    logs = AuditLogger.get_audit_logs(limit=limit, search=q)
    return jsonify({"success": True, "data": logs})

@security_bp.route("/api/settings/update", methods=["POST"])
@login_required
def api_update_settings():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    conn = get_db()
    with conn:
        for k, v in data.items():
            if k in ("csrf_token", "_csrf_token"):
                continue
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))

    audit_log("Settings Update", "Application configuration thresholds updated", success=True)
    return jsonify({"success": True, "message": "Settings saved successfully"})

@security_bp.route("/api/settings/export")
@login_required
def api_export_settings():
    conn = get_db()
    cursor = conn.execute("SELECT key, value FROM settings")
    settings_dict = {row["key"]: row["value"] for row in cursor.fetchall()}

    cursor = conn.execute("SELECT name, trigger_metric, trigger_operator, trigger_value, action_type, action_target, enabled FROM automation_rules")
    rules = [dict(r) for r in cursor.fetchall()]

    cursor = conn.execute("SELECT name, task_type, target, schedule_type, schedule_value, enabled FROM scheduled_tasks")
    tasks = [dict(r) for r in cursor.fetchall()]

    backup_payload = {
        "version": "1.0",
        "exported_at": SystemService.get_system_summary()["datetime"],
        "settings": settings_dict,
        "automation_rules": rules,
        "scheduled_tasks": tasks
    }

    return Response(
        json.dumps(backup_payload, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=rpi-control-backup.json"}
    )

@security_bp.route("/api/settings/import", methods=["POST"])
@login_required
def api_import_settings():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    if "backup_file" not in request.files:
        return jsonify({"success": False, "message": "No backup file uploaded"}), 400

    f = request.files["backup_file"]
    try:
        data = json.load(f)
    except Exception as e:
        return jsonify({"success": False, "message": f"Malformed JSON: {e}"}), 400

    # Validate structure
    if "settings" not in data:
        return jsonify({"success": False, "message": "Invalid backup schema: missing 'settings'"}), 400

    conn = get_db()
    with conn:
        for k, v in data.get("settings", {}).items():
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))

    audit_log("Settings Imported", "Configuration backup restored", success=True)
    return jsonify({"success": True, "message": "Configuration successfully imported"})

@security_bp.route("/api/logs/app")
@login_required
def api_get_app_logs():
    level = request.args.get("level", "")
    lines = int(request.args.get("lines", 100))
    content = AuditLogger.read_app_logs(lines=lines, level_filter=level)
    return jsonify({"success": True, "data": "".join(content)})

@security_bp.route("/api/logs/clear", methods=["POST"])
@login_required
def api_clear_app_logs():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    AuditLogger.clear_app_logs()
    audit_log("Application Logs Cleared", "Administrator truncated app log file", success=True)
    return jsonify({"success": True, "message": "Application logs cleared"})

@security_bp.route("/api/system/reboot", methods=["POST"])
@login_required
def api_system_reboot():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    audit_log("System Reboot", "Reboot command dispatched", success=True)
    success, msg = SystemService.reboot()
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@security_bp.route("/api/system/shutdown", methods=["POST"])
@login_required
def api_system_shutdown():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    audit_log("System Shutdown", "Shutdown command dispatched", success=True)
    success, msg = SystemService.shutdown()
    return jsonify({"success": success, "message": msg}), 200 if success else 400
