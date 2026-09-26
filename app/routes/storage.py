from flask import Blueprint, render_template, request, jsonify
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.services.storage_manager import StorageManager

storage_bp = Blueprint("storage", __name__)

@storage_bp.route("/storage")
@login_required
def index():
    filesystems = StorageManager.get_mounted_filesystems()
    hardware_disks = StorageManager.get_disk_hardware_info()
    return render_template("storage.html", 
                           filesystems=filesystems, 
                           hardware_disks=hardware_disks, 
                           csrf_token=generate_csrf_token())

@storage_bp.route("/api/storage/filesystems")
@login_required
def api_filesystems():
    filesystems = StorageManager.get_mounted_filesystems()
    return jsonify({"success": True, "data": filesystems})

@storage_bp.route("/api/storage/hardware")
@login_required
def api_hardware():
    disks = StorageManager.get_disk_hardware_info()
    return jsonify({"success": True, "data": disks})

@storage_bp.route("/api/storage/clean", methods=["POST"])
@login_required
def api_clean():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    targets = data.get("targets")
    if not targets:
        targets = ["journal", "apt", "tmp", "cache"]

    result = StorageManager.clean_storage(targets)
    audit_log("Storage Cleanup", f"Reclaimed {result.get('freed_mb')} MB ({', '.join(targets)})", success=result.get("success", False))
    return jsonify(result)

