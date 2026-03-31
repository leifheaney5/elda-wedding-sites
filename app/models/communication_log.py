from datetime import datetime
from app import db


class CommunicationLog(db.Model):
    __tablename__ = "communication_logs"

    STATUS_QUEUED = "queued"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    CHANNEL_EMAIL = "email"

    TRIGGER_AUTOMATION = "automation"
    TRIGGER_MANUAL = "manual"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("email_templates.id"), nullable=True, index=True)
    automation_rule_id = db.Column(db.Integer, db.ForeignKey("automation_rules.id"), nullable=True, index=True)

    client_user_id = db.Column(db.Integer, db.ForeignKey("client_users.id"), nullable=True, index=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=True, index=True)
    vendor_booking_id = db.Column(db.Integer, db.ForeignKey("vendor_bookings.id"), nullable=True, index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking_requests.id"), nullable=True, index=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=True, index=True)

    channel = db.Column(db.String(20), nullable=False, default=CHANNEL_EMAIL)
    trigger_source = db.Column(db.String(20), nullable=False, default=TRIGGER_AUTOMATION)
    lifecycle_key = db.Column(db.String(120), nullable=True)
    idempotency_key = db.Column(db.String(255), nullable=False, unique=True, index=True)

    recipient_name = db.Column(db.String(180), nullable=True)
    recipient_email = db.Column(db.String(180), nullable=False, index=True)
    sender_email = db.Column(db.String(180), nullable=True)

    status = db.Column(db.String(20), nullable=False, default=STATUS_QUEUED, index=True)
    provider_name = db.Column(db.String(30), nullable=True)
    provider_message_id = db.Column(db.String(180), nullable=True)
    provider_error = db.Column(db.Text, nullable=True)

    subject_rendered = db.Column(db.String(255), nullable=False)
    body_html_rendered = db.Column(db.Text, nullable=False)
    body_markdown_rendered = db.Column(db.Text, nullable=True)
    payload_json = db.Column(db.JSON, nullable=True)

    scheduled_for = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by_admin_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), nullable=True, index=True)

    template = db.relationship("EmailTemplate", backref="communication_logs", lazy=True)
    automation_rule = db.relationship("AutomationRule", backref="communication_logs", lazy=True)

    def __repr__(self):
        return f"<CommunicationLog {self.id} {self.status} {self.recipient_email}>"
