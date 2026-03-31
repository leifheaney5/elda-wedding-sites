from __future__ import annotations

from datetime import date, datetime, timedelta

from app.models.contact import ContactSubmission
from app.models.booking import BookingRequest
from app.models.service_request import ServiceRequest
from app.models.payment import Payment


def build_weekly_digest_data(week_ending: date, include_unpaid: bool = True) -> dict:
    week_start = week_ending - timedelta(days=6)
    start_dt = datetime.combine(week_start, datetime.min.time())
    end_dt = datetime.combine(week_ending, datetime.max.time())

    contacts = ContactSubmission.query.filter(
        ContactSubmission.submitted_at >= start_dt,
        ContactSubmission.submitted_at <= end_dt,
    ).all()
    bookings = BookingRequest.query.filter(
        BookingRequest.submitted_at >= start_dt,
        BookingRequest.submitted_at <= end_dt,
    ).all()
    services = ServiceRequest.query.filter(
        ServiceRequest.submitted_at >= start_dt,
        ServiceRequest.submitted_at <= end_dt,
    ).all()
    payments = Payment.query.filter(
        Payment.created_at >= start_dt,
        Payment.created_at <= end_dt,
    ).all()

    paid_revenue = sum(p.amount_cents for p in payments if p.status == Payment.STATUS_PAID)
    pending_revenue = sum(
        p.amount_cents for p in payments if p.status == Payment.STATUS_PENDING
    )

    effective_revenue = paid_revenue + pending_revenue if include_unpaid else paid_revenue

    days = [week_start + timedelta(days=i) for i in range(7)]
    daily = {
        "labels": [d.strftime("%a %b %d") for d in days],
        "contacts": [0] * 7,
        "bookings": [0] * 7,
        "services": [0] * 7,
        "revenue_dollars": [0.0] * 7,
    }

    day_index = {d: idx for idx, d in enumerate(days)}

    for item in contacts:
        if item.submitted_at and item.submitted_at.date() in day_index:
            daily["contacts"][day_index[item.submitted_at.date()]] += 1

    for item in bookings:
        if item.submitted_at and item.submitted_at.date() in day_index:
            daily["bookings"][day_index[item.submitted_at.date()]] += 1

    for item in services:
        if item.submitted_at and item.submitted_at.date() in day_index:
            daily["services"][day_index[item.submitted_at.date()]] += 1

    for item in payments:
        if not item.created_at or item.created_at.date() not in day_index:
            continue
        if item.status == Payment.STATUS_PAID or (
            include_unpaid and item.status == Payment.STATUS_PENDING
        ):
            idx = day_index[item.created_at.date()]
            daily["revenue_dollars"][idx] += round(item.amount_cents / 100, 2)

    booking_status = {
        BookingRequest.STATUS_NEW: 0,
        BookingRequest.STATUS_REVIEWING: 0,
        BookingRequest.STATUS_CONFIRMED: 0,
        BookingRequest.STATUS_CANCELLED: 0,
    }
    for item in bookings:
        if item.status in booking_status:
            booking_status[item.status] += 1

    total_leads = len(contacts) + len(bookings) + len(services)
    conversion_pct = round((len(bookings) / total_leads) * 100, 1) if total_leads else 0

    return {
        "week_start": week_start,
        "week_ending": week_ending,
        "include_unpaid": include_unpaid,
        "kpi": {
            "total_leads": total_leads,
            "contacts": len(contacts),
            "bookings": len(bookings),
            "services": len(services),
            "payments": len(payments),
            "paid_revenue_dollars": round(paid_revenue / 100, 2),
            "pending_revenue_dollars": round(pending_revenue / 100, 2),
            "effective_revenue_dollars": round(effective_revenue / 100, 2),
            "conversion_pct": conversion_pct,
            "unread_contacts": sum(1 for c in contacts if not c.is_read),
        },
        "booking_status": booking_status,
        "daily": daily,
        "max_daily": {
            "contacts": max(daily["contacts"]) if any(daily["contacts"]) else 1,
            "bookings": max(daily["bookings"]) if any(daily["bookings"]) else 1,
            "services": max(daily["services"]) if any(daily["services"]) else 1,
            "revenue": max(daily["revenue_dollars"]) if any(daily["revenue_dollars"]) else 1,
        },
    }
