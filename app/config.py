import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Base configuration for the CWA translation platform."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

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

    # CSRF
    WTF_CSRF_ENABLED = _bool(os.environ.get("WTF_CSRF_ENABLED"), True)

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

    @staticmethod
    def init_app(app):
        os.makedirs(os.path.join(basedir, "data"), exist_ok=True)


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(name=None):
    name = name or os.environ.get("FLASK_ENV", "default")
    return config.get(name, DevelopmentConfig)
