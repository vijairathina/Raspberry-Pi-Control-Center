from flask import Blueprint, render_template, request, jsonify
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.services.hardware_manager import HardwareManager
from app.services.gpio_manager import GPIOManager
from app.services.camera_manager import CameraManager

hardware_bp = Blueprint("hardware", __name__)

@hardware_bp.route("/hardware")
@login_required
def index():
    overview = HardwareManager.get_hardware_overview()
    pins = GPIOManager.get_pins()
    camera = CameraManager.detect_camera()
    return render_template("hardware.html", 
                           overview=overview, 
                           pins=pins, 
                           camera=camera, 
                           csrf_token=generate_csrf_token())

@hardware_bp.route("/api/hardware/overview")
@login_required
def api_overview():
    overview = HardwareManager.get_hardware_overview()
    return jsonify({"success": True, "data": overview})

@hardware_bp.route("/api/hardware/gpio")
@login_required
def api_gpio():
    pins = GPIOManager.get_pins()
    return jsonify({"success": True, "data": pins})

@hardware_bp.route("/api/hardware/gpio/mode", methods=["POST"])
@login_required
def api_gpio_mode():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    try:
        gpio_num = int(data.get("gpio", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid GPIO number"}), 400

    mode = data.get("mode", "").strip().upper()
    success, msg = GPIOManager.set_pin_mode(gpio_num, mode)
    audit_log("GPIO Mode Change", f"GPIO: {gpio_num}, Mode: {mode}. Result: {msg}", success=success)

    return jsonify({"success": success, "message": msg}), 200 if success else 400

@hardware_bp.route("/api/hardware/gpio/state", methods=["POST"])
@login_required
def api_gpio_state():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    try:
        gpio_num = int(data.get("gpio", 0))
        state = int(data.get("state", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid GPIO parameters"}), 400

    success, msg = GPIOManager.set_pin_state(gpio_num, state)
    audit_log("GPIO Output Toggle", f"GPIO: {gpio_num}, State: {'HIGH' if state == 1 else 'LOW'}. Result: {msg}", success=success)

    return jsonify({"success": success, "message": msg}), 200 if success else 400

@hardware_bp.route("/api/hardware/camera")
@login_required
def api_camera():
    cam = CameraManager.detect_camera()
    return jsonify({"success": True, "data": cam})

@hardware_bp.route("/api/hardware/camera/preview")
@login_required
def api_camera_preview():
    preview = CameraManager.capture_preview()
    return jsonify(preview)
