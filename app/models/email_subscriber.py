from datetime import datetime
from app import db


class EmailSubscriber(db.Model):
    __tablename__ = "email_subscribers"

    SOURCE_FOOTER = "footer"
    SOURCE_CLIENT_PLAN = "client_plan"
    SOURCE_ADMIN = "admin"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False, unique=True, index=True)
    name = db.Column(db.String(150), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    source = db.Column(db.String(30), nullable=False, default=SOURCE_FOOTER)
    notes = db.Column(db.Text, nullable=True)
    subscribed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    unsubscribed_at = db.Column(db.DateTime, nullable=True)
    last_email_sent_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<EmailSubscriber {self.email} active={self.is_active}>"
