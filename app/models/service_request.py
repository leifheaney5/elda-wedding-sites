from datetime import datetime
from app import db


class ServiceRequest(db.Model):
    __tablename__ = "service_requests"

    TYPE_PACKAGE = "package"
    TYPE_VENUE = "venue"
    TYPE_CATERING = "catering"
    TYPE_FLORALS = "florals"

    STATUS_NEW = "new"
    STATUS_REVIEWING = "reviewing"
    STATUS_CONTACTED = "contacted"
    STATUS_CLOSED = "closed"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client_users.id"), nullable=True, index=True)
    request_type = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    event_date = db.Column(db.Date, nullable=True)
    guest_count = db.Column(db.Integer, nullable=True)
    selected_service = db.Column(db.String(150), nullable=True)
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_NEW)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin_notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<ServiceRequest {self.id} [{self.request_type}] {self.email}>"
