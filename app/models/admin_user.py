from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


class AdminUser(UserMixin, db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")  # owner | staff
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        try:
            return check_password_hash(self.password_hash, password)
        except (ValueError, TypeError):
            return False

    def get_id(self):
        return f"admin:{self.id}"

    @property
    def user_type(self) -> str:
        return "admin"

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"

    def __repr__(self):
        return f"<AdminUser {self.email} [{self.role}]>"


@login_manager.user_loader
def load_user(user_id: str):
    if not user_id:
        return None
    try:
        user_type, raw_id = user_id.split(":", 1)
    except ValueError:
        # Backward compatibility with old un-prefixed admin sessions.
        return db.session.get(AdminUser, int(user_id))

    if user_type == "admin":
        return db.session.get(AdminUser, int(raw_id))
    if user_type == "client":
        from app.models.client_user import ClientUser

        return db.session.get(ClientUser, int(raw_id))
    return None
