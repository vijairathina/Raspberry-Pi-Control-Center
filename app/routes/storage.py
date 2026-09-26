from flask import Blueprint, render_template, jsonify
from app.auth import login_required, generate_csrf_token
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
