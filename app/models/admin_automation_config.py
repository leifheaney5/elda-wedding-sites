from datetime import datetime

from app import db


class AdminAutomationConfig(db.Model):
    __tablename__ = "admin_automation_configs"

    id = db.Column(db.Integer, primary_key=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    auto_mark_stale_bookings_reviewing = db.Column(db.Boolean, nullable=False, default=False)
    stale_booking_days = db.Column(db.Integer, nullable=False, default=3)
    unread_contacts_threshold = db.Column(db.Integer, nullable=False, default=8)
    open_service_requests_threshold = db.Column(db.Integer, nullable=False, default=8)
    pending_payments_threshold = db.Column(db.Integer, nullable=False, default=5)
    last_run_at = db.Column(db.DateTime, nullable=True)
    last_run_summary = db.Column(db.Text, nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), nullable=True, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    updated_by = db.relationship("AdminUser", backref=db.backref("automation_config_updates", lazy="dynamic"))

    def __repr__(self):
        return f"<AdminAutomationConfig enabled={self.is_enabled} stale_days={self.stale_booking_days}>"
