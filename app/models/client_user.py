from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class ClientUser(UserMixin, db.Model):
    __tablename__ = "client_users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    auth_provider = db.Column(db.String(30), nullable=False, default="email")
    oauth_subject = db.Column(db.String(255), nullable=True, unique=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    bookings = db.relationship("BookingRequest", backref="client", lazy=True)
    contacts = db.relationship("ContactSubmission", backref="client", lazy=True)
    service_requests = db.relationship("ServiceRequest", backref="client", lazy=True)
    inspiration = db.relationship(
        "ClientInspiration", backref="client", uselist=False, lazy=True
    )
    plan_tasks = db.relationship("ClientPlanTask", backref="client", lazy=True)
    rsvp_guests = db.relationship("ClientRsvpGuest", backref="client", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        try:
            return check_password_hash(self.password_hash, password)
        except (ValueError, TypeError):
            return False

    def get_id(self):
        return f"client:{self.id}"

    @property
    def user_type(self) -> str:
        return "client"

    @property
    def is_owner(self) -> bool:
        return False

    def __repr__(self):
        return f"<ClientUser {self.email}>"
