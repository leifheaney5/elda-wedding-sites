from datetime import datetime
from app import db


class ClientInspiration(db.Model):
    __tablename__ = "client_inspirations"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("client_users.id"), nullable=False, unique=True, index=True
    )
    colors = db.Column(db.String(500), nullable=True)
    themes = db.Column(db.String(500), nullable=True)
    florals = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ClientInspiration client={self.client_id}>"
