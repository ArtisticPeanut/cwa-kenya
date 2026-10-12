from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.forms import LoginForm, ProfileForm, RegisterForm
from app.models import County, Dialect, Language, User

auth_bp = Blueprint("auth", __name__)


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
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RegisterForm()
    _populate_choices(form, request.form.get("preferred_language_id", type=int))
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter(db.func.lower(User.email) == email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("auth/register.html", form=form)
        user = User(
            email=email,
            display_name=form.display_name.data.strip(),
            county_id=form.county_id.data or None,
            preferred_language_id=form.preferred_language_id.data or None,
            preferred_dialect_id=form.preferred_dialect_id.data or None,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome! Your contributor account has been created.", "success")
        return redirect(url_for("main.tasks"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter(db.func.lower(User.email) == email).first()
        if user and user.is_seed:
            flash("This is an imported record and cannot be used to sign in.", "warning")
        elif user and user.check_password(form.password.data):
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
            login_user(user, remember=form.remember.data)
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            flash(f"Signed in as {user.display_name}.", "success")
            return redirect(url_for("main.tasks"))
        else:
            flash("Invalid email or password.", "danger")
    return render_template("auth/login.html", form=form)


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
        current_user.display_name = form.display_name.data.strip()
        current_user.county_id = form.county_id.data or None
        current_user.preferred_language_id = form.preferred_language_id.data or None
        current_user.preferred_dialect_id = form.preferred_dialect_id.data or None
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html", form=form)
