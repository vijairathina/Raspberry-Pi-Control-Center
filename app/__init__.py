import os
from datetime import timedelta
from flask import Flask
from app.config import config
from app.database import init_db, close_db
from app.services.scheduler import TaskScheduler
from app.services.automation_engine import AutomationEngine

def create_app(test_config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Load configuration
    app.config["SECRET_KEY"] = config["server"].get("secret_key", "dev-secret-key-12345")
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=config["server"].get("session_lifetime_minutes", 1440))
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    if test_config:
        app.config.update(test_config)

    # Initialize Database
    with app.app_context():
        init_db()

    # Teardown database connection
    @app.teardown_appcontext
    def teardown_db(exception=None):
        close_db()

    # Register Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.performance import performance_bp
    from app.routes.services import services_bp
    from app.routes.processes import processes_bp
    from app.routes.bluetooth import bluetooth_bp
    from app.routes.wifi import wifi_bp
    from app.routes.network import network_bp
    from app.routes.storage import storage_bp
    from app.routes.hardware import hardware_bp
    from app.routes.diagnostics import diagnostics_bp
    from app.routes.tasks import tasks_bp
    from app.routes.automation import automation_bp
    from app.routes.docker_routes import docker_bp
    from app.routes.tailscale_routes import tailscale_bp
    from app.routes.security_routes import security_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(performance_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(processes_bp)
    app.register_blueprint(bluetooth_bp)
    app.register_blueprint(wifi_bp)
    app.register_blueprint(network_bp)
    app.register_blueprint(storage_bp)
    app.register_blueprint(hardware_bp)
    app.register_blueprint(diagnostics_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(automation_bp)
    app.register_blueprint(docker_bp)
    app.register_blueprint(tailscale_bp)
    app.register_blueprint(security_bp)

    # Start background loops if not in testing
    if not app.config.get("TESTING"):
        TaskScheduler.start_background_loop()
        AutomationEngine.start_background_loop()
        from app.services.diagnostics import DiagnosticsService
        DiagnosticsService.start_internet_monitor_loop()

    return app
