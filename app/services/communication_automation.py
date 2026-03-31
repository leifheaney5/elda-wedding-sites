from __future__ import annotations

from datetime import datetime, timedelta

from app import db
from app.models.automation_rule import AutomationRule
from app.models.booking import BookingRequest
from app.models.client_rsvp_guest import ClientRsvpGuest
from app.models.client_user import ClientUser
from app.models.communication_log import CommunicationLog
from app.models.email_template import EmailTemplate
from app.models.payment import Payment
from app.models.planning_submission import PlanningSubmission
from app.models.vendor import Vendor, VendorBooking, VendorLead, VendorPaymentPlan, VendorTransaction
from app.services.communications import enqueue_template_email


def _format_money(cents: int | None, currency: str = "USD") -> str:
    amount = (cents or 0) / 100
    return f"{currency.upper()} {amount:,.2f}"


def _latest_booking_for_client(client_id: int | None, email: str | None) -> BookingRequest | None:
    if client_id:
        booking = (
            BookingRequest.query.filter_by(client_id=client_id)
            .order_by(BookingRequest.submitted_at.desc())
            .first()
        )
        if booking:
            return booking
    if email:
        return (
            BookingRequest.query.filter(BookingRequest.email.ilike(email.strip().lower()))
            .order_by(BookingRequest.submitted_at.desc())
            .first()
        )
    return None


def _resolve_vendor_contact(vendor_booking: VendorBooking) -> tuple[str | None, str | None]:
    vendor = Vendor.query.get(vendor_booking.vendor_id)
    lead = VendorLead.query.get(vendor_booking.lead_id)
    if not lead:
        return None, vendor.business_name if vendor else None
    return lead.inquiry_email, vendor.business_name if vendor else None


def _ensure_rule_defaults() -> None:
    defaults = [
        {
            "key": "payment_due_7d",
            "name": "Payment Reminder (7 days)",
            "trigger_type": AutomationRule.TRIGGER_PAYMENT_DUE,
            "template_key": "payment_due_reminder",
            "days": 7,
        },
        {
            "key": "payment_due_24h",
            "name": "Payment Reminder (24 hours)",
            "trigger_type": AutomationRule.TRIGGER_PAYMENT_DUE,
            "hours": 24,
            "template_key": "payment_due_reminder",
        },
        {
            "key": "rsvp_soft_deadline_followup",
            "name": "RSVP Soft Deadline Follow-up",
            "trigger_type": AutomationRule.TRIGGER_RSVP_SOFT_DEADLINE,
            "days": 0,
            "template_key": "rsvp_soft_deadline_followup",
        },
        {
            "key": "countdown_6_months",
            "name": "Wedding Countdown (6 months)",
            "trigger_type": AutomationRule.TRIGGER_WEDDING_COUNTDOWN,
            "days": 180,
            "template_key": "wedding_countdown_milestone",
        },
        {
            "key": "countdown_1_month",
            "name": "Wedding Countdown (1 month)",
            "trigger_type": AutomationRule.TRIGGER_WEDDING_COUNTDOWN,
            "days": 30,
            "template_key": "wedding_countdown_milestone",
        },
        {
            "key": "countdown_big_week",
            "name": "Wedding Countdown (Big week)",
            "trigger_type": AutomationRule.TRIGGER_WEDDING_COUNTDOWN,
            "days": 7,
            "template_key": "wedding_countdown_milestone",
        },
        {
            "key": "vendor_confirm_30d",
            "name": "Vendor Confirmation (30 days)",
            "trigger_type": AutomationRule.TRIGGER_VENDOR_CONFIRMATION,
            "days": 30,
            "template_key": "vendor_confirmation_ping",
        },
    ]

    for item in defaults:
        template = EmailTemplate.query.filter_by(key=item["template_key"]).first()
        if not template:
            continue
        existing = AutomationRule.query.filter_by(key=item["key"]).first()
        if existing:
            continue
        db.session.add(
            AutomationRule(
                key=item["key"],
                name=item["name"],
                trigger_type=item["trigger_type"],
                template_id=template.id,
                trigger_offset_days=item.get("days"),
                trigger_offset_hours=item.get("hours"),
                is_active=True,
            )
        )
    db.session.commit()


def evaluate_automation_rules(*, now: datetime | None = None, dry_run: bool = False) -> dict:
    _ensure_rule_defaults()
    current_time = now or datetime.utcnow()
    created = 0

    active_rules = AutomationRule.query.filter_by(is_active=True).all()
    template_map = {
        template.id: template
        for template in EmailTemplate.query.filter(EmailTemplate.id.in_([rule.template_id for rule in active_rules])).all()
    }

    for rule in active_rules:
        template = template_map.get(rule.template_id)
        if not template:
            continue

        if rule.trigger_type == AutomationRule.TRIGGER_PAYMENT_DUE:
            target_due = current_time + timedelta(days=rule.trigger_offset_days or 0, hours=rule.trigger_offset_hours or 0)
            start_window = target_due - timedelta(minutes=30)
            end_window = target_due + timedelta(minutes=30)

            plans = (
                VendorPaymentPlan.query.join(VendorBooking, VendorPaymentPlan.booking_id == VendorBooking.id)
                .join(VendorLead, VendorBooking.lead_id == VendorLead.id)
                .filter(VendorBooking.status.in_([VendorBooking.STATUS_TENTATIVE, VendorBooking.STATUS_CONFIRMED]))
                .all()
            )
            for plan in plans:
                due_candidates = [
                    ("deposit", plan.deposit_due_at, plan.deposit_amount_cents),
                    ("final", plan.final_due_at, plan.final_amount_cents),
                ]
                for milestone, due_at, amount_cents in due_candidates:
                    if not due_at:
                        continue
                    if not (start_window <= due_at <= end_window):
                        continue

                    existing_tx = VendorTransaction.query.filter_by(
                        booking_id=plan.booking_id,
                        milestone=milestone,
                    ).filter(VendorTransaction.status == VendorTransaction.STATUS_SUCCEEDED).first()
                    if existing_tx:
                        continue

                    booking = VendorBooking.query.get(plan.booking_id)
                    if not booking:
                        continue
                    lead = VendorLead.query.get(booking.lead_id)
                    if not lead:
                        continue

                    idempotency_key = f"payment:{rule.key}:{plan.booking_id}:{milestone}:{due_at.date().isoformat()}"
                    context = {
                        "client_name": lead.inquiry_name,
                        "payment_amount": _format_money(amount_cents),
                        "payment_due_date": due_at.strftime("%B %d, %Y"),
                        "wedding_date": booking.event_date.strftime("%B %d, %Y") if booking.event_date else "TBD",
                        "vendor_name": (Vendor.query.get(booking.vendor_id).business_name if Vendor.query.get(booking.vendor_id) else "Your vendor"),
                    }
                    if dry_run:
                        created += 1
                        continue
                    log = enqueue_template_email(
                        template=template,
                        recipient_email=lead.inquiry_email,
                        context=context,
                        idempotency_key=idempotency_key,
                        trigger_source=CommunicationLog.TRIGGER_AUTOMATION,
                        lifecycle_key=rule.key,
                        vendor_id=booking.vendor_id,
                        vendor_booking_id=booking.id,
                        automation_rule_id=rule.id,
                    )
                    if not getattr(log, "_was_existing", False):
                        created += 1

        elif rule.trigger_type == AutomationRule.TRIGGER_RSVP_SOFT_DEADLINE:
            pending_by_client: dict[int, list[ClientRsvpGuest]] = {}
            pending_guests = ClientRsvpGuest.query.filter_by(status=ClientRsvpGuest.STATUS_PENDING).all()
            for guest in pending_guests:
                pending_by_client.setdefault(guest.client_id, []).append(guest)

            for client_id, guests in pending_by_client.items():
                client = ClientUser.query.get(client_id)
                if not client:
                    continue
                booking = _latest_booking_for_client(client.id, client.email)
                if not booking or not booking.wedding_date:
                    continue

                soft_deadline_days = (rule.metadata_json or {}).get("soft_deadline_days_before", 30)
                soft_deadline = booking.wedding_date - timedelta(days=int(soft_deadline_days))
                if soft_deadline != current_time.date():
                    continue

                pending_count = len(guests)
                planning_pending_count = PlanningSubmission.query.filter_by(client_id=client.id).filter(
                    PlanningSubmission.status == PlanningSubmission.STATUS_PENDING
                ).count()

                idempotency_key = f"rsvp:{rule.key}:{client.id}:{soft_deadline.isoformat()}"
                context = {
                    "client_name": client.full_name or "Bride",
                    "wedding_date": booking.wedding_date.strftime("%B %d, %Y"),
                    "pending_rsvp_count": pending_count,
                    "planning_pending_count": planning_pending_count,
                }
                if dry_run:
                    created += 1
                    continue
                log = enqueue_template_email(
                    template=template,
                    recipient_email=client.email,
                    context=context,
                    idempotency_key=idempotency_key,
                    trigger_source=CommunicationLog.TRIGGER_AUTOMATION,
                    lifecycle_key=rule.key,
                    client_user_id=client.id,
                    booking_id=booking.id,
                    automation_rule_id=rule.id,
                )
                if not getattr(log, "_was_existing", False):
                    created += 1

        elif rule.trigger_type == AutomationRule.TRIGGER_WEDDING_COUNTDOWN:
            target_days = int(rule.trigger_offset_days or 0)
            bookings = BookingRequest.query.filter(
                BookingRequest.wedding_date.isnot(None),
                BookingRequest.status.in_([BookingRequest.STATUS_NEW, BookingRequest.STATUS_REVIEWING, BookingRequest.STATUS_CONFIRMED]),
            ).all()
            for booking in bookings:
                if not booking.wedding_date:
                    continue
                days_until = (booking.wedding_date - current_time.date()).days
                if days_until != target_days:
                    continue

                recipient_email = booking.email
                recipient_name = booking.couple_name or "Bride"
                milestone_label = "The Big Week" if target_days <= 7 else ("1 Month To Go" if target_days <= 30 else "6 Months To Go")
                idempotency_key = f"countdown:{rule.key}:{booking.id}:{booking.wedding_date.isoformat()}"
                context = {
                    "client_name": recipient_name,
                    "wedding_date": booking.wedding_date.strftime("%B %d, %Y"),
                    "countdown_label": milestone_label,
                    "days_remaining": days_until,
                }
                if dry_run:
                    created += 1
                    continue
                log = enqueue_template_email(
                    template=template,
                    recipient_email=recipient_email,
                    context=context,
                    idempotency_key=idempotency_key,
                    trigger_source=CommunicationLog.TRIGGER_AUTOMATION,
                    lifecycle_key=rule.key,
                    client_user_id=booking.client_id,
                    booking_id=booking.id,
                    automation_rule_id=rule.id,
                )
                if not getattr(log, "_was_existing", False):
                    created += 1

        elif rule.trigger_type == AutomationRule.TRIGGER_VENDOR_CONFIRMATION:
            target_days = int(rule.trigger_offset_days or 30)
            bookings = VendorBooking.query.filter(
                VendorBooking.event_date.isnot(None),
                VendorBooking.status.in_([VendorBooking.STATUS_TENTATIVE, VendorBooking.STATUS_CONFIRMED]),
            ).all()
            for booking in bookings:
                if not booking.event_date:
                    continue
                days_until = (booking.event_date - current_time.date()).days
                if days_until != target_days:
                    continue

                vendor_email, vendor_name = _resolve_vendor_contact(booking)
                if not vendor_email:
                    continue

                idempotency_key = f"vendor-confirm:{rule.key}:{booking.id}:{booking.event_date.isoformat()}"
                context = {
                    "vendor_name": vendor_name or "Vendor Partner",
                    "event_date": booking.event_date.strftime("%B %d, %Y"),
                    "arrival_time": booking.event_start_at.strftime("%I:%M %p") if booking.event_start_at else "TBD",
                    "client_name": VendorLead.query.get(booking.lead_id).inquiry_name if VendorLead.query.get(booking.lead_id) else "Client",
                }
                if dry_run:
                    created += 1
                    continue
                log = enqueue_template_email(
                    template=template,
                    recipient_email=vendor_email,
                    context=context,
                    idempotency_key=idempotency_key,
                    trigger_source=CommunicationLog.TRIGGER_AUTOMATION,
                    lifecycle_key=rule.key,
                    vendor_id=booking.vendor_id,
                    vendor_booking_id=booking.id,
                    automation_rule_id=rule.id,
                )
                if not getattr(log, "_was_existing", False):
                    created += 1

    if not dry_run:
        db.session.commit()

    return {"queued": created, "dry_run": dry_run}
