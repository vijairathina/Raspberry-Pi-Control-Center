from flask import Blueprint, render_template, request, jsonify
from app.auth import login_required, validate_csrf_token, audit_log, generate_csrf_token
from app.services.diagnostics import DiagnosticsService

diagnostics_bp = Blueprint("diagnostics", __name__)

@diagnostics_bp.route("/diagnostics")
@login_required
def index():
    initial_conn = DiagnosticsService.run_connectivity_test()
    stats = DiagnosticsService.get_connectivity_stats(hours=1)
    return render_template("diagnostics.html", 
                           initial_conn=initial_conn, 
                           stats=stats, 
                           csrf_token=generate_csrf_token())

@diagnostics_bp.route("/api/diagnostics/ping", methods=["POST"])
@login_required
def api_ping():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    host = data.get("host", "").strip()
    count = int(data.get("count", 2))

    res = DiagnosticsService.ping_host(host, count=count)
    return jsonify(res)

@diagnostics_bp.route("/api/diagnostics/dns", methods=["POST"])
@login_required
def api_dns():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    domain = data.get("domain", "").strip()

    res = DiagnosticsService.dns_lookup(domain)
    return jsonify(res)

@diagnostics_bp.route("/api/diagnostics/traceroute", methods=["POST"])
@login_required
def api_traceroute():
    if not validate_csrf_token():
        return jsonify({"success": False, "message": "CSRF validation failed"}), 400

    data = request.get_json(silent=True) or request.form
    host = data.get("host", "").strip()

    res = DiagnosticsService.traceroute(host)
    return jsonify(res)

@diagnostics_bp.route("/api/diagnostics/connectivity")
@login_required
def api_connectivity():
    res = DiagnosticsService.run_connectivity_test()
    return jsonify({"success": True, "data": res})

@diagnostics_bp.route("/api/diagnostics/history")
@login_required
def api_history():
    hours = int(request.args.get("hours", 1))
    stats = DiagnosticsService.get_connectivity_stats(hours=hours)
    return jsonify({"success": True, "data": stats})
