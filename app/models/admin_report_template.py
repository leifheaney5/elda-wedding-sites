from datetime import datetime

from app import db


class AdminReportTemplate(db.Model):
    __tablename__ = "admin_report_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    dataset = db.Column(db.String(30), nullable=False, index=True)
    fields_csv = db.Column(db.Text, nullable=False)
    status_filter = db.Column(db.String(30), nullable=False, default="all")
    date_start = db.Column(db.Date, nullable=True)
    date_end = db.Column(db.Date, nullable=True)
    viz_type = db.Column(db.String(30), nullable=False, default="daily_volume")
    created_by_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_by = db.relationship("AdminUser", backref=db.backref("report_templates", lazy="dynamic"))

    def field_list(self) -> list[str]:
        return [field.strip() for field in (self.fields_csv or "").split(",") if field.strip()]

    def __repr__(self):
        return f"<AdminReportTemplate {self.id} {self.name!r} dataset={self.dataset}>"
