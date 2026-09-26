from flask import Blueprint, render_template, request, jsonify
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.services.automation_engine import AutomationEngine
from app.services.audit_logger import AuditLogger

automation_bp = Blueprint("automation", __name__)

@automation_bp.route("/automation")
@login_required
def index():
    rules = AutomationEngine.list_rules()
    alerts = AuditLogger.get_alerts(limit=50)
    return render_template("automation.html", rules=rules, alerts=alerts, csrf_token=generate_csrf_token())

@automation_bp.route("/api/automation/rules")
@login_required
def api_rules():
    rules = AutomationEngine.list_rules()
    return jsonify({"success": True, "data": rules})

@automation_bp.route("/api/automation/add", methods=["POST"])
@login_required
def api_add():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    name = data.get("name", "").strip()
    metric = data.get("metric", "").strip()
    op = data.get("operator", ">").strip()
    try:
        val = float(data.get("value", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid threshold value"}), 400

    action_type = data.get("action_type", "create_alert").strip()
    action_target = data.get("action_target", "").strip()

    success, msg = AutomationEngine.add_rule(name, metric, op, val, action_type, action_target)
    audit_log("Add Automation Rule", f"Rule: {name} (IF {metric} {op} {val} THEN {action_type})", success=success)

    return jsonify({"success": success, "message": msg}), 200 if success else 400

@automation_bp.route("/api/automation/toggle", methods=["POST"])
@login_required
def api_toggle():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    rule_id = int(data.get("id", 0))
    enabled = bool(data.get("enabled", True))

    success = AutomationEngine.toggle_rule(rule_id, enabled)
    return jsonify({"success": success, "message": f"Rule {'enabled' if enabled else 'disabled'}"})

@automation_bp.route("/api/automation/delete", methods=["POST"])
@login_required
def api_delete():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    rule_id = int(data.get("id", 0))

    success = AutomationEngine.delete_rule(rule_id)
    audit_log("Delete Automation Rule", f"Rule ID: {rule_id}", success=success)
    return jsonify({"success": success, "message": "Rule deleted"})

@automation_bp.route("/api/automation/alerts")
@login_required
def api_alerts():
    alerts = AuditLogger.get_alerts(limit=50)
    return jsonify({"success": True, "data": alerts})

@automation_bp.route("/api/automation/alerts/resolve", methods=["POST"])
@login_required
def api_resolve_alert():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    alert_id = int(data.get("id", 0))

    success = AuditLogger.resolve_alert(alert_id)
    return jsonify({"success": success, "message": "Alert marked resolved"})
