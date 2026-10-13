"""Flask CLI commands for setup and administration."""

import re

import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import ROLE_ADMIN, ROLE_REVIEWER, User
from app.services import exporter, importer, seeding


def register_cli(app):
    app.cli.add_command(init_db)
    app.cli.add_command(seed)
    app.cli.add_command(import_csv)
    app.cli.add_command(repair_classification)
    app.cli.add_command(create_user)
    app.cli.add_command(migrate_usernames)
    app.cli.add_command(export_data)


def _unique_username(base, exclude_id=None):
    base = re.sub(r"[^a-z0-9_]", "", (base or "user").lower())[:24] or "user"
    candidate, n = base, 1
    while User.username_taken(candidate, exclude_id=exclude_id):
        n += 1
        candidate = f"{base}{n}"[:30]
    return candidate


@click.command("init-db")
@with_appcontext
def init_db():
    """Create all database tables."""
    db.create_all()
    click.echo("Database tables created.")


@click.command("seed")
@with_appcontext
def seed():
    """Seed reference data (counties, languages, terms, milestones)."""
    stats = seeding.seed_all(verbose=True)
    click.echo(f"Seeded: {stats}")


@click.command("import-csv")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@with_appcontext
def import_csv(path):
    """Import Google Forms responses CSV at PATH."""
    stats = importer.import_csv(path)
    click.echo(f"Import stats: {stats}")


@click.command("repair-classification")
@with_appcontext
def repair_classification():
    """Reclassify submissions filed under the wrong language."""
    stats = importer.repair_misclassified(verbose=True)
    click.echo(f"Repair stats: {stats}")


@click.command("create-user")
@click.option("--email", prompt=True)
@click.option("--name", prompt="Display name")
@click.option("--username", default=None,
              help="Defaults to the email's local part.")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--role", default="admin",
              type=click.Choice(["contributor", "reviewer", "admin"]))
@with_appcontext
def create_user(email, name, username, password, role):
    """Create a user account (defaults to administrator)."""
    email = email.strip().lower()
    if User.query.filter(db.func.lower(User.email) == email).first():
        click.echo("A user with that email already exists.")
        raise SystemExit(1)
    username = _unique_username(username or email.split("@")[0])
    user = User(email=email, username=username, display_name=name.strip(), role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Created {role} account for {email} (username: {username}).")


@click.command("migrate-usernames")
@with_appcontext
def migrate_usernames():
    """Add the username column (if missing) and backfill from each email."""
    db.create_all()  # creates the password_reset_otps table on older databases
    from sqlalchemy import inspect, text

    columns = {c["name"] for c in inspect(db.engine).get_columns("users")}
    if "username" not in columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(30)"))
        db.session.commit()
        click.echo("Added users.username column.")
    db.session.execute(
        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)")
    )
    db.session.commit()

    changed = 0
    for user in User.query.order_by(User.id).all():
        if user.username:
            continue
        user.username = _unique_username(
            (user.email or "user").split("@")[0], exclude_id=user.id
        )
        changed += 1
    db.session.commit()
    click.echo(f"Backfilled {changed} username(s).")


@click.command("export")
@click.option("--format", "fmt", default="json", type=click.Choice(["json", "csv"]))
@click.option("--include-unapproved", is_flag=True)
@with_appcontext
def export_data(fmt, include_unapproved):
    """Print approved translations to stdout as JSON or CSV."""
    if fmt == "json":
        click.echo(exporter.to_json(include_unapproved=include_unapproved))
    else:
        click.echo(exporter.to_csv(include_unapproved=include_unapproved))
