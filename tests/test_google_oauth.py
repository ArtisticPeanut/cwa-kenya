from flask import redirect

from app.extensions import db, oauth
from app.models import User


def _enable_google(app):
    """Configure and register the Google client on an already-built app."""
    from app.oauth import register_google

    app.config["GOOGLE_CLIENT_ID"] = "test-client-id"
    app.config["GOOGLE_CLIENT_SECRET"] = "test-secret"
    register_google(app)


def _fake_token(userinfo):
    return lambda: {"userinfo": userinfo}


def test_button_hidden_when_google_not_configured(app, client):
    resp = client.get("/auth/login")
    assert b"Continue with Google" not in resp.data


def test_button_shown_when_configured(app, client):
    _enable_google(app)
    resp = client.get("/auth/login")
    assert b"Continue with Google" in resp.data
    register = client.get("/auth/register")
    assert b"Continue with Google" in register.data


def test_google_login_disabled_redirects_to_login(app, client):
    resp = client.get("/auth/google", follow_redirects=True)
    assert b"available right now" in resp.data


def test_google_login_redirects_to_google(app, client, monkeypatch):
    _enable_google(app)
    captured = {}

    def fake_authorize_redirect(redirect_uri):
        captured["uri"] = redirect_uri
        return redirect("https://accounts.google.com/o/oauth2/v2/auth?client_id=x")

    monkeypatch.setattr(oauth.google, "authorize_redirect", fake_authorize_redirect)
    resp = client.get("/auth/google")
    assert resp.status_code == 302
    assert "accounts.google.com" in resp.headers["Location"]
    assert captured["uri"].endswith("/auth/google/callback")


def test_google_callback_creates_verified_user(app, client, monkeypatch):
    _enable_google(app)
    monkeypatch.setattr(
        oauth.google,
        "authorize_access_token",
        _fake_token(
            {"email": "newuser@gmail.com", "email_verified": True, "name": "New User"}
        ),
    )
    resp = client.get("/auth/google/callback", follow_redirects=True)
    assert resp.status_code == 200
    user = User.query.filter_by(email="newuser@gmail.com").first()
    assert user is not None
    assert user.email_verified is True
    assert user.username == "newuser"
    assert user.display_name == "New User"
    assert b"created with Google" in resp.data


def test_google_callback_links_existing_unverified_account(app, client, monkeypatch):
    _enable_google(app)
    from tests.conftest import make_user

    user = make_user(app, "linkme@test.ke", "Link Me", email_verified=False)
    monkeypatch.setattr(
        oauth.google,
        "authorize_access_token",
        _fake_token({"email": "linkme@test.ke", "email_verified": True}),
    )
    resp = client.get("/auth/google/callback", follow_redirects=True)
    assert resp.status_code == 200
    db.session.refresh(user)
    assert user.email_verified is True
    # No duplicate account was created.
    assert User.query.filter_by(email="linkme@test.ke").count() == 1


def test_google_callback_rejects_unverified_email(app, client, monkeypatch):
    _enable_google(app)
    monkeypatch.setattr(
        oauth.google,
        "authorize_access_token",
        _fake_token({"email": "unverified@gmail.com", "email_verified": False}),
    )
    resp = client.get("/auth/google/callback", follow_redirects=True)
    assert b"verified email" in resp.data
    assert User.query.filter_by(email="unverified@gmail.com").first() is None


def test_google_callback_blocks_seed_records(app, client, monkeypatch):
    _enable_google(app)
    from tests.conftest import make_user

    user = make_user(app, "seed@import.local", "Seed Person")
    user.is_seed = True
    db.session.commit()
    monkeypatch.setattr(
        oauth.google,
        "authorize_access_token",
        _fake_token({"email": "seed@import.local", "email_verified": True}),
    )
    resp = client.get("/auth/google/callback", follow_redirects=True)
    assert b"imported record" in resp.data


def test_google_callback_handles_exchange_failure(app, client, monkeypatch):
    _enable_google(app)

    def boom():
        raise RuntimeError("bad state")

    monkeypatch.setattr(oauth.google, "authorize_access_token", boom)
    resp = client.get("/auth/google/callback", follow_redirects=True)
    assert b"complete Google sign-in" in resp.data


def test_google_callback_avoids_username_collision(app, client, monkeypatch):
    _enable_google(app)
    existing = User(
        email="taken@test.ke", username="newuser", display_name="Taken",
        email_verified=True,
    )
    db.session.add(existing)
    db.session.commit()

    monkeypatch.setattr(
        oauth.google,
        "authorize_access_token",
        _fake_token({"email": "newuser@gmail.com", "email_verified": True}),
    )
    client.get("/auth/google/callback", follow_redirects=True)
    user = User.query.filter_by(email="newuser@gmail.com").first()
    assert user is not None
    assert user.username != "newuser"
    assert user.username.startswith("newuser")
