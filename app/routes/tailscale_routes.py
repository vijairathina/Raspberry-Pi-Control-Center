from flask import Blueprint, render_template, request, jsonify
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.services.tailscale_manager import TailscaleManager

tailscale_bp = Blueprint("tailscale", __name__)

@tailscale_bp.route("/tailscale")
@login_required
def index():
    status = TailscaleManager.get_status()
    return render_template("tailscale.html", tailscale=status, csrf_token=generate_csrf_token())

@tailscale_bp.route("/api/tailscale/status")
@login_required
def api_status():
    status = TailscaleManager.get_status()
    return jsonify({"success": True, "data": status})

@tailscale_bp.route("/api/tailscale/control", methods=["POST"])
@login_required
def api_control():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    action = data.get("action", "").strip()

    success, msg = TailscaleManager.control_tailscale(action)
    audit_log(f"Tailscale {action.upper()}", msg, success=success)

    return jsonify({"success": success, "message": msg}), 200 if success else 400
