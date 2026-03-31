from datetime import datetime
from app import db


class SiteAnnouncement(db.Model):
    __tablename__ = "site_announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    created_by_id = db.Column(
        db.Integer, db.ForeignKey("admin_users.id"), nullable=True, index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<SiteAnnouncement {self.id} {self.title!r}>"
