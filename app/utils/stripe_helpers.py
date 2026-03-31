"""
Stripe payment helpers.
Full integration TBD — placeholder structure for future implementation.
"""
import stripe
from flask import current_app
from app import db
from app.models.payment import Payment


def get_stripe():
    stripe.api_key = current_app.config.get("STRIPE_SECRET_KEY")
    return stripe


def create_payment_intent(amount_cents: int, currency: str = "usd", metadata: dict = None):
    """
    Create a Stripe PaymentIntent and a local Payment record.
    Returns (payment_intent, payment_record).
    """
    s = get_stripe()
    intent = s.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        metadata=metadata or {},
    )
    payment = Payment(
        stripe_payment_intent_id=intent["id"],
        amount_cents=amount_cents,
        currency=currency,
        status=Payment.STATUS_PENDING,
        description=metadata.get("description") if metadata else None,
    )
    db.session.add(payment)
    db.session.commit()
    return intent, payment


def handle_webhook(payload: bytes, sig_header: str):
    """
    Process Stripe webhook events.
    Called from a POST /stripe/webhook route (to be added).
    """
    s = get_stripe()
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")
    try:
        event = s.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return False

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        payment = Payment.query.filter_by(
            stripe_payment_intent_id=intent["id"]
        ).first()
        if payment:
            from datetime import datetime
            payment.status = Payment.STATUS_PAID
            payment.paid_at = datetime.utcnow()
            db.session.commit()

    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        payment = Payment.query.filter_by(
            stripe_payment_intent_id=intent["id"]
        ).first()
        if payment:
            payment.status = Payment.STATUS_FAILED
            db.session.commit()

    return True
