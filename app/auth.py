import time
from datetime import datetime, timezone

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db, limiter
from app.forms import (
    ForgotPasswordForm,
    LoginForm,
    ProfileForm,
    RegisterForm,
    ResendVerificationForm,
    ResetPasswordForm,
    VerifyEmailForm,
)
from app.models import (
    County,
    Dialect,
    EmailVerificationOTP,
    Language,
    PasswordResetOTP,
    User,
)
from app.services.email import (
    mail_configured,
    send_password_reset_email,
    send_verification_email,
)

auth_bp = Blueprint("auth", __name__)

RESERVED_USERNAMES = {
    "admin", "administrator", "root", "system", "support", "moderator",
    "staff", "official", "mimo", "cwa", "help", "security", "me", "you",
}
RESEND_COOLDOWN_SECONDS = 60


def _safe_next(target):
    """Only allow same-site, absolute-path redirects (blocks //evil.com)."""
    if not target or not target.startswith("/"):
        return None
    if target.startswith("//") or target.startswith("/\\"):
        return None
    return target


def _issue_verification(user):
    """Create a fresh email-verification code and try to email it.

    Returns one of:
      "sent"   — handed to the configured SMTP server
      "logged" — no SMTP configured, so the code was written to the console/log
      "failed" — sending raised; the user can request a new code

    The code record is always saved by the caller so it can be resent.
    """
    _record, code = EmailVerificationOTP.issue(
        user, ttl_minutes=current_app.config["OTP_TTL_MINUTES"]
    )
    if not mail_configured():
        send_verification_email(user, code)  # falls back to console logging
        return "logged"
    try:
        send_verification_email(user, code)
        return "sent"
    except Exception:  # noqa: BLE001 - keep the account, let them resend
        current_app.logger.exception("Verification email failed")
        return "failed"


def _verification_flash(status, email):
    """Flash an honest message about how the verification code was delivered."""
    if status == "sent":
        flash(f"We've emailed a 6-digit code to {email}.", "success")
    elif status == "logged":
        flash(
            "Email delivery isn't set up yet, so the 6-digit code was printed "
            "to the server console. Configure SMTP_* in your .env to send real "
            "email.",
            "info",
        )
    else:
        flash(
            "We couldn't send the email right now. Please tap \"Resend code\" "
            "to try again.",
            "warning",
        )


def county_choices():
    return [(0, "— None —")] + [
        (c.id, c.name) for c in County.query.order_by(County.name).all()
    ]


def language_choices():
    return [(0, "— None —")] + [
        (l.id, l.name) for l in Language.query.order_by(Language.name).all()
    ]


def dialect_choices(language_id=None):
    query = Dialect.query
    if language_id:
        query = query.filter_by(language_id=language_id)
    return [(0, "— None —")] + [
        (d.id, f"{d.name} ({d.language.name})")
        for d in query.order_by(Dialect.name).all()
    ]


def _populate_choices(form, language_id=None):
    form.county_id.choices = county_choices()
    form.preferred_language_id.choices = language_choices()
    form.preferred_dialect_id.choices = dialect_choices(language_id)


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"],
               error_message="Too many sign-up attempts. Please try again later.")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RegisterForm()
    _populate_choices(form, request.form.get("preferred_language_id", type=int))
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        username = User.normalize_username(form.username.data)
        if User.query.filter(db.func.lower(User.email) == email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("auth/register.html", form=form)
        if username in RESERVED_USERNAMES:
            flash("That username is reserved. Please choose another.", "danger")
            return render_template("auth/register.html", form=form)
        if User.username_taken(username):
            flash("That username is already taken. Please choose another.", "danger")
            return render_template("auth/register.html", form=form)
        user = User(
            email=email,
            username=username,
            display_name=form.display_name.data.strip(),
            county_id=form.county_id.data or None,
            preferred_language_id=form.preferred_language_id.data or None,
            preferred_dialect_id=form.preferred_dialect_id.data or None,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # assign an id so the verification code can link to it
        status = _issue_verification(user)
        db.session.commit()
        session["verify_uid"] = user.id
        session["verify_sent_at"] = time.time()
        _verification_flash(status, email)
        return redirect(url_for("auth.verify_email"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"],
               error_message="Too many sign-in attempts. Please wait a minute and try again.")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.find_by_identifier(form.identifier.data)
        if user and user.is_seed:
            flash("This is an imported record and cannot be used to sign in.", "warning")
        elif user and user.check_password(form.password.data):
            if not user.email_verified:
                session["verify_uid"] = user.id
                flash(
                    "Please confirm your email before signing in. "
                    "Enter the code we emailed you, or request a new one.",
                    "warning",
                )
                return redirect(url_for("auth.verify_email"))
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
            login_user(user, remember=form.remember.data)
            next_url = _safe_next(request.args.get("next"))
            if next_url:
                return redirect(next_url)
            flash(f"Signed in as {user.display_name}.", "success")
            return redirect(url_for("main.tasks"))
        else:
            flash("Invalid username/email or password.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/verify", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"],
               error_message="Too many attempts. Please wait a minute and try again.")
def verify_email():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    uid = session.get("verify_uid")
    user = db.session.get(User, uid) if uid else None
    if not user:
        flash("Create an account first, then confirm your email.", "info")
        return redirect(url_for("auth.register"))
    if user.email_verified:
        flash("Your email is already confirmed. Please sign in.", "info")
        return redirect(url_for("auth.login"))

    form = VerifyEmailForm()
    resend_form = ResendVerificationForm()
    if form.validate_on_submit():
        record = (
            EmailVerificationOTP.query.filter_by(user_id=user.id, used=False)
            .order_by(EmailVerificationOTP.created_at.desc())
            .first()
        )
        max_attempts = current_app.config["OTP_MAX_ATTEMPTS"]
        if record and record.verify(form.code.data, max_attempts=max_attempts):
            user.mark_email_verified()
            db.session.commit()
            session.pop("verify_uid", None)
            session.pop("verify_sent_at", None)
            login_user(user)
            flash("Email confirmed — karibu aboard!", "success")
            return redirect(url_for("main.tasks"))
        db.session.commit()
        flash("That code is not valid or has expired. Check it and try again.", "danger")
    return render_template(
        "auth/verify_email.html", form=form, resend_form=resend_form, email=user.email
    )


@auth_bp.route("/verify/resend", methods=["POST"])
@limiter.limit("5 per minute", methods=["POST"],
               error_message="Too many resend requests. Please wait a minute and try again.")
def resend_verification():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    resend_form = ResendVerificationForm()
    if not resend_form.validate_on_submit():
        return redirect(url_for("auth.verify_email"))
    uid = session.get("verify_uid")
    user = db.session.get(User, uid) if uid else None
    if not user:
        flash("Create an account first, then confirm your email.", "info")
        return redirect(url_for("auth.register"))
    if user.email_verified:
        flash("Your email is already confirmed. Please sign in.", "info")
        return redirect(url_for("auth.login"))
    sent_at = session.get("verify_sent_at")
    if sent_at and (time.time() - sent_at) < RESEND_COOLDOWN_SECONDS:
        flash("A code was just sent. Please check your inbox.", "info")
        return redirect(url_for("auth.verify_email"))
    sent = _issue_verification(user)
    db.session.commit()
    session["verify_sent_at"] = time.time()
    _verification_flash(sent, user.email)
    return redirect(url_for("auth.verify_email"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.home"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    _populate_choices(form, current_user.preferred_language_id)
    if request.method == "GET":
        form.county_id.data = current_user.county_id or 0
        form.preferred_language_id.data = current_user.preferred_language_id or 0
        form.preferred_dialect_id.data = current_user.preferred_dialect_id or 0
    if form.validate_on_submit():
        username = User.normalize_username(form.username.data)
        if username in RESERVED_USERNAMES:
            flash("That username is reserved. Please choose another.", "danger")
            return render_template("auth/profile.html", form=form)
        if User.username_taken(username, exclude_id=current_user.id):
            flash("That username is already taken. Please choose another.", "danger")
            return render_template("auth/profile.html", form=form)
        current_user.username = username
        current_user.display_name = form.display_name.data.strip()
        current_user.county_id = form.county_id.data or None
        current_user.preferred_language_id = form.preferred_language_id.data or None
        current_user.preferred_dialect_id = form.preferred_dialect_id.data or None
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html", form=form)


@auth_bp.route("/forgot", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"],
               error_message="Too many reset requests. Please wait a minute and try again.")
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.find_by_identifier(form.identifier.data)
        if user and not user.is_seed and user.password_hash:
            sent_at = session.get("reset_sent_at")
            if sent_at and (time.time() - sent_at) < RESEND_COOLDOWN_SECONDS:
                flash("A code was just sent. Please check your inbox.", "info")
                return redirect(url_for("auth.reset_password"))
            record, code = PasswordResetOTP.issue(
                user, ttl_minutes=current_app.config["OTP_TTL_MINUTES"]
            )
            db.session.commit()
            try:
                send_password_reset_email(user, code)
            except Exception:  # noqa: BLE001 - surface a friendly error, keep record
                current_app.logger.exception("Password reset email failed")
                flash(
                    "We could not send the email right now. Please try again shortly.",
                    "danger",
                )
                return render_template("auth/forgot_password.html", form=form)
            session["reset_uid"] = user.id
            session["reset_sent_at"] = time.time()
            flash("We've sent a 6-digit code to the email on that account.", "success")
            return redirect(url_for("auth.reset_password"))
        # Generic message avoids revealing whether an account exists.
        flash(
            "If an account matches, we've sent a reset code to its email address.",
            "info",
        )
        return render_template("auth/forgot_password.html", form=form)
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"],
               error_message="Too many attempts. Please wait a minute and try again.")
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    uid = session.get("reset_uid")
    user = db.session.get(User, uid) if uid else None
    if not user:
        flash("Enter your details to receive a reset code.", "info")
        return redirect(url_for("auth.forgot_password"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        record = (
            PasswordResetOTP.query.filter_by(user_id=user.id, used=False)
            .order_by(PasswordResetOTP.created_at.desc())
            .first()
        )
        max_attempts = current_app.config["OTP_MAX_ATTEMPTS"]
        if record and record.verify(form.code.data, max_attempts=max_attempts):
            user.set_password(form.password.data)
            db.session.commit()
            session.pop("reset_uid", None)
            session.pop("reset_sent_at", None)
            flash("Your password has been updated. Please sign in.", "success")
            return redirect(url_for("auth.login"))
        db.session.commit()
        flash("That code is not valid or has expired. Check it and try again.", "danger")
    return render_template("auth/reset_password.html", form=form, email=user.email)
