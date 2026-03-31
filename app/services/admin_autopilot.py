from __future__ import annotations

import json
from datetime import datetime, timedelta

from app import db
from app.models.admin_audit_log import AdminAuditLog
from app.models.admin_automation_config import AdminAutomationConfig
from app.models.booking import BookingRequest
from app.models.contact import ContactSubmission
from app.models.payment import Payment
from app.models.service_request import ServiceRequest


def get_admin_automation_config() -> AdminAutomationConfig:
    config = AdminAutomationConfig.query.first()
    if config:
        return config

    config = AdminAutomationConfig()
    db.session.add(config)
    db.session.commit()
    return config


def run_admin_autopilot(*, trigger: str, actor_admin_user_id: int | None = None) -> dict:
    config = get_admin_automation_config()
    now = datetime.utcnow()

    unread_contacts = ContactSubmission.query.filter_by(is_read=False).count()
    open_service_requests = ServiceRequest.query.filter(
        ServiceRequest.status.in_([
            ServiceRequest.STATUS_NEW,
            ServiceRequest.STATUS_REVIEWING,
        ])
    ).count()
    pending_payments = Payment.query.filter_by(status=Payment.STATUS_PENDING).count()

    stale_cutoff = now - timedelta(days=max(1, config.stale_booking_days))
    stale_new_bookings = BookingRequest.query.filter(
        BookingRequest.status == BookingRequest.STATUS_NEW,
        BookingRequest.submitted_at.isnot(None),
        BookingRequest.submitted_at <= stale_cutoff,
    ).all()

    auto_transitioned = 0
    if config.is_enabled and config.auto_mark_stale_bookings_reviewing:
        for booking in stale_new_bookings:
            booking.status = BookingRequest.STATUS_REVIEWING
            auto_transitioned += 1

    recommendations: list[str] = []
    if unread_contacts >= max(1, config.unread_contacts_threshold):
        recommendations.append(
            f"Unread contacts are high ({unread_contacts}). Prioritize contact triage."
        )
    if open_service_requests >= max(1, config.open_service_requests_threshold):
        recommendations.append(
            f"Open service requests are high ({open_service_requests}). Schedule follow-ups."
        )
    if pending_payments >= max(1, config.pending_payments_threshold):
        recommendations.append(
            f"Pending payments are high ({pending_payments}). Trigger payment reminder workflow."
        )
    if not recommendations:
        recommendations.append("No threshold breaches detected. Continue standard operating cadence.")

    result = {
        "trigger": trigger,
        "enabled": config.is_enabled,
        "unread_contacts": unread_contacts,
        "open_service_requests": open_service_requests,
        "pending_payments": pending_payments,
        "stale_new_bookings": len(stale_new_bookings),
        "auto_transitioned_to_reviewing": auto_transitioned,
        "recommendations": recommendations,
    }

    config.last_run_at = now
    config.last_run_summary = (
        f"Run at {now.strftime('%Y-%m-%d %H:%M UTC')} • "
        f"Unread={unread_contacts}, Open Services={open_service_requests}, Pending Payments={pending_payments}, "
        f"Stale New Bookings={len(stale_new_bookings)}, Auto-Transitioned={auto_transitioned}"
    )
    if actor_admin_user_id:
        config.updated_by_id = actor_admin_user_id

    db.session.add(
        AdminAuditLog(
            admin_user_id=actor_admin_user_id,
            action="autopilot.run",
            entity_type="admin_autopilot",
            entity_id=str(config.id),
            detail=json.dumps(result),
        )
    )

    db.session.commit()
    return result
