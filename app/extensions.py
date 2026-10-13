from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
oauth = OAuth()

login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"


@login_manager.user_loader
def load_user(user_id):
    from app.models import User

    return db.session.get(User, int(user_id))
