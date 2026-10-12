import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    Language,
    ROLE_ADMIN,
    Term,
    User,
)
from app.services import seeding  # noqa: E402


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        seeding.seed_all()
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def sample_term(app):
    return Term.query.filter_by(slug="phishing").first()


@pytest.fixture()
def sample_language(app):
    return Language.query.filter_by(name="Kikuyu").first()


def make_user(app, email, name, role="contributor", password="supersecret1"):
    user = User(email=email, display_name=name, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def admin_user(app):
    return make_user(app, "admin@test.ke", "Admin", role=ROLE_ADMIN)


@pytest.fixture()
def contributor(app):
    return make_user(app, "contrib@test.ke", "Contributor")
