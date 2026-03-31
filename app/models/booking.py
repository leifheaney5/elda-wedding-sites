from datetime import datetime
from app import db


class BookingRequest(db.Model):
    __tablename__ = "booking_requests"

    # Status choices
    STATUS_NEW = "new"
    STATUS_REVIEWING = "reviewing"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client_users.id"), nullable=True, index=True)
    couple_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    wedding_date = db.Column(db.Date, nullable=True)
    package_id = db.Column(db.String(50), nullable=True)   # slug e.g. "elopement"
    guest_count = db.Column(db.Integer, nullable=True)
    venue_preference = db.Column(db.String(150), nullable=True)
    ceremony_time = db.Column(db.String(50), nullable=True)
    special_requests = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_NEW)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin_notes = db.Column(db.Text, nullable=True)

    # Relationships
    payments = db.relationship("Payment", backref="booking", lazy=True)

    def __repr__(self):
        return f"<BookingRequest {self.id} — {self.couple_name} [{self.status}]>"
