from flask import Blueprint, render_template, request, jsonify
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.services.processes_manager import ProcessManager

processes_bp = Blueprint("processes", __name__)

@processes_bp.route("/processes")
@login_required
def index():
    procs = ProcessManager.list_processes(sort_by="cpu")
    return render_template("processes.html", processes=procs, csrf_token=generate_csrf_token())

@processes_bp.route("/api/processes/list")
@login_required
def api_list():
    sort_by = request.args.get("sort_by", "cpu")
    reverse = request.args.get("reverse", "true").lower() == "true"
    search = request.args.get("q", "")
    procs = ProcessManager.list_processes(sort_by=sort_by, reverse=reverse, search=search)
    return jsonify({
        "success": True,
        "data": procs,
        "message": f"Loaded {len(procs)} processes"
    })

@processes_bp.route("/api/processes/kill", methods=["POST"])
@login_required
def api_kill():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    try:
        pid = int(data.get("pid", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid PID"}), 400

    force = bool(data.get("force", False))
    success, msg = ProcessManager.kill_process(pid, force=force)
    audit_log(f"Process {'SIGKILL' if force else 'SIGTERM'}", f"PID: {pid}. Result: {msg}", success=success)

    return jsonify({
        "success": success,
        "message": msg
    }), 200 if success else 400
