from app.extensions import db
from app.models import EmailVerificationOTP, PasswordResetOTP, User


def _register(client, **overrides):
    data = {
        "display_name": "Amani Wanjiru",
        "username": "amani_w",
        "email": "amani@example.ke",
        "password": "strongpass1",
        "confirm": "strongpass1",
        "county_id": "0",
        "preferred_language_id": "0",
        "preferred_dialect_id": "0",
        "consent": "y",
    }
    data.update(overrides)
    return client.post("/auth/register", data=data, follow_redirects=True)


def _mark_verified(email):
    user = User.query.filter_by(email=email).first()
    user.mark_email_verified()
    db.session.commit()
    return user


def test_register_creates_username(app, client):
    resp = _register(client)
    assert resp.status_code == 200
    user = User.query.filter_by(email="amani@example.ke").first()
    assert user is not None
    assert user.username == "amani_w"
    assert user.email_verified is False


def test_register_rejects_duplicate_username(app, client):
    _register(client)
    client.get("/auth/logout")
    resp = _register(client, email="other@example.ke")
    assert b"already taken" in resp.data
    assert User.query.filter_by(email="other@example.ke").first() is None


def test_register_rejects_reserved_username(app, client):
    resp = _register(client, username="admin", email="wannabe@example.ke")
    assert b"reserved" in resp.data
    assert User.query.filter_by(email="wannabe@example.ke").first() is None


def test_register_rejects_bad_username(app, client):
    resp = _register(client, username="bad name!", email="bad@example.ke")
    assert User.query.filter_by(email="bad@example.ke").first() is None
    assert b"characters" in resp.data or b"Username" in resp.data


def test_login_with_username_or_email(app, client):
    _register(client)
    client.get("/auth/logout")
    _mark_verified("amani@example.ke")

    by_username = client.post(
        "/auth/login",
        data={"identifier": "amani_w", "password": "strongpass1"},
        follow_redirects=True,
    )
    assert b"Signed in as" in by_username.data
    client.get("/auth/logout")

    by_email = client.post(
        "/auth/login",
        data={"identifier": "amani@example.ke", "password": "strongpass1"},
        follow_redirects=True,
    )
    assert b"Signed in as" in by_email.data


def test_login_wrong_password(app, client):
    _register(client)
    client.get("/auth/logout")
    resp = client.post(
        "/auth/login",
        data={"identifier": "amani_w", "password": "nope"},
        follow_redirects=True,
    )
    assert b"Invalid username/email or password" in resp.data


def test_seed_user_cannot_login(app, client):
    from tests.conftest import make_user
    user = make_user(app, "seed@test.ke", "Seed Person")
    user.is_seed = True
    db.session.commit()
    resp = client.post(
        "/auth/login",
        data={"identifier": "seed@test.ke", "password": "supersecret1"},
        follow_redirects=True,
    )
    assert b"cannot be used to sign in" in resp.data


def test_forgot_password_otp_flow(app, client, monkeypatch):
    _register(client)
    client.get("/auth/logout")
    _mark_verified("amani@example.ke")

    captured = {}

    def fake_send(user, code):
        captured["code"] = code
        captured["user_id"] = user.id
        return True

    monkeypatch.setattr("app.auth.send_password_reset_email", fake_send)

    resp = client.post(
        "/auth/forgot", data={"identifier": "amani_w"}, follow_redirects=True
    )
    assert resp.status_code == 200
    assert len(captured["code"]) == 6
    assert PasswordResetOTP.query.filter_by(user_id=captured["user_id"]).count() == 1

    reset = client.post(
        "/auth/reset",
        data={"code": captured["code"], "password": "brandnew1", "confirm": "brandnew1"},
        follow_redirects=True,
    )
    assert b"password has been updated" in reset.data

    login = client.post(
        "/auth/login",
        data={"identifier": "amani_w", "password": "brandnew1"},
        follow_redirects=True,
    )
    assert b"Signed in as" in login.data


def test_reset_rejects_wrong_code(app, client, monkeypatch):
    _register(client)
    client.get("/auth/logout")

    monkeypatch.setattr("app.auth.send_password_reset_email", lambda u, c: True)
    client.post("/auth/forgot", data={"identifier": "amani_w"})

    resp = client.post(
        "/auth/reset",
        data={"code": "000000", "password": "brandnew1", "confirm": "brandnew1"},
        follow_redirects=True,
    )
    assert b"not valid or has expired" in resp.data
    user = User.query.filter_by(email="amani@example.ke").first()
    assert user.check_password("strongpass1")  # unchanged


def test_forgot_password_unknown_account_is_generic(app, client):
    resp = client.post(
        "/auth/forgot", data={"identifier": "ghost@nowhere.ke"}, follow_redirects=True
    )
    assert b"If an account matches" in resp.data
    assert b"No account" not in resp.data
    assert b"not found" not in resp.data


def test_login_next_rejects_external_redirect(app, client):
    _register(client)
    client.get("/auth/logout")
    _mark_verified("amani@example.ke")
    resp = client.post(
        "/auth/login?next=//evil.example.com",
        data={"identifier": "amani_w", "password": "strongpass1"},
    )
    assert resp.status_code == 302
    location = resp.headers["Location"]
    assert "evil.example.com" not in location
    assert location.endswith("/tasks")


def test_login_next_allows_relative_path(app, client):
    _register(client)
    client.get("/auth/logout")
    _mark_verified("amani@example.ke")
    resp = client.post(
        "/auth/login?next=/tasks/phishing",
        data={"identifier": "amani_w", "password": "strongpass1"},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/tasks/phishing")


def test_production_requires_a_strong_secret_key(monkeypatch):
    import pytest

    from app import create_app

    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        create_app("production")


def test_production_accepts_a_strong_secret_key(monkeypatch):
    from app import create_app

    monkeypatch.setenv("SECRET_KEY", "s" * 48)
    app = create_app("production")
    assert app.debug is False
    assert app.config["SESSION_COOKIE_SECURE"] is True


def test_login_is_rate_limited(monkeypatch):
    from app import create_app
    from app.config import TestingConfig
    from app.extensions import limiter

    monkeypatch.setattr(TestingConfig, "RATELIMIT_ENABLED", True)
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    client = app.test_client()

    codes = [
        client.post(
            "/auth/login", data={"identifier": "nobody", "password": "wrong"}
        ).status_code
        for _ in range(12)
    ]
    assert 429 in codes
    limiter.reset()


def _capture_verification(monkeypatch):
    captured = {}

    def fake_send(user, code):
        captured["code"] = code
        captured["user_id"] = user.id
        return True

    monkeypatch.setattr("app.auth.send_verification_email", fake_send)
    monkeypatch.setattr("app.auth.mail_configured", lambda: True)
    return captured


def test_register_requires_email_verification(app, client, monkeypatch):
    captured = _capture_verification(monkeypatch)
    resp = _register(client)
    assert b"emailed a 6-digit code" in resp.data

    user = User.query.filter_by(email="amani@example.ke").first()
    assert user.email_verified is False
    assert EmailVerificationOTP.query.filter_by(user_id=user.id, used=False).count() == 1
    assert len(captured["code"]) == 6

    blocked = client.post(
        "/auth/login",
        data={"identifier": "amani_w", "password": "strongpass1"},
        follow_redirects=True,
    )
    assert b"confirm your email" in blocked.data.lower()

    page = client.get("/auth/verify")
    assert page.status_code == 200

    done = client.post(
        "/auth/verify", data={"code": captured["code"]}, follow_redirects=True
    )
    assert b"Email confirmed" in done.data
    user = User.query.filter_by(email="amani@example.ke").first()
    assert user.email_verified is True
    assert user.email_verified_at is not None


def test_verify_rejects_wrong_code(app, client, monkeypatch):
    _capture_verification(monkeypatch)
    _register(client)
    resp = client.post(
        "/auth/verify", data={"code": "000000"}, follow_redirects=True
    )
    assert b"not valid or has expired" in resp.data
    user = User.query.filter_by(email="amani@example.ke").first()
    assert user.email_verified is False


def test_verification_resend_has_cooldown(app, client, monkeypatch):
    captured = _capture_verification(monkeypatch)
    _register(client)
    first_code = captured["code"]
    resp = client.post("/auth/verify/resend", data={}, follow_redirects=True)
    assert b"just sent" in resp.data
    # The cooldown prevents a fresh code from being issued immediately.
    assert captured["code"] == first_code


def test_register_without_smtp_reports_console(app, client, monkeypatch):
    monkeypatch.setattr("app.auth.mail_configured", lambda: False)
    monkeypatch.setattr("app.auth.send_verification_email", lambda u, c: False)
    resp = _register(client)
    assert b"printed to the server console" in resp.data
    user = User.query.filter_by(email="amani@example.ke").first()
    assert user.email_verified is False

