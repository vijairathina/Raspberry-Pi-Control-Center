from flask import Blueprint, render_template, request, jsonify
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.services.bluetooth_manager import BluetoothManager

bluetooth_bp = Blueprint("bluetooth", __name__)

@bluetooth_bp.route("/bluetooth")
@login_required
def index():
    status = BluetoothManager.get_status()
    return render_template("bluetooth.html", bt=status, csrf_token=generate_csrf_token())

@bluetooth_bp.route("/api/bluetooth/status")
@login_required
def api_status():
    status = BluetoothManager.get_status()
    return jsonify({"success": True, "data": status})

@bluetooth_bp.route("/api/bluetooth/power", methods=["POST"])
@login_required
def api_power():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    enable = bool(data.get("enable", True))
    success, msg = BluetoothManager.set_power(enable)
    audit_log(f"Bluetooth Power {'ON' if enable else 'OFF'}", msg, success=success)

    return jsonify({"success": success, "message": msg}), 200 if success else 400

@bluetooth_bp.route("/api/bluetooth/restart", methods=["POST"])
@login_required
def api_restart():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    success, msg = BluetoothManager.restart_bluetooth()
    audit_log("Bluetooth Restart", msg, success=success)
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@bluetooth_bp.route("/api/bluetooth/scan")
@login_required
def api_scan():
    devices = BluetoothManager.scan_devices(duration_seconds=5)
    return jsonify({"success": True, "data": devices, "message": f"Found {len(devices)} devices"})

@bluetooth_bp.route("/api/bluetooth/pair", methods=["POST"])
@login_required
def api_pair():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    mac = data.get("mac", "").strip()
    success, msg = BluetoothManager.pair_device(mac)
    audit_log("Bluetooth Pair", f"MAC: {mac}. Result: {msg}", success=success)
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@bluetooth_bp.route("/api/bluetooth/remove", methods=["POST"])
@login_required
def api_remove():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    mac = data.get("mac", "").strip()
    success, msg = BluetoothManager.remove_device(mac)
    audit_log("Bluetooth Remove Pairing", f"MAC: {mac}. Result: {msg}", success=success)
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@bluetooth_bp.route("/api/bluetooth/connect", methods=["POST"])
@login_required
def api_connect():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    mac = data.get("mac", "").strip()
    connect = bool(data.get("connect", True))
    success, msg = BluetoothManager.connect_device(mac, connect=connect)
    audit_log(f"Bluetooth {'Connect' if connect else 'Disconnect'}", f"MAC: {mac}. Result: {msg}", success=success)
    return jsonify({"success": success, "message": msg}), 200 if success else 400
