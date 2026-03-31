from datetime import datetime
from app import db


class SeatingPlan(db.Model):
    __tablename__ = "seating_plans"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client_users.id"), nullable=True, index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking_requests.id"), nullable=True, index=True)
    title = db.Column(db.String(180), nullable=False)
    venue_area = db.Column(db.String(120), nullable=True)
    table_layout_json = db.Column(db.JSON, nullable=True)
    rsvp_json = db.Column(db.JSON, nullable=True)
    final_guest_count = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SeatingPlan {self.id} client={self.client_id}>"
