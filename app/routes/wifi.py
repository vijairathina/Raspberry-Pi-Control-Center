from flask import Blueprint, render_template, request, jsonify
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.services.wifi_manager import WifiManager

wifi_bp = Blueprint("wifi", __name__)

@wifi_bp.route("/wifi")
@login_required
def index():
    curr = WifiManager.get_current_connection()
    saved = WifiManager.get_saved_networks()
    return render_template("wifi.html", current=curr, saved=saved, csrf_token=generate_csrf_token())

@wifi_bp.route("/api/wifi/current")
@login_required
def api_current():
    curr = WifiManager.get_current_connection()
    return jsonify({"success": True, "data": curr})

@wifi_bp.route("/api/wifi/scan")
@login_required
def api_scan():
    scanned = WifiManager.scan_networks()
    return jsonify({"success": True, "data": scanned, "message": f"Found {len(scanned)} Wi-Fi networks"})

@wifi_bp.route("/api/wifi/saved")
@login_required
def api_saved():
    saved = WifiManager.get_saved_networks()
    return jsonify({"success": True, "data": saved})

@wifi_bp.route("/api/wifi/connect", methods=["POST"])
@login_required
def api_connect():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    ssid = data.get("ssid", "").strip()
    password = data.get("password", "")

    if not ssid:
        return jsonify({"success": False, "message": "SSID cannot be empty"}), 400

    success, msg = WifiManager.connect_network(ssid, password=password)
    audit_log("Wi-Fi Connect", f"SSID: {ssid}. Result: {msg}", success=success)

    # Password is never returned in response
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@wifi_bp.route("/api/wifi/disconnect", methods=["POST"])
@login_required
def api_disconnect():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    iface = data.get("interface", "wlan0")
    success, msg = WifiManager.disconnect_network(iface)
    audit_log("Wi-Fi Disconnect", f"Interface: {iface}. Result: {msg}", success=success)
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@wifi_bp.route("/api/wifi/forget", methods=["POST"])
@login_required
def api_forget():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    identifier = data.get("identifier", "").strip() # Name or UUID
    success, msg = WifiManager.forget_network(identifier)
    audit_log("Wi-Fi Forget Network", f"Target: {identifier}. Result: {msg}", success=success)
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@wifi_bp.route("/api/wifi/priority", methods=["POST"])
@login_required
def api_priority():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    identifier = data.get("identifier", "").strip()
    try:
        priority = int(data.get("priority", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid priority number"}), 400

    success, msg = WifiManager.set_priority(identifier, priority)
    audit_log("Network Priority Update", f"Connection: {identifier}, Priority: {priority}", success=success)
    return jsonify({"success": success, "message": msg}), 200 if success else 400
