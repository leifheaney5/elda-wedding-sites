from datetime import datetime
from app import db


class EmailTemplate(db.Model):
    __tablename__ = "email_templates"

    AUDIENCE_CLIENT = "client"
    AUDIENCE_VENDOR = "vendor"
    AUDIENCE_INTERNAL = "internal"

    CATEGORY_LIFECYCLE = "lifecycle"
    CATEGORY_ANNOUNCEMENT = "announcement"
    CATEGORY_OPERATIONAL = "operational"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), nullable=False, unique=True, index=True)
    name = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(40), nullable=False, default=CATEGORY_OPERATIONAL)
    audience = db.Column(db.String(40), nullable=False, default=AUDIENCE_CLIENT)
    description = db.Column(db.String(255), nullable=True)
    subject_template = db.Column(db.String(255), nullable=False)
    body_html_template = db.Column(db.Text, nullable=False)
    body_markdown_template = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_system = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<EmailTemplate {self.key}>"
