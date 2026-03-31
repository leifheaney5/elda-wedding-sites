from datetime import datetime
from app import db


class Payment(db.Model):
    __tablename__ = "payments"

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_REFUNDED = "refunded"
    STATUS_FAILED = "failed"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer, db.ForeignKey("booking_requests.id"), nullable=True
    )
    stripe_payment_intent_id = db.Column(db.String(200), nullable=True, unique=True)
    amount_cents = db.Column(db.Integer, nullable=False)   # store as cents — no floats
    currency = db.Column(db.String(10), nullable=False, default="usd")
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    description = db.Column(db.String(255), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def amount_dollars(self) -> float:
        return self.amount_cents / 100

    def __repr__(self):
        return (
            f"<Payment {self.id} ${self.amount_dollars:.2f} [{self.status}]>"
        )
