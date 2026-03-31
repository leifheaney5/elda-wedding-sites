from datetime import datetime
from app import db


class ClientRsvpGuest(db.Model):
    __tablename__ = "client_rsvp_guests"

    STATUS_PENDING = "pending"
    STATUS_ATTENDING = "attending"
    STATUS_DECLINED = "declined"
    STATUS_MAYBE = "maybe"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("client_users.id"), nullable=False, index=True
    )
    full_name = db.Column(db.String(180), nullable=False)
    email = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    group_label = db.Column(db.String(80), nullable=True)
    table_name = db.Column(db.String(120), nullable=True)
    meal_choice = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    notes = db.Column(db.Text, nullable=True)
    invited_at = db.Column(db.DateTime, nullable=True)
    responded_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<ClientRsvpGuest {self.id} {self.full_name} [{self.status}]>"
