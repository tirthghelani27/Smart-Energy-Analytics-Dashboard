# ============================================================
# Smart Energy Analytics Platform - Configuration
# ============================================================

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration shared across all environments."""

    # ── App ──────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    APP_NAME = "Smart Energy Analytics"
    APP_VERSION = "1.0.0"

    # ── Database ─────────────────────────────────────────────
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_NAME = os.environ.get("DB_NAME", "smart_energy_db")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # ── Session ───────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = False          # set True in production (HTTPS)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # ── File Uploads ─────────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # ── Reports ───────────────────────────────────────────────
    REPORTS_FOLDER = os.path.join(BASE_DIR, "src", "static", "reports")

    # ── Email (Flask-Mail) ───────────────────────────────────
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@smartenergy.com")

    # ── Password Reset ────────────────────────────────────────
    # How long (in seconds) a password-reset link remains valid.
    PASSWORD_RESET_EXPIRY = int(os.environ.get("PASSWORD_RESET_EXPIRY", 3600))

    # ── Energy / Carbon ──────────────────────────────────────
    # kg CO₂ emitted per kWh (India grid average)
    CO2_EMISSION_FACTOR = float(os.environ.get("CO2_EMISSION_FACTOR", 0.82))
    # Default electricity tariff (₹ per kWh)
    DEFAULT_TARIFF_RATE = float(os.environ.get("DEFAULT_TARIFF_RATE", 6.50))

    # ── Pagination ───────────────────────────────────────────
    RECORDS_PER_PAGE = 10

    # ── ML Models ────────────────────────────────────────────
    MODELS_FOLDER = os.path.join(BASE_DIR, "src", "static", "models")


class DevelopmentConfig(Config):
    """Development environment — debug on, SQLite fallback available."""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = False          # set True to log SQL queries


class TestingConfig(Config):
    """Testing environment — uses an in-memory SQLite DB."""
    DEBUG = True
    TESTING = True
    # Override to SQLite so tests run without a MySQL server
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "tests", "test_uploads")


class ProductionConfig(Config):
    """Production environment — strict security settings.

    SECRET_KEY MUST be set via the environment variable SECRET_KEY before
    deploying.  The check is deferred to runtime (inside create_app) so that
    simply *importing* config.py never raises — only actually running in
    production without the variable set will raise.
    """
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

    # Read from env; keep the base-class fallback so the class body never
    # raises.  create_app() performs the hard check at runtime.
    SECRET_KEY = os.environ.get("SECRET_KEY") or Config.SECRET_KEY

    @staticmethod
    def validate():
        """Call this once inside create_app() when FLASK_ENV=production."""
        key = os.environ.get("SECRET_KEY", "")
        if not key or key == "dev-secret-key-change-in-production":
            raise RuntimeError(
                "ProductionConfig requires a strong SECRET_KEY environment "
                "variable. Set it before starting the server."
            )


# ── Config map ───────────────────────────────────────────────
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config():
    """Return the config class that matches the FLASK_ENV environment variable."""
    env = os.environ.get("FLASK_ENV", "default")
    return config_map.get(env, DevelopmentConfig)
