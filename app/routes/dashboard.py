from flask import Blueprint, render_template, jsonify, session
from app.auth import login_required, generate_csrf_token
from app.services.system_service import SystemService
from app.services.bluetooth_manager import BluetoothManager
from app.services.wifi_manager import WifiManager
from app.services.audit_logger import AuditLogger
from app.services.service_manager import ServiceManager

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    summary = SystemService.get_system_summary()
    return render_template("dashboard.html", summary=summary, csrf_token=generate_csrf_token())

@dashboard_bp.route("/api/dashboard/summary")
@login_required
def api_summary():
    summary = SystemService.get_system_summary()
    bt_status = BluetoothManager.get_status()
    wifi_status = WifiManager.get_current_connection()

    # Dynamic Alert Evaluation for Dashboard
    alerts = []
    qm = summary["quick_metrics"]
    health = summary["health"]

    # CPU alert
    if qm["cpu_percent"] >= 95:
        alerts.append({"type": "High CPU", "severity": "Critical", "message": f"CPU load is critical at {qm['cpu_percent']}%"})
    elif qm["cpu_percent"] >= 85:
        alerts.append({"type": "High CPU", "severity": "Warning", "message": f"CPU load is elevated at {qm['cpu_percent']}%"})

    # RAM alert
    if qm["ram_percent"] >= 95:
        alerts.append({"type": "High RAM", "severity": "Critical", "message": f"Memory usage is critical at {qm['ram_percent']}%"})
    elif qm["ram_percent"] >= 85:
        alerts.append({"type": "High RAM", "severity": "Warning", "message": f"Memory usage is elevated at {qm['ram_percent']}%"})

    # Temp alert
    if qm["temp_celsius"] >= 80:
        alerts.append({"type": "High Temperature", "severity": "Critical", "message": f"Core temperature is {qm['temp_celsius']}°C"})
    elif qm["temp_celsius"] >= 70:
        alerts.append({"type": "High Temperature", "severity": "Warning", "message": f"Core temperature is {qm['temp_celsius']}°C"})

    # Disk alert
    if qm["disk_percent"] >= 90:
        alerts.append({"type": "Disk Full", "severity": "Critical", "message": f"Storage partition is {qm['disk_percent']}% full"})
    elif qm["disk_percent"] >= 75:
        alerts.append({"type": "Disk Usage", "severity": "Warning", "message": f"Storage partition is {qm['disk_percent']}% full"})

    # Undervoltage / Throttling
    throttling = health["throttling"]
    if throttling.get("undervoltage_now"):
        alerts.append({"type": "Undervoltage", "severity": "Critical", "message": "Active power undervoltage detected on board"})
    elif throttling.get("throttled_now"):
        alerts.append({"type": "CPU Throttled", "severity": "Critical", "message": "CPU frequency throttling active due to heat/power"})

    # Bluetooth alert
    if not bt_status.get("powered"):
        alerts.append({"type": "Bluetooth Disabled", "severity": "Normal", "message": "Bluetooth radio is currently switched off"})

    # Wi-Fi alert
    if not wifi_status.get("connected") or wifi_status.get("ssid") == "Disconnected":
        alerts.append({"type": "Wi-Fi Disconnected", "severity": "Warning", "message": "Wireless interface is not connected to a network"})

    recent_db_alerts = AuditLogger.get_alerts(resolved=False, limit=5)

    return jsonify({
        "success": True,
        "data": {
            "summary": summary,
            "bluetooth": bt_status,
            "wifi": wifi_status,
            "active_alerts": alerts,
            "db_alerts": recent_db_alerts
        },
        "message": "Telemetry updated"
    })
