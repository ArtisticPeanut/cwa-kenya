"""Google Sign-In (OAuth 2.0 / OpenID Connect) wiring.

The Google client is only registered when both ``GOOGLE_CLIENT_ID`` and
``GOOGLE_CLIENT_SECRET`` are configured, so the app runs unchanged (and the
"Continue with Google" button stays hidden) when they are not set.
"""

from flask import current_app

from app.extensions import oauth

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
GOOGLE_SCOPE = "openid email profile"


def google_oauth_configured(config=None):
    """True when both Google credentials are present."""
    config = config if config is not None else current_app.config
    return bool(config.get("GOOGLE_CLIENT_ID") and config.get("GOOGLE_CLIENT_SECRET"))


def register_google(app):
    """Register (or re-register) the Google client from the current config."""
    if not google_oauth_configured(app.config):
        return False
    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url=GOOGLE_DISCOVERY_URL,
        client_kwargs={"scope": GOOGLE_SCOPE},
    )
    return True


def init_oauth(app):
    oauth.init_app(app)
    register_google(app)
