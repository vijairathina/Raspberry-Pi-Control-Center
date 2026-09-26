from flask import Blueprint, render_template, request, jsonify
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.services.docker_manager import DockerManager

docker_bp = Blueprint("docker", __name__)

@docker_bp.route("/docker")
@login_required
def index():
    status = DockerManager.get_containers()
    return render_template("docker.html", docker=status, csrf_token=generate_csrf_token())

@docker_bp.route("/api/docker/status")
@login_required
def api_status():
    status = DockerManager.get_containers()
    return jsonify({"success": True, "data": status})

@docker_bp.route("/api/docker/control", methods=["POST"])
@login_required
def api_control():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    container_id = data.get("id", "").strip()
    action = data.get("action", "").strip()

    success, msg = DockerManager.control_container(container_id, action)
    audit_log(f"Docker Container {action.upper()}", f"ID: {container_id}. Result: {msg}", success=success)

    return jsonify({"success": success, "message": msg}), 200 if success else 400

@docker_bp.route("/api/docker/logs")
@login_required
def api_logs():
    container_id = request.args.get("id", "").strip()
    lines = int(request.args.get("lines", 100))
    logs = DockerManager.get_container_logs(container_id, lines=lines)
    return jsonify({"success": True, "data": logs})
