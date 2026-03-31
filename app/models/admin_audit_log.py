from datetime import datetime

from app import db


class AdminAuditLog(db.Model):
    __tablename__ = "admin_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), nullable=True, index=True)
    action = db.Column(db.String(120), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=False, index=True)
    entity_id = db.Column(db.String(64), nullable=True, index=True)
    detail = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    admin_user = db.relationship("AdminUser", backref=db.backref("audit_logs", lazy="dynamic"))

    def __repr__(self):
        return f"<AdminAuditLog action={self.action} entity={self.entity_type}:{self.entity_id}>"
