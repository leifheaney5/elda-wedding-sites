from datetime import datetime
from app import db


class AutomationRule(db.Model):
    __tablename__ = "automation_rules"

    TRIGGER_PAYMENT_DUE = "payment_due"
    TRIGGER_RSVP_SOFT_DEADLINE = "rsvp_soft_deadline"
    TRIGGER_WEDDING_COUNTDOWN = "wedding_countdown"
    TRIGGER_VENDOR_CONFIRMATION = "vendor_confirmation"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), nullable=False, unique=True, index=True)
    name = db.Column(db.String(180), nullable=False)
    trigger_type = db.Column(db.String(60), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey("email_templates.id"), nullable=False, index=True)
    trigger_offset_days = db.Column(db.Integer, nullable=True)
    trigger_offset_hours = db.Column(db.Integer, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    template = db.relationship("EmailTemplate", backref="automation_rules", lazy=True)

    def __repr__(self):
        return f"<AutomationRule {self.key} ({self.trigger_type})>"
