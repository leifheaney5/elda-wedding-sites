from datetime import datetime
from app import db


class ContactSubmission(db.Model):
    __tablename__ = "contact_submissions"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client_users.id"), nullable=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    subject = db.Column(db.String(200), nullable=True)
    services_interested = db.Column(db.String(500), nullable=True)
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    admin_notes = db.Column(db.Text, nullable=True)
    attachments = db.relationship(
        "ContactAttachment",
        backref="submission",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<ContactSubmission {self.id} from {self.email}>"


class ContactAttachment(db.Model):
    __tablename__ = "contact_attachments"

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(
        db.Integer, db.ForeignKey("contact_submissions.id"), nullable=False, index=True
    )
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(120), nullable=True)
    data = db.Column(db.LargeBinary, nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    uploaded_by = db.Column(db.String(20), nullable=False, default="client")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ContactAttachment {self.id} {self.filename}>"
