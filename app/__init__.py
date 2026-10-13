import os

from flask import Flask, render_template

from app.config import get_config
from app.extensions import db, login_manager, csrf, limiter


def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=False)
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Ensure the data directory exists before SQLAlchemy touches SQLite.
    config_class.init_app(app)
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///"):
        db_path = app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
        if db_path and db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Behind a reverse proxy, trust one layer of X-Forwarded-* headers so Flask
    # sees the real client IP (rate limiting) and the correct scheme.
    if app.config.get("TRUST_PROXY"):
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    _register_blueprints(app)
    _register_cli(app)
    _register_jinja(app)
    _register_errors(app)

    return app


def _register_blueprints(app):
    from app.auth import auth_bp
    from app.main import main_bp
    from app.admin import admin_bp
    from app.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api/v1")


def _register_cli(app):
    from app.cli import register_cli

    register_cli(app)


def _register_jinja(app):
    from app.models import (
        ROLE_LABELS,
        STATUS_LABELS,
        CATEGORY_LABELS,
    )
    from app.services.recognition import TIER_LABELS

    @app.context_processor
    def inject_globals():
        return {
            "app_name": app.config["APP_NAME"],
            "app_short_name": app.config["APP_SHORT_NAME"],
            "role_labels": ROLE_LABELS,
            "status_labels": STATUS_LABELS,
            "category_labels": CATEGORY_LABELS,
            "tier_labels": TIER_LABELS,
        }

    @app.template_filter("datetime")
    def _datetime(value, fmt="%d %b %Y, %H:%M"):
        if not value:
            return ""
        return value.strftime(fmt)

    @app.template_filter("date")
    def _date(value, fmt="%d %b %Y"):
        if not value:
            return ""
        return value.strftime(fmt)

    @app.template_filter("pct")
    def _pct(value):
        try:
            return f"{float(value) * 100:.0f}%"
        except (TypeError, ValueError):
            return "0%"


def _register_errors(app):
    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/error.html", code=403,
                               message="You do not have permission to access this page."), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/error.html", code=404,
                               message="The page you are looking for was not found."), 404

    @app.errorhandler(429)
    def too_many_requests(error):
        message = getattr(error, "description", None) or (
            "Too many requests. Please slow down and try again shortly."
        )
        return render_template("errors/error.html", code=429, message=message), 429

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("errors/error.html", code=500,
                               message="Something went wrong on our side."), 500
