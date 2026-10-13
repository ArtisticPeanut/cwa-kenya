import io
import json
import urllib.error

import pytest

from app import create_app
from app.services import email as email_service


class _FakeResponse:
    def __init__(self, body=b""):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeSMTP:
    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.started_tls = False
        self.logged_in = None
        self.sent = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, msg):
        self.sent = msg


def test_send_email_uses_smtp_when_configured(monkeypatch):
    app = create_app("testing")
    app.config.update(
        SMTP_HOST="smtp.example.com",
        SMTP_PORT=587,
        SMTP_USE_TLS=True,
        SMTP_USER="bot@example.com",
        SMTP_PASSWORD="secret",
        MAIL_FROM="bot@example.com",
        MAIL_FROM_NAME="CWA",
    )

    created = {}

    def factory(host, port, timeout=None):
        created["smtp"] = _FakeSMTP(host, port, timeout)
        return created["smtp"]

    monkeypatch.setattr(email_service.smtplib, "SMTP", factory)

    with app.app_context():
        ok = email_service.send_email("to@example.com", "Hi", "body")

    smtp = created["smtp"]
    assert ok is True
    assert smtp.host == "smtp.example.com"
    assert smtp.port == 587
    assert smtp.started_tls is True
    assert smtp.logged_in == ("bot@example.com", "secret")
    assert smtp.sent["To"] == "to@example.com"
    assert smtp.sent["Subject"] == "Hi"


def test_send_email_falls_back_to_logging_when_unconfigured(capsys):
    app = create_app("testing")
    app.config["SMTP_HOST"] = None

    with app.app_context():
        assert email_service.mail_configured() is False
        ok = email_service.send_email("to@example.com", "Hi", "body")

    assert ok is False
    assert "MIMO MAIL" in capsys.readouterr().out


def test_verification_email_builds_message(monkeypatch):
    app = create_app("testing")
    app.config["SMTP_HOST"] = "smtp.example.com"
    app.config["MAIL_FROM"] = "bot@example.com"
    app.config["MAIL_FROM_NAME"] = "CWA"

    captured = {}

    def fake_send(to, subject, body_text, body_html=None):
        captured.update(
            to=to, subject=subject, body_text=body_text, body_html=body_html
        )
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send)

    with app.app_context():
        from app.models import User

        user = User(email="amani@example.ke", display_name="Amani",
                    username="amani_w")
        email_service.send_verification_email(user, "123456")

    assert captured["to"] == "amani@example.ke"
    assert "123456" in captured["body_text"]
    assert "123456" in captured["body_html"]


def test_send_email_uses_brevo_api(monkeypatch):
    app = create_app("testing")
    app.config.update(
        BREVO_API_KEY="key123",
        RESEND_API_KEY=None,
        SMTP_HOST=None,
        MAIL_FROM="bot@example.com",
        MAIL_FROM_NAME="CWA",
    )

    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = {k.lower(): v for k, v in request.header_items()}
        captured["data"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setattr(email_service.urllib.request, "urlopen", fake_urlopen)

    with app.app_context():
        assert email_service.mail_configured() is True
        ok = email_service.send_email("to@example.com", "Hi", "body", "<b>body</b>")

    assert ok is True
    assert captured["url"] == "https://api.brevo.com/v3/smtp/email"
    assert captured["headers"]["api-key"] == "key123"
    assert captured["data"]["to"] == [{"email": "to@example.com"}]
    assert captured["data"]["subject"] == "Hi"
    assert captured["data"]["textContent"] == "body"
    assert captured["data"]["htmlContent"] == "<b>body</b>"


def test_send_email_uses_resend_api(monkeypatch):
    app = create_app("testing")
    app.config.update(
        BREVO_API_KEY=None,
        RESEND_API_KEY="re_123",
        SMTP_HOST="smtp.should-not-be-used.example.com",
        MAIL_FROM="bot@example.com",
        MAIL_FROM_NAME="CWA",
    )

    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = {k.lower(): v for k, v in request.header_items()}
        captured["data"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setattr(email_service.urllib.request, "urlopen", fake_urlopen)

    with app.app_context():
        ok = email_service.send_email("to@example.com", "Hi", "body")

    assert ok is True
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["authorization"] == "Bearer re_123"
    assert captured["data"]["to"] == ["to@example.com"]
    assert captured["data"]["subject"] == "Hi"
    assert "bot@example.com" in captured["data"]["from"]


def test_send_email_api_error_raises(monkeypatch):
    app = create_app("testing")
    app.config.update(
        BREVO_API_KEY="bad",
        RESEND_API_KEY=None,
        SMTP_HOST=None,
        MAIL_FROM="bot@example.com",
    )

    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, 401, "Unauthorized", {},
            io.BytesIO(b'{"message":"bad key"}'),
        )

    monkeypatch.setattr(email_service.urllib.request, "urlopen", fake_urlopen)

    with app.app_context():
        with pytest.raises(RuntimeError):
            email_service.send_email("to@example.com", "Hi", "body")
