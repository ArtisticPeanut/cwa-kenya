"""Outbound email helper.

Uses SMTP when configured (via SMTP_* settings). When SMTP_HOST is not set the
message is written to the application log and stdout instead, so development
and demos work without a mail server. Real credentials can be plugged in later
without any code change.
"""

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from flask import current_app


def mail_configured():
    return bool(current_app.config.get("SMTP_HOST"))


def send_email(to, subject, body_text, body_html=None):
    """Send an email, or log it when no SMTP server is configured.

    Returns True when handed to an SMTP server, False when it was logged.
    """
    cfg = current_app.config
    sender = cfg.get("MAIL_FROM")
    from_name = cfg.get("MAIL_FROM_NAME") or cfg.get("APP_SHORT_NAME")

    if not mail_configured():
        _log_dev_message(to, subject, body_text)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name, sender)) if sender else from_name
    msg["To"] = to
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    host = cfg["SMTP_HOST"]
    port = cfg.get("SMTP_PORT", 587)
    use_tls = cfg.get("SMTP_USE_TLS", True)

    if use_tls:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls(context=context)
            if cfg.get("SMTP_USER"):
                server.login(cfg["SMTP_USER"], cfg.get("SMTP_PASSWORD") or "")
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(host, port, timeout=15) as server:
            if cfg.get("SMTP_USER"):
                server.login(cfg["SMTP_USER"], cfg.get("SMTP_PASSWORD") or "")
            server.send_message(msg)
    return True


def send_password_reset_email(user, code):
    """Email a one-time password-reset code to a user."""
    app_short = current_app.config.get("APP_SHORT_NAME", "CWA Kenya")
    minutes = current_app.config.get("OTP_TTL_MINUTES", 10)
    name = user.display_name or user.username or "there"
    subject = f"Your {app_short} security code"
    body_text = (
        f"Jambo {name},\n\n"
        f"Someone asked to reset the password for your {app_short} account.\n\n"
        f"Your verification code is: {code}\n\n"
        f"Enter this code to choose a new password. It expires in {minutes} minutes.\n"
        f"If you did not request this, you can safely ignore this email — "
        f"your password will not change.\n\n"
        f"— Mimo & the {app_short} team\n"
    )
    body_html = (
        f'<div style="font-family:Segoe UI,system-ui,Arial,sans-serif;color:#1e2235;'
        f'max-width:480px;margin:auto;">'
        f'<h2 style="color:#4338ca;margin:0 0 .4rem;">{app_short}</h2>'
        f"<p>Jambo {name},</p>"
        f"<p>Someone asked to reset the password for your {app_short} account. "
        f"Use this code to choose a new password:</p>"
        f'<p style="font-size:2rem;font-weight:800;letter-spacing:.3em;'
        f'background:#eef2ff;color:#3730a3;padding:.6rem 1rem;border-radius:12px;'
        f'text-align:center;">{code}</p>'
        f"<p>This code expires in {minutes} minutes. If you did not request it, "
        f"you can ignore this email.</p>"
        f'<p style="color:#6b7280;">— Mimo &amp; the {app_short} team</p>'
        f"</div>"
    )
    return send_email(user.email, subject, body_text, body_html)


def _log_dev_message(to, subject, body):
    current_app.logger.warning("[MAIL-DEV] to=%s subject=%s", to, subject)
    banner = "=" * 60
    print(f"\n{banner}\nMIMO MAIL (dev — no SMTP configured)\n"
          f"To: {to}\nSubject: {subject}\n\n{body}\n{banner}\n")
