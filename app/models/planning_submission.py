from datetime import datetime
from app import db


class PlanningSubmission(db.Model):
    __tablename__ = "planning_submissions"

    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_ARCHIVED = "archived"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client_users.id"), nullable=True, index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking_requests.id"), nullable=True, index=True)
    recipient_name = db.Column(db.String(150), nullable=True)
    recipient_email = db.Column(db.String(150), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)
    response_json = db.Column(db.JSON, nullable=True)
    rendered_text = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<PlanningSubmission {self.id} {self.status}>"
