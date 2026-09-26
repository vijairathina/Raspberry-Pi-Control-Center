from flask import Blueprint, render_template, request, jsonify
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.services.scheduler import TaskScheduler

tasks_bp = Blueprint("tasks", __name__)

@tasks_bp.route("/tasks")
@login_required
def index():
    tasks = TaskScheduler.list_tasks()
    return render_template("tasks.html", tasks=tasks, csrf_token=generate_csrf_token())

@tasks_bp.route("/api/tasks/list")
@login_required
def api_list():
    tasks = TaskScheduler.list_tasks()
    return jsonify({"success": True, "data": tasks})

@tasks_bp.route("/api/tasks/add", methods=["POST"])
@login_required
def api_add():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    name = data.get("name", "").strip()
    task_type = data.get("task_type", "").strip()
    target = data.get("target", "").strip()
    schedule_type = data.get("schedule_type", "daily").strip()
    schedule_value = data.get("schedule_value", "02:00").strip()

    success, msg = TaskScheduler.add_task(name, task_type, target, schedule_type, schedule_value)
    audit_log("Add Scheduled Task", f"Task: {name} ({task_type}) at {schedule_value}", success=success)

    return jsonify({"success": success, "message": msg}), 200 if success else 400

@tasks_bp.route("/api/tasks/delete", methods=["POST"])
@login_required
def api_delete():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    try:
        task_id = int(data.get("id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    success = TaskScheduler.delete_task(task_id)
    audit_log("Delete Scheduled Task", f"Task ID: {task_id}", success=success)
    return jsonify({"success": success, "message": "Task deleted"})

@tasks_bp.route("/api/tasks/toggle", methods=["POST"])
@login_required
def api_toggle():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    task_id = int(data.get("id", 0))
    enabled = bool(data.get("enabled", True))

    success = TaskScheduler.toggle_task(task_id, enabled)
    return jsonify({"success": success, "message": f"Task {'enabled' if enabled else 'disabled'}"})
