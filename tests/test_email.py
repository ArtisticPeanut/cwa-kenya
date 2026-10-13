from app import create_app
from app.services import email as email_service


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
