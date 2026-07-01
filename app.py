
import os
from flask import Flask
from config import get_config

# ── Re-export extensions so legacy `from app import db` still works ──
# Any file that already does `from app import db` continues to work
# without changes.  Both names refer to the SAME object.
from src.extensions import db, login_manager, bcrypt, mail, migrate  # noqa: F401


def create_app(config_class=None):
    """
    Application factory.

    Usage:
        app = create_app()                  # picks up FLASK_ENV from environment
        app = create_app(TestingConfig)     # explicit config (used by pytest)
    """
    app = Flask(
        __name__,
        template_folder=os.path.join("src", "templates"),
        static_folder=os.path.join("src", "static"),
    )

    # ── Load config ──────────────────────────────────────────
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # Deferred production-secret validation (never raises at import time)
    if hasattr(config_class, "validate"):
        config_class.validate()

    # ── Ensure required directories exist ────────────────────
    for folder in [
        app.config["UPLOAD_FOLDER"],
        app.config["REPORTS_FOLDER"],
        app.config["MODELS_FOLDER"],
    ]:
        os.makedirs(folder, exist_ok=True)

    # ── Bind extensions to this app ──────────────────────────
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # ── Login manager ─────────────────────────────────────────
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        from src.models.user import User
        return db.session.get(User, int(user_id))

    # ── Register blueprints ───────────────────────────────────
    _register_blueprints(app)

    # ── Template filters / context processors ────────────────
    _register_template_filters(app)

    # ── Shell context (`flask shell`) ─────────────────────────
    @app.shell_context_processor
    def make_shell_context():
        from src.models.user import User
        from src.models.electricity_usage import ElectricityUsage
        from src.models.appliance import Appliance
        from src.models.prediction import Prediction
        from src.models.alert import Alert
        from src.models.recommendation import Recommendation
        from src.models.carbon_footprint import CarbonFootprint
        from src.models.report import Report
        return {
            "db": db,
            "User": User,
            "ElectricityUsage": ElectricityUsage,
            "Appliance": Appliance,
            "Prediction": Prediction,
            "Alert": Alert,
            "Recommendation": Recommendation,
            "CarbonFootprint": CarbonFootprint,
            "Report": Report,
        }

    # ── Error handlers ────────────────────────────────────────
    from flask import render_template as _rt

    @app.errorhandler(403)
    def forbidden(e):
        return _rt("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return _rt("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        # In development, re-raise so Flask shows the real traceback
        if app.config.get("DEBUG"):
            raise e
        return _rt("errors/500.html"), 500

    return app


# ── Blueprint registration ────────────────────────────────────
def _register_blueprints(app: Flask):
    """Import and register every blueprint inside create_app scope."""
    from src.routes.main import main_bp
    from src.routes.auth import auth_bp
    from src.routes.dashboard import dashboard_bp
    from src.routes.analytics import analytics_bp
    from src.routes.appliances import appliances_bp
    from src.routes.forecasting import forecasting_bp
    from src.routes.carbon import carbon_bp
    from src.routes.recommendations import recommendations_bp
    from src.routes.reports import reports_bp
    from src.routes.admin import admin_bp
    from src.routes.data_import import data_import_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp,            url_prefix="/auth")
    app.register_blueprint(dashboard_bp,       url_prefix="/dashboard")
    app.register_blueprint(analytics_bp,       url_prefix="/analytics")
    app.register_blueprint(appliances_bp,      url_prefix="/appliances")
    app.register_blueprint(forecasting_bp,     url_prefix="/forecasting")
    app.register_blueprint(carbon_bp,          url_prefix="/carbon")
    app.register_blueprint(recommendations_bp, url_prefix="/recommendations")
    app.register_blueprint(reports_bp,         url_prefix="/reports")
    app.register_blueprint(admin_bp,           url_prefix="/admin")
    app.register_blueprint(data_import_bp,     url_prefix="/data")


# ── Template filters / globals ────────────────────────────────
def _register_template_filters(app: Flask):
    @app.template_filter("currency")
    def currency_filter(value):
        try:
            return f"₹{float(value):,.2f}"
        except (ValueError, TypeError):
            return "₹0.00"

    @app.template_filter("kwh")
    def kwh_filter(value):
        try:
            return f"{float(value):,.2f} kWh"
        except (ValueError, TypeError):
            return "0.00 kWh"

    @app.template_filter("co2")
    def co2_filter(value):
        try:
            return f"{float(value):,.2f} kg CO₂"
        except (ValueError, TypeError):
            return "0.00 kg CO₂"

    @app.template_global("app_name")
    def app_name():
        return app.config.get("APP_NAME", "Smart Energy Analytics")

    @app.context_processor
    def inject_globals():
        return {
            "emission_factor": app.config.get("CO2_EMISSION_FACTOR", 0.82),
            "tariff_rate":     app.config.get("DEFAULT_TARIFF_RATE", 6.50),
            "app_version":     app.config.get("APP_VERSION", "1.0.0"),
        }


# ── Run directly (`python app.py`) ────────────────────────────
if __name__ == "__main__":
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=app.config.get("DEBUG", False),
    )
