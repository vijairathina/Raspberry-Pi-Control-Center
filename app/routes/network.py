from flask import Blueprint, render_template, request, jsonify
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.services.network_manager import NetworkManager

network_bp = Blueprint("network", __name__)

@network_bp.route("/network")
@login_required
def index():
    interfaces = NetworkManager.get_interfaces()
    client_ip = request.remote_addr or "127.0.0.1"
    ports = NetworkManager.get_listening_ports()
    firewall = NetworkManager.get_firewall_status()
    return render_template("network.html", 
                           interfaces=interfaces, 
                           client_ip=client_ip, 
                           ports=ports, 
                           firewall=firewall, 
                           csrf_token=generate_csrf_token())

@network_bp.route("/api/network/interfaces")
@login_required
def api_interfaces():
    client_ip = request.remote_addr or "127.0.0.1"
    interfaces = NetworkManager.get_interfaces()
    # Annotate with client current connection flag
    for iface in interfaces:
        iface["is_current_client"] = NetworkManager.is_client_on_interface(iface["name"], client_ip)
    return jsonify({"success": True, "data": interfaces, "client_ip": client_ip})

@network_bp.route("/api/network/interface/state", methods=["POST"])
@login_required
def api_interface_state():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    iface = data.get("interface", "").strip()
    state = data.get("state", "").strip().lower()

    if not iface or state not in ("up", "down"):
        return jsonify({"success": False, "message": "Invalid interface or state"}), 400

    client_ip = request.remote_addr or "127.0.0.1"
    if state == "down" and NetworkManager.is_client_on_interface(iface, client_ip):
        audit_log("Network Interface Warning", f"Attempted to shut down active connection interface: {iface}", success=False)

    success, msg = NetworkManager.set_interface_state(iface, state)
    audit_log(f"Interface {state.upper()}", f"Interface: {iface}. Result: {msg}", success=success)

    return jsonify({"success": success, "message": msg}), 200 if success else 400

@network_bp.route("/api/network/interface/renew", methods=["POST"])
@login_required
def api_renew_dhcp():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    iface = data.get("interface", "").strip()
    success, msg = NetworkManager.renew_dhcp(iface)
    audit_log("DHCP Renew", f"Interface: {iface}. Result: {msg}", success=success)
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@network_bp.route("/api/network/temporary-block", methods=["POST"])
@login_required
def api_temporary_block():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    iface = data.get("interface", "").strip()
    try:
        duration_minutes = int(data.get("duration_minutes", 10))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid duration"}), 400

    client_ip = request.remote_addr or "127.0.0.1"
    duration_seconds = duration_minutes * 60

    result = NetworkManager.schedule_temporary_disable(iface, duration_seconds, client_ip)
    audit_log("Temporary Network Block", 
              f"Disabled {iface} for {duration_minutes} min. Auto-restore scheduled.", 
              success=result["success"])

    return jsonify(result), 200 if result["success"] else 400

@network_bp.route("/api/network/temporary-restore", methods=["POST"])
@login_required
def api_temporary_restore():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    iface = data.get("interface", "").strip()
    success, msg = NetworkManager.restore_temporary_disable(iface)
    audit_log("Temporary Network Restore", f"Restored {iface}. Result: {msg}", success=success)
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@network_bp.route("/api/network/ports")
@login_required
def api_ports():
    ports = NetworkManager.get_listening_ports()
    return jsonify({"success": True, "data": ports})

@network_bp.route("/api/network/port-alias", methods=["POST"])
@login_required
def api_set_port_alias():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    try:
        port = int(data.get("port", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid port number"}), 400

    if port <= 0 or port > 65535:
        return jsonify({"success": False, "message": "Port number must be between 1 and 65535"}), 400

    label = str(data.get("label", "")).strip()
    success, msg = NetworkManager.set_port_alias(port, label)
    audit_log("Port Alias Set", f"Port: {port}, Label: '{label}'", success=success)
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@network_bp.route("/api/network/firewall")
@login_required
def api_firewall():
    status = NetworkManager.get_firewall_status()
    return jsonify({"success": True, "data": status})

