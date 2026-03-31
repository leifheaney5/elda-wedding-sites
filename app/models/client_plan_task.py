from datetime import datetime
from app import db


class ClientPlanTask(db.Model):
    __tablename__ = "client_plan_tasks"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("client_users.id"), nullable=False, index=True
    )
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(80), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    is_required = db.Column(db.Boolean, default=True)
    is_completed = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ClientPlanTask {self.id} client={self.client_id}>"
