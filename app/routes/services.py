from flask import Blueprint, render_template, request, jsonify, Response
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.services.service_manager import ServiceManager

services_bp = Blueprint("services", __name__)

@services_bp.route("/services")
@login_required
def index():
    services = ServiceManager.list_services()
    return render_template("services.html", services=services, csrf_token=generate_csrf_token())

@services_bp.route("/service-logs")
@login_required
def service_logs():
    service_name = request.args.get("unit", "ssh.service")
    return render_template("service_logs.html", selected_unit=service_name, csrf_token=generate_csrf_token())

@services_bp.route("/api/services/list")
@login_required
def api_list():
    q = request.args.get("q", "")
    services = ServiceManager.list_services(search_query=q)
    return jsonify({
        "success": True,
        "data": services,
        "message": f"Found {len(services)} services"
    })

@services_bp.route("/api/services/control", methods=["POST"])
@login_required
def api_control():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    name = data.get("name", "").strip()
    action = data.get("action", "").strip()

    if not name or not action:
        return jsonify({"success": False, "message": "Missing service name or action"}), 400

    success, message = ServiceManager.control_service(name, action)
    audit_log(f"Service Control: {action}", f"Target: {name}. Result: {message}", success=success)

    return jsonify({
        "success": success,
        "message": message
    }), 200 if success else 400

@services_bp.route("/api/services/logs")
@login_required
def api_logs():
    name = request.args.get("unit", "").strip()
    lines = int(request.args.get("lines", 50))
    error_only = request.args.get("error_only", "false").lower() == "true"
    search = request.args.get("search", "")

    result = ServiceManager.get_service_logs(name, lines=lines, error_only=error_only, search=search)
    return jsonify(result)

@services_bp.route("/api/services/logs/download")
@login_required
def api_download_logs():
    name = request.args.get("unit", "service").strip()
    lines = int(request.args.get("lines", 500))
    result = ServiceManager.get_service_logs(name, lines=lines)
    log_content = result.get("logs", "")

    return Response(
        log_content,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment;filename={name}-journal.log"}
    )
