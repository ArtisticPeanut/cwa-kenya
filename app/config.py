import os
from datetime import timedelta

from dotenv import load_dotenv

# Load a local .env file (if present) for every entrypoint — including WSGI
# servers, which do not load it the way the Flask CLI does. Real environment
# variables still take precedence (override defaults to False).
load_dotenv()

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Sentinel used in development only. Production refuses to start with this value.
DEV_SECRET_KEY = "dev-secret-change-me"

# Well-known placeholders that must never be used in production.
WEAK_SECRET_KEYS = {
    DEV_SECRET_KEY,
    "change-me-to-a-long-random-string",
    "changeme",
    "secret",
    "secret-key",
    "password",
}


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Base configuration for the CWA translation platform."""

    # Resolved from SECRET_KEY at init_app time (see init_app below).
    SECRET_KEY = None

    base_url = os.environ.get("DATABASE_URL")
    if base_url:
        SQLALCHEMY_DATABASE_URI = base_url
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
            basedir, "data", "cwa.db"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Session / auth
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # CSRF
    WTF_CSRF_ENABLED = _bool(os.environ.get("WTF_CSRF_ENABLED"), True)

    # Rate limiting (Flask-Limiter). Memory storage is fine for a single
    # process; point RATELIMIT_STORAGE_URI at Redis (e.g. redis://localhost:6379)
    # when running multiple workers.
    RATELIMIT_ENABLED = _bool(os.environ.get("RATELIMIT_ENABLED"), True)
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    # Trust X-Forwarded-* headers from one reverse proxy (needed so rate
    # limiting sees the real client IP and HTTPS is detected correctly).
    TRUST_PROXY = _bool(os.environ.get("TRUST_PROXY"), False)

    # App metadata
    APP_NAME = "Kenyan Community-Driven Cybersecurity Translation Platform"
    APP_SHORT_NAME = "CWA Kenya"
    DEFAULT_LANGUAGE = "en"

    # Consensus thresholds (used by the review workflow)
    MIN_VOTES_FOR_CONSENSUS = int(os.environ.get("MIN_VOTES_FOR_CONSENSUS", 3))
    CONSENSUS_RATIO = float(os.environ.get("CONSENSUS_RATIO", 0.66))
    AMBIGUITY_MARGIN = float(os.environ.get("AMBIGUITY_MARGIN", 0.15))

    # API
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", 12))

    # Email (SMTP) — falls back to console logging when SMTP_HOST is unset
    SMTP_HOST = os.environ.get("SMTP_HOST")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    SMTP_USE_TLS = _bool(os.environ.get("SMTP_USE_TLS"), True)
    MAIL_FROM = (os.environ.get("MAIL_FROM") or os.environ.get("SMTP_USER") or "").strip() or None
    MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "Cyber Words Africa")

    # Optional HTTPS email API. Use these on hosts that block outbound SMTP
    # (e.g. Render's free plan): traffic goes over port 443 instead. When set,
    # they take precedence over SMTP. Set exactly one API key.
    # Values are trimmed so a stray space/newline from copy-paste can't break them.
    BREVO_API_KEY = (os.environ.get("BREVO_API_KEY") or "").strip() or None
    RESEND_API_KEY = (os.environ.get("RESEND_API_KEY") or "").strip() or None

    # One-time codes for password reset
    OTP_TTL_MINUTES = int(os.environ.get("OTP_TTL_MINUTES", "10"))
    OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", "5"))

    @staticmethod
    def init_app(app):
        os.makedirs(os.path.join(basedir, "data"), exist_ok=True)
        # Resolve the signing key now so env changes (and .env) are honoured,
        # and so production can validate it before the app starts serving.
        app.config["SECRET_KEY"] = (
            os.environ.get("SECRET_KEY") or DEV_SECRET_KEY
        )


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    @staticmethod
    def init_app(app):
        Config.init_app(app)
        secret = app.config.get("SECRET_KEY")
        if (
            not secret
            or secret in WEAK_SECRET_KEYS
            or len(secret) < 32
        ):
            raise RuntimeError(
                "SECRET_KEY must be set to a unique value of at least 32 "
                "characters before running in production. Set the SECRET_KEY "
                "environment variable (see .env.example)."
            )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(name=None):
    name = name or os.environ.get("FLASK_ENV", "default")
    return config.get(name, DevelopmentConfig)
