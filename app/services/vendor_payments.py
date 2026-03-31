from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin
from typing import Any

import stripe
from flask import current_app

from app import db
from app.models.vendor import (
    Vendor,
    VendorPayoutAccount,
    VendorBooking,
    VendorPaymentPlan,
    VendorTransaction,
)


def _stripe_client() -> Any:
    api_key = current_app.config.get("STRIPE_SECRET_KEY")
    if not api_key:
        raise RuntimeError("Stripe is not configured")
    stripe.api_key = api_key
    return stripe


def _absolute_url(path_or_url: str) -> str:
    site_url = current_app.config.get("SITE_URL", "").rstrip("/")
    value = (path_or_url or "").strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if not site_url:
        return value
    return urljoin(f"{site_url}/", value.lstrip("/"))


def ensure_vendor_connect_account(vendor: Vendor) -> VendorPayoutAccount:
    existing = VendorPayoutAccount.query.filter_by(vendor_id=vendor.id).first()
    if existing:
        return existing

    stripe_client = _stripe_client()
    account_type = VendorPayoutAccount.ACCOUNT_EXPRESS
    account = stripe_client.Account.create(type=account_type)

    record = VendorPayoutAccount(
        vendor_id=vendor.id,
        stripe_account_id=account["id"],
        account_type=account_type,
        charges_enabled=bool(account.get("charges_enabled")),
        payouts_enabled=bool(account.get("payouts_enabled")),
        onboarding_status="pending",
    )
    db.session.add(record)
    db.session.commit()
    return record


def create_connect_onboarding_link(vendor: Vendor) -> dict:
    payout = ensure_vendor_connect_account(vendor)
    stripe_client = _stripe_client()

    refresh_url = _absolute_url(current_app.config.get("STRIPE_CONNECT_REFRESH_URL", "/admin/reports/weekly"))
    return_url = _absolute_url(current_app.config.get("STRIPE_CONNECT_RETURN_URL", "/admin/reports/weekly"))

    link = stripe_client.AccountLink.create(
        account=payout.stripe_account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding",
    )

    return {
        "url": link["url"],
        "expires_at": link.get("expires_at"),
        "stripe_account_id": payout.stripe_account_id,
    }


def create_vendor_milestone_payment_intent(
    vendor: Vendor,
    booking: VendorBooking,
    milestone: str,
    currency: str = "usd",
) -> dict:
    payout = VendorPayoutAccount.query.filter_by(vendor_id=vendor.id).first()
    if not payout:
        raise ValueError("Vendor has no connected payout account")

    plan = VendorPaymentPlan.query.filter_by(booking_id=booking.id).first()
    if not plan:
        raise ValueError("Booking has no payment plan")

    milestone = (milestone or "").strip().lower()
    if milestone == VendorTransaction.MILESTONE_DEPOSIT:
        amount_cents = int(plan.deposit_amount_cents or 0)
    elif milestone == VendorTransaction.MILESTONE_FINAL:
        amount_cents = int(plan.final_amount_cents or 0)
    else:
        raise ValueError("Unsupported milestone")

    if amount_cents <= 0:
        raise ValueError("Milestone amount is not configured")

    fee_bps = int(current_app.config.get("STRIPE_PLATFORM_FEE_BPS", 1000))
    platform_fee_cents = max(0, int(round(amount_cents * fee_bps / 10000)))
    vendor_net_cents = max(0, amount_cents - platform_fee_cents)

    stripe_client = _stripe_client()
    intent = stripe_client.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        automatic_payment_methods={"enabled": True},
        application_fee_amount=platform_fee_cents,
        transfer_data={"destination": payout.stripe_account_id},
        metadata={
            "vendor_id": str(vendor.id),
            "vendor_booking_id": str(booking.id),
            "milestone": milestone,
        },
    )

    tx = VendorTransaction(
        vendor_id=vendor.id,
        booking_id=booking.id,
        milestone=milestone,
        stripe_payment_intent_id=intent["id"],
        currency=currency,
        gross_cents=amount_cents,
        platform_fee_cents=platform_fee_cents,
        vendor_net_cents=vendor_net_cents,
        status=intent.get("status") or VendorTransaction.STATUS_REQUIRES_PAYMENT_METHOD,
    )
    db.session.add(tx)
    db.session.commit()

    return {
        "transaction_id": tx.id,
        "payment_intent_id": intent["id"],
        "client_secret": intent.get("client_secret"),
        "status": tx.status,
        "gross_cents": tx.gross_cents,
        "platform_fee_cents": tx.platform_fee_cents,
        "vendor_net_cents": tx.vendor_net_cents,
    }


def process_connect_webhook(payload: bytes, signature: str | None) -> dict:
    stripe_client = _stripe_client()
    secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")

    if not secret:
        raise RuntimeError("Stripe webhook secret not configured")

    event = stripe_client.Webhook.construct_event(payload, signature, secret)
    event_type = event.get("type", "")

    if event_type.startswith("account."):
        account = event["data"]["object"]
        payout = VendorPayoutAccount.query.filter_by(
            stripe_account_id=account.get("id")
        ).first()
        if payout:
            payout.charges_enabled = bool(account.get("charges_enabled"))
            payout.payouts_enabled = bool(account.get("payouts_enabled"))
            payout.onboarding_status = "complete" if payout.charges_enabled else "pending"
            db.session.commit()

    elif event_type == "payment_intent.succeeded":
        intent = event["data"]["object"]
        tx = VendorTransaction.query.filter_by(
            stripe_payment_intent_id=intent.get("id")
        ).first()
        if tx:
            tx.status = VendorTransaction.STATUS_SUCCEEDED
            tx.paid_at = datetime.utcnow()
            db.session.commit()

    elif event_type == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        tx = VendorTransaction.query.filter_by(
            stripe_payment_intent_id=intent.get("id")
        ).first()
        if tx:
            tx.status = VendorTransaction.STATUS_FAILED
            db.session.commit()

    return {"ok": True, "event_type": event_type}
