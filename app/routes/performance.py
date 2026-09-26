from flask import Blueprint, render_template, jsonify
from app.auth import login_required, generate_csrf_token
from app.services.performance_service import PerformanceService

performance_bp = Blueprint("performance", __name__)

@performance_bp.route("/performance")
@login_required
def index():
    initial_metrics = PerformanceService.get_metrics()
    return render_template("performance.html", metrics=initial_metrics, csrf_token=generate_csrf_token())

@performance_bp.route("/api/performance/metrics")
@login_required
def api_metrics():
    metrics = PerformanceService.get_metrics()
    return jsonify({
        "success": True,
        "data": metrics,
        "message": "Performance metrics retrieved"
    })
