from datetime import datetime, date, timedelta
import calendar
import csv
import re
from io import BytesIO
from io import StringIO
from functools import wraps
from flask import (
    Blueprint,
    Response,
    current_app,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    abort,
    send_file,
)
from flask_login import login_user, logout_user, login_required, current_user
from flask_limiter.util import get_remote_address
from app import db, limiter
from app.models.admin_user import AdminUser
from app.models.client_user import ClientUser
from app.models.contact import ContactSubmission, ContactAttachment
from app.models.booking import BookingRequest
from app.models.payment import Payment
from app.models.service_request import ServiceRequest
from app.models.client_inspiration import ClientInspiration
from app.models.client_plan_task import ClientPlanTask
from app.models.client_rsvp_guest import ClientRsvpGuest
from app.models.seating_plan import SeatingPlan
from app.models.site_announcement import SiteAnnouncement
from app.models.admin_audit_log import AdminAuditLog
from app.models.admin_automation_config import AdminAutomationConfig
from app.models.admin_report_template import AdminReportTemplate
from app.models.email_subscriber import EmailSubscriber
from app.models.email_template import EmailTemplate
from app.models.automation_rule import AutomationRule
from app.models.communication_log import CommunicationLog
from app.models.vendor import (
    Vendor,
    VendorPayoutAccount,
    VendorPackage,
    VendorLead,
    VendorQuote,
    VendorBooking,
    VendorPaymentPlan,
    VendorTransaction,
)
from app.services.attachments import build_contact_attachment
from app.services.admin_autopilot import get_admin_automation_config, run_admin_autopilot
from app.services.report_studio import DATASET_CONFIG, build_report, dataset_options, parse_fields
from app.services.communication_templates import ensure_default_email_templates
from app.services.communication_automation import evaluate_automation_rules
from app.services.communications import (
    enqueue_template_email,
    dispatch_due_communications,
    cancel_queued_communication,
    render_template_string,
)
from app.utils.email import send_bulk_message, automated_subscriber_update_content

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
def restrict_portal_to_admin_users():
    if request.endpoint in {"admin.login"}:
        return
    if not current_user.is_authenticated:
        return
    if getattr(current_user, "user_type", None) != "admin":
        abort(403)


def owner_required(f):
    """Restrict view to admin users with role='owner'."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_owner:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _find_inspiration_for_contact(submission: ContactSubmission) -> ClientInspiration | None:
    if submission.client_id:
        board = ClientInspiration.query.filter_by(client_id=submission.client_id).first()
        if board:
            return board
    if submission.email:
        user = ClientUser.query.filter_by(email=submission.email.strip().lower()).first()
        if user:
            return ClientInspiration.query.filter_by(client_id=user.id).first()
    return None


def _parse_table_layout(raw_layout: str) -> dict[str, list[str]]:
    layout: dict[str, list[str]] = {}
    for line in (raw_layout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            continue
        table_name, guests_raw = line.split(":", 1)
        guests = [guest.strip() for guest in guests_raw.split(",") if guest.strip()]
        table_name = table_name.strip()
        if table_name:
            layout[table_name] = guests
    return layout


def _extract_requested_event_date(raw_text: str | None) -> date | None:
    if not raw_text:
        return None

    date_patterns = [
        r"Event Date:\s*(\d{4}-\d{2}-\d{2})",
        r"Preferred Date:\s*(\d{4}-\d{2}-\d{2})",
        r"Requested (?:Call )?Date:\s*(\d{4}-\d{2}-\d{2})",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, raw_text, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
    return None


def _layout_to_text(layout_json: dict | None) -> str:
    if not layout_json or not isinstance(layout_json, dict):
        return ""
    lines = []
    for table_name, guests in layout_json.items():
        guest_list = guests if isinstance(guests, list) else []
        lines.append(f"{table_name}: {', '.join(str(g) for g in guest_list)}")
    return "\n".join(lines)


def _parse_rsvp(raw_rsvp: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (raw_rsvp or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            continue
        guest_name, status = line.split(":", 1)
        guest_name = guest_name.strip()
        status = status.strip()
        if guest_name:
            out[guest_name] = status
    return out


def _rsvp_to_text(rsvp_json: dict | None) -> str:
    if not rsvp_json or not isinstance(rsvp_json, dict):
        return ""
    return "\n".join(f"{guest}: {status}" for guest, status in rsvp_json.items())


def _normalize_rsvp_status(raw_status: str | None) -> str:
    allowed = {
        ClientRsvpGuest.STATUS_PENDING,
        ClientRsvpGuest.STATUS_ATTENDING,
        ClientRsvpGuest.STATUS_DECLINED,
        ClientRsvpGuest.STATUS_MAYBE,
    }
    normalized = (raw_status or "").strip().lower()
    if normalized in {"yes", "confirmed"}:
        return ClientRsvpGuest.STATUS_ATTENDING
    if normalized in {"no"}:
        return ClientRsvpGuest.STATUS_DECLINED
    return normalized if normalized in allowed else ClientRsvpGuest.STATUS_PENDING


def _rsvp_status_label(status: str) -> str:
    mapping = {
        ClientRsvpGuest.STATUS_ATTENDING: "Attending",
        ClientRsvpGuest.STATUS_PENDING: "Pending",
        ClientRsvpGuest.STATUS_DECLINED: "Declined",
        ClientRsvpGuest.STATUS_MAYBE: "Maybe",
    }
    return mapping.get(_normalize_rsvp_status(status), "Pending")


def _extract_guest_names_from_text(raw_text: str | None) -> list[str]:
    if not raw_text:
        return []

    names: list[str] = []
    seen: set[str] = set()
    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if ":" in cleaned:
            cleaned = cleaned.split(":", 1)[1].strip() or cleaned
        parts = [part.strip() for part in cleaned.split(",") if part.strip()]
        for part in parts:
            canonical = part.lower()
            if canonical in seen:
                continue
            if len(part) > 80:
                continue
            seen.add(canonical)
            names.append(part)
    return names


def _admin_login_rate_limit_key() -> str:
    email = (request.form.get("email") or "").strip().lower()
    remote = get_remote_address() or (request.remote_addr or "unknown")
    return f"{remote}:{email}" if email else remote


def _parse_optional_datetime_local(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _parse_optional_date(value: str | None) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


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


def _communication_template_preview(template: EmailTemplate, context: dict) -> dict:
    subject = render_template_string(template.subject_template, context)
    body = render_template_string(template.body_html_template, context)
    return {"subject": subject, "body_html": body}


def _report_studio_inputs(source) -> dict:
    dataset = (source.get("dataset") or "contacts").strip().lower()
    if dataset not in DATASET_CONFIG:
        dataset = "contacts"

    raw_fields = source.getlist("fields") if hasattr(source, "getlist") else []
    if not raw_fields:
        raw_fields = (source.get("fields") or "").split(",")

    selected_fields = parse_fields(dataset, raw_fields)
    status_filter = (source.get("status") or "all").strip().lower() or "all"
    date_start = _parse_optional_date(source.get("date_start"))
    date_end = _parse_optional_date(source.get("date_end"))
    viz_type = (source.get("viz_type") or "daily_volume").strip().lower()
    if viz_type not in {"daily_volume", "status_breakdown"}:
        viz_type = "daily_volume"

    return {
        "dataset": dataset,
        "selected_fields": selected_fields,
        "status_filter": status_filter,
        "date_start": date_start,
        "date_end": date_end,
        "viz_type": viz_type,
    }


def _record_admin_audit(
    *,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    detail: str | None = None,
) -> None:
    if not current_user.is_authenticated:
        return
    if getattr(current_user, "user_type", None) != "admin":
        return

    db.session.add(
        AdminAuditLog(
            admin_user_id=current_user.id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            detail=detail,
            ip_address=request.remote_addr,
        )
    )


def _weekly_report_payload(
    week_ending: date,
    include_unpaid: bool,
    service_type_filter: str,
):
    week_start = week_ending - timedelta(days=6)
    window_start = datetime.combine(week_start, datetime.min.time())
    window_end = datetime.combine(week_ending, datetime.max.time())

    contacts = ContactSubmission.query.filter(
        ContactSubmission.submitted_at >= window_start,
        ContactSubmission.submitted_at <= window_end,
    ).all()
    bookings = BookingRequest.query.filter(
        BookingRequest.submitted_at >= window_start,
        BookingRequest.submitted_at <= window_end,
    ).all()
    services_query = ServiceRequest.query.filter(
        ServiceRequest.submitted_at >= window_start,
        ServiceRequest.submitted_at <= window_end,
    )
    valid_service_types = {
        ServiceRequest.TYPE_PACKAGE,
        ServiceRequest.TYPE_VENUE,
        ServiceRequest.TYPE_CATERING,
        ServiceRequest.TYPE_FLORALS,
    }
    if service_type_filter in valid_service_types:
        services_query = services_query.filter(
            ServiceRequest.request_type == service_type_filter
        )
    services = services_query.all()

    payments = Payment.query.filter(
        Payment.created_at >= window_start,
        Payment.created_at <= window_end,
    ).all()
    paid_revenue_cents = sum(
        p.amount_cents for p in payments if p.status == Payment.STATUS_PAID
    )
    pending_revenue_cents = sum(
        p.amount_cents for p in payments if p.status == Payment.STATUS_PENDING
    )
    realized_revenue_cents = (
        paid_revenue_cents + pending_revenue_cents if include_unpaid else paid_revenue_cents
    )

    day_labels = []
    contacts_daily = []
    bookings_daily = []
    services_daily = []
    revenue_daily = []

    contacts_by_day = {d: 0 for d in [week_start + timedelta(days=i) for i in range(7)]}
    bookings_by_day = {d: 0 for d in [week_start + timedelta(days=i) for i in range(7)]}
    services_by_day = {d: 0 for d in [week_start + timedelta(days=i) for i in range(7)]}
    revenue_by_day = {d: 0 for d in [week_start + timedelta(days=i) for i in range(7)]}

    for item in contacts:
        if item.submitted_at:
            d = item.submitted_at.date()
            if d in contacts_by_day:
                contacts_by_day[d] += 1
    for item in bookings:
        if item.submitted_at:
            d = item.submitted_at.date()
            if d in bookings_by_day:
                bookings_by_day[d] += 1
    for item in services:
        if item.submitted_at:
            d = item.submitted_at.date()
            if d in services_by_day:
                services_by_day[d] += 1
    for item in payments:
        if not item.created_at:
            continue
        if item.status == Payment.STATUS_PAID or (
            include_unpaid and item.status == Payment.STATUS_PENDING
        ):
            d = item.created_at.date()
            if d in revenue_by_day:
                revenue_by_day[d] += item.amount_cents

    for i in range(7):
        d = week_start + timedelta(days=i)
        day_labels.append(d.strftime("%a %b %d"))
        contacts_daily.append(contacts_by_day[d])
        bookings_daily.append(bookings_by_day[d])
        services_daily.append(services_by_day[d])
        revenue_daily.append(round(revenue_by_day[d] / 100, 2))

    booking_status_counts = {
        BookingRequest.STATUS_NEW: 0,
        BookingRequest.STATUS_REVIEWING: 0,
        BookingRequest.STATUS_CONFIRMED: 0,
        BookingRequest.STATUS_CANCELLED: 0,
    }
    for item in bookings:
        if item.status in booking_status_counts:
            booking_status_counts[item.status] += 1

    service_mix_counts = {
        ServiceRequest.TYPE_PACKAGE: 0,
        ServiceRequest.TYPE_VENUE: 0,
        ServiceRequest.TYPE_CATERING: 0,
        ServiceRequest.TYPE_FLORALS: 0,
    }
    for item in services:
        if item.request_type in service_mix_counts:
            service_mix_counts[item.request_type] += 1

    total_leads = len(contacts) + len(bookings) + len(services)
    booking_conversion_pct = round((len(bookings) / total_leads) * 100, 1) if total_leads else 0
    unread_contacts = sum(1 for item in contacts if not item.is_read)
    confirmed_bookings = sum(
        1 for item in bookings if item.status == BookingRequest.STATUS_CONFIRMED
    )

    top_contacts = sorted(
        contacts,
        key=lambda x: x.submitted_at or datetime.min,
        reverse=True,
    )[:5]
    top_bookings = sorted(
        bookings,
        key=lambda x: x.submitted_at or datetime.min,
        reverse=True,
    )[:5]
    top_services = sorted(
        services,
        key=lambda x: x.submitted_at or datetime.min,
        reverse=True,
    )[:5]

    return {
        "week_start": week_start,
        "week_ending": week_ending,
        "include_unpaid": include_unpaid,
        "service_type_filter": service_type_filter,
        "day_labels": day_labels,
        "contacts_daily": contacts_daily,
        "bookings_daily": bookings_daily,
        "services_daily": services_daily,
        "revenue_daily": revenue_daily,
        "kpi": {
            "total_leads": total_leads,
            "contacts": len(contacts),
            "bookings": len(bookings),
            "services": len(services),
            "payments": len(payments),
            "paid_revenue_dollars": round(paid_revenue_cents / 100, 2),
            "pending_revenue_dollars": round(pending_revenue_cents / 100, 2),
            "realized_revenue_dollars": round(realized_revenue_cents / 100, 2),
            "booking_conversion_pct": booking_conversion_pct,
            "unread_contacts": unread_contacts,
            "confirmed_bookings": confirmed_bookings,
        },
        "booking_status_counts": booking_status_counts,
        "service_mix_counts": service_mix_counts,
        "top_contacts": top_contacts,
        "top_bookings": top_bookings,
        "top_services": top_services,
        "max_values": {
            "contacts": max(contacts_daily) if any(contacts_daily) else 1,
            "bookings": max(bookings_daily) if any(bookings_daily) else 1,
            "services": max(services_daily) if any(services_daily) else 1,
            "revenue": max(revenue_daily) if any(revenue_daily) else 1,
        },
    }


def _pct_delta(current_value: float, previous_value: float) -> float:
    if previous_value == 0:
        return 100.0 if current_value > 0 else 0.0
    return round(((current_value - previous_value) / previous_value) * 100, 1)


def _weekly_report_with_comparison(
    week_ending: date,
    include_unpaid: bool,
    service_type_filter: str,
):
    report = _weekly_report_payload(
        week_ending=week_ending,
        include_unpaid=include_unpaid,
        service_type_filter=service_type_filter,
    )
    previous = _weekly_report_payload(
        week_ending=week_ending - timedelta(days=7),
        include_unpaid=include_unpaid,
        service_type_filter=service_type_filter,
    )

    current_kpi = report["kpi"]
    previous_kpi = previous["kpi"]
    comparison = {
        "leads_pct": _pct_delta(current_kpi["total_leads"], previous_kpi["total_leads"]),
        "bookings_pct": _pct_delta(current_kpi["bookings"], previous_kpi["bookings"]),
        "revenue_pct": _pct_delta(
            current_kpi["realized_revenue_dollars"], previous_kpi["realized_revenue_dollars"]
        ),
        "conversion_pct": round(
            current_kpi["booking_conversion_pct"] - previous_kpi["booking_conversion_pct"],
            1,
        ),
        "confirmed_bookings_delta": current_kpi["confirmed_bookings"] - previous_kpi["confirmed_bookings"],
        "unread_contacts_delta": current_kpi["unread_contacts"] - previous_kpi["unread_contacts"],
    }

    actions = []
    if current_kpi["unread_contacts"] >= 8:
        actions.append(
            {
                "level": "high",
                "title": "Clear contact backlog",
                "detail": f"{current_kpi['unread_contacts']} unread contacts can impact conversion speed.",
                "url": url_for("admin.contacts", unread=1),
            }
        )
    if current_kpi["booking_conversion_pct"] < 20:
        actions.append(
            {
                "level": "medium",
                "title": "Review lead qualification workflow",
                "detail": "Booking conversion is below 20% this week.",
                "url": url_for("admin.bookings", status=BookingRequest.STATUS_NEW),
            }
        )
    if current_kpi["pending_revenue_dollars"] > current_kpi["paid_revenue_dollars"]:
        actions.append(
            {
                "level": "medium",
                "title": "Follow up on pending transactions",
                "detail": "Pending revenue exceeds paid revenue in this report window.",
                "url": url_for("admin.payments", status=Payment.STATUS_PENDING),
            }
        )
    if not actions:
        actions.append(
            {
                "level": "low",
                "title": "Operational cadence is healthy",
                "detail": "No urgent interventions identified this week.",
                "url": url_for("admin.dashboard"),
            }
        )

    report["comparison"] = comparison
    report["previous_window"] = {
        "week_start": previous["week_start"],
        "week_ending": previous["week_ending"],
    }
    report["actions"] = actions
    report["executive_summary"] = (
        f"{current_kpi['total_leads']} leads generated with "
        f"{current_kpi['bookings']} bookings and "
        f"${current_kpi['realized_revenue_dollars']:.2f} in reported revenue."
    )
    return report


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@admin_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(lambda: current_app.config.get("ADMIN_LOGIN_GET_LIMIT", "240 per hour"), methods=["GET"])
@limiter.limit(
    lambda: current_app.config.get("ADMIN_LOGIN_POST_LIMIT", "12 per 15 minutes"),
    methods=["POST"],
    key_func=_admin_login_rate_limit_key,
)
def login():
    if current_user.is_authenticated:
        if getattr(current_user, "user_type", None) == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("client.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = AdminUser.query.filter_by(email=email, is_active=True).first()
        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            _record_admin_audit(
                action="auth.login",
                entity_type="admin_user",
                entity_id=user.id,
                detail="Successful admin login",
            )
            db.session.commit()
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("admin.dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
@login_required
def logout():
    _record_admin_audit(
        action="auth.logout",
        entity_type="admin_user",
        entity_id=current_user.id,
        detail="Admin logout",
    )
    db.session.commit()
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("admin.login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@admin_bp.route("/")
@login_required
def dashboard():
    today = date.today()
    trend_window_options = [
        {"value": "1w", "label": "Last 1 week", "days": 7, "bucket": "day"},
        {"value": "1m", "label": "Last 1 month", "days": 30, "bucket": "day"},
        {"value": "3m", "label": "Last 3 months", "months": 3, "bucket": "month"},
        {"value": "6m", "label": "Last 6 months", "months": 6, "bucket": "month"},
        {"value": "12m", "label": "Last 12 months", "months": 12, "bucket": "month"},
        {"value": "18m", "label": "Last 18 months", "months": 18, "bucket": "month"},
    ]
    selected_window = request.args.get("window", "6m", type=str)
    selected_window_meta = next(
        (item for item in trend_window_options if item["value"] == selected_window),
        next(item for item in trend_window_options if item["value"] == "6m"),
    )
    selected_window = selected_window_meta["value"]

    stats = {
        "total_contacts": ContactSubmission.query.count(),
        "unread_contacts": ContactSubmission.query.filter_by(is_read=False).count(),
        "total_bookings": BookingRequest.query.count(),
        "new_bookings": BookingRequest.query.filter_by(
            status=BookingRequest.STATUS_NEW
        ).count(),
        "confirmed_bookings": BookingRequest.query.filter_by(
            status=BookingRequest.STATUS_CONFIRMED
        ).count(),
        "total_payments": Payment.query.filter_by(status=Payment.STATUS_PAID).count(),
        "pending_payments": Payment.query.filter_by(
            status=Payment.STATUS_PENDING
        ).count(),
        "failed_payments": Payment.query.filter_by(
            status=Payment.STATUS_FAILED
        ).count(),
        "total_revenue_cents": db.session.query(
            db.func.sum(Payment.amount_cents)
        )
        .filter_by(status=Payment.STATUS_PAID)
        .scalar()
        or 0,
        "pending_revenue_cents": db.session.query(
            db.func.sum(Payment.amount_cents)
        )
        .filter_by(status=Payment.STATUS_PENDING)
        .scalar()
        or 0,
        "service_requests": ServiceRequest.query.count(),
    }

    booking_status_counts = {
        BookingRequest.STATUS_NEW: BookingRequest.query.filter_by(
            status=BookingRequest.STATUS_NEW
        ).count(),
        BookingRequest.STATUS_REVIEWING: BookingRequest.query.filter_by(
            status=BookingRequest.STATUS_REVIEWING
        ).count(),
        BookingRequest.STATUS_CONFIRMED: BookingRequest.query.filter_by(
            status=BookingRequest.STATUS_CONFIRMED
        ).count(),
        BookingRequest.STATUS_CANCELLED: BookingRequest.query.filter_by(
            status=BookingRequest.STATUS_CANCELLED
        ).count(),
    }
    service_type_counts = {
        ServiceRequest.TYPE_PACKAGE: ServiceRequest.query.filter_by(
            request_type=ServiceRequest.TYPE_PACKAGE
        ).count(),
        ServiceRequest.TYPE_VENUE: ServiceRequest.query.filter_by(
            request_type=ServiceRequest.TYPE_VENUE
        ).count(),
        ServiceRequest.TYPE_CATERING: ServiceRequest.query.filter_by(
            request_type=ServiceRequest.TYPE_CATERING
        ).count(),
        ServiceRequest.TYPE_FLORALS: ServiceRequest.query.filter_by(
            request_type=ServiceRequest.TYPE_FLORALS
        ).count(),
    }

    total_leads = stats["total_contacts"] + stats["total_bookings"] + stats["service_requests"]
    lead_to_booking_rate = (
        (stats["total_bookings"] / total_leads) * 100 if total_leads else 0
    )
    booking_confirm_rate = (
        (stats["confirmed_bookings"] / stats["total_bookings"]) * 100
        if stats["total_bookings"]
        else 0
    )
    paid_revenue_cents = stats["total_revenue_cents"]
    avg_paid_ticket_cents = (
        int(round(paid_revenue_cents / stats["total_payments"]))
        if stats["total_payments"]
        else 0
    )

    trend_markers = []
    trend_labels = []
    trend_keys = []

    if selected_window_meta["bucket"] == "day":
        day_count = int(selected_window_meta["days"])
        start_day = today - timedelta(days=day_count - 1)
        marker = start_day
        while marker <= today:
            trend_markers.append(marker)
            trend_labels.append(marker.strftime("%b %d"))
            trend_keys.append(marker.strftime("%Y-%m-%d"))
            marker = marker + timedelta(days=1)
        trend_key_for_datetime = lambda value: value.strftime("%Y-%m-%d")
    else:
        marker = today.replace(day=1)
        for _ in range(int(selected_window_meta["months"])):
            trend_markers.append(marker)
            if marker.month == 1:
                marker = date(marker.year - 1, 12, 1)
            else:
                marker = date(marker.year, marker.month - 1, 1)
        trend_markers = sorted(trend_markers)
        trend_labels = [m.strftime("%b %Y") for m in trend_markers]
        trend_keys = [m.strftime("%Y-%m") for m in trend_markers]
        trend_key_for_datetime = lambda value: value.strftime("%Y-%m")

    trend_index = {k: idx for idx, k in enumerate(trend_keys)}

    leads_by_trend = [0] * len(trend_markers)
    contacts_by_trend = [0] * len(trend_markers)
    bookings_by_trend = [0] * len(trend_markers)
    services_by_trend = [0] * len(trend_markers)
    revenue_by_trend_cents = [0] * len(trend_markers)

    for c in ContactSubmission.query.with_entities(ContactSubmission.submitted_at):
        if not c.submitted_at:
            continue
        key = trend_key_for_datetime(c.submitted_at)
        if key in trend_index:
            idx = trend_index[key]
            contacts_by_trend[idx] += 1
            leads_by_trend[idx] += 1

    for b in BookingRequest.query.with_entities(BookingRequest.submitted_at):
        if not b.submitted_at:
            continue
        key = trend_key_for_datetime(b.submitted_at)
        if key in trend_index:
            idx = trend_index[key]
            bookings_by_trend[idx] += 1
            leads_by_trend[idx] += 1

    for s in ServiceRequest.query.with_entities(ServiceRequest.submitted_at):
        if not s.submitted_at:
            continue
        key = trend_key_for_datetime(s.submitted_at)
        if key in trend_index:
            idx = trend_index[key]
            services_by_trend[idx] += 1
            leads_by_trend[idx] += 1

    paid_payments = Payment.query.filter_by(status=Payment.STATUS_PAID).all()
    for p in paid_payments:
        dt = p.paid_at or p.created_at
        if not dt:
            continue
        key = trend_key_for_datetime(dt)
        if key in trend_index:
            revenue_by_trend_cents[trend_index[key]] += p.amount_cents

    upcoming_bookings = (
        BookingRequest.query.filter(
            BookingRequest.wedding_date.isnot(None),
            BookingRequest.wedding_date >= today,
        )
        .order_by(BookingRequest.wedding_date.asc())
        .limit(8)
        .all()
    )
    upcoming_service_events = (
        ServiceRequest.query.filter(
            ServiceRequest.event_date.isnot(None),
            ServiceRequest.event_date >= today,
        )
        .order_by(ServiceRequest.event_date.asc())
        .limit(8)
        .all()
    )
    recent_calendar_contacts = (
        ContactSubmission.query.filter(
            db.or_(
                ContactSubmission.services_interested == "sales_lead",
                ContactSubmission.services_interested.ilike("portal_message:request"),
                ContactSubmission.subject.ilike("%call%"),
                ContactSubmission.subject.ilike("%meeting%"),
                ContactSubmission.subject.ilike("%consult%"),
            )
        )
        .order_by(ContactSubmission.submitted_at.desc())
        .limit(60)
        .all()
    )

    upcoming_events = []
    for item in upcoming_bookings:
        upcoming_events.append(
            {
                "date": item.wedding_date,
                "title": item.couple_name,
                "subtitle": f"Wedding • {item.package_id or 'Custom package'}",
                "url": url_for("admin.booking_detail", id=item.id),
            }
        )
    for item in upcoming_service_events:
        upcoming_events.append(
            {
                "date": item.event_date,
                "title": item.name,
                "subtitle": f"{item.request_type.title()} request • {item.selected_service or 'Custom'}",
                "url": url_for("admin.service_request_detail", id=item.id),
            }
        )
    for item in recent_calendar_contacts:
        requested_date = _extract_requested_event_date(item.message)
        if not requested_date and item.submitted_at:
            requested_date = item.submitted_at.date()
        if not requested_date or requested_date < today:
            continue

        subject_text = (item.subject or "Meeting request").strip()
        if item.services_interested == "sales_lead":
            label = "Sales call"
        elif item.services_interested == "portal_message:request":
            label = "Portal request"
        else:
            label = "Meeting request"

        upcoming_events.append(
            {
                "date": requested_date,
                "title": f"{label}: {item.name}",
                "subtitle": subject_text,
                "url": url_for("admin.contact_detail", id=item.id),
            }
        )
    upcoming_events.sort(key=lambda e: e["date"] or today)
    upcoming_events = upcoming_events[:12]

    upcoming_weddings_30 = BookingRequest.query.filter(
        BookingRequest.wedding_date.isnot(None),
        BookingRequest.wedding_date >= today,
        BookingRequest.wedding_date <= (today + timedelta(days=30)),
    ).count()

    confirmed_with_dates = BookingRequest.query.filter(
        BookingRequest.status == BookingRequest.STATUS_CONFIRMED,
        BookingRequest.wedding_date.isnot(None),
    ).all()
    avg_days_to_wedding = 0
    if confirmed_with_dates:
        deltas = []
        for item in confirmed_with_dates:
            delta_days = (item.wedding_date - today).days
            if delta_days >= 0:
                deltas.append(delta_days)
        if deltas:
            avg_days_to_wedding = int(round(sum(deltas) / len(deltas)))

    top_service_type = "N/A"
    if any(service_type_counts.values()):
        top_service_type = max(service_type_counts, key=service_type_counts.get).title()

    priority_queue = []
    for item in (
        ContactSubmission.query.filter_by(is_read=False)
        .order_by(ContactSubmission.submitted_at.desc())
        .limit(6)
        .all()
    ):
        priority_queue.append(
            {
                "priority": "High",
                "priority_rank": 1,
                "title": f"Unread lead: {item.name}",
                "subtitle": item.email,
                "timestamp": item.submitted_at or datetime.min,
                "action_label": "Open contact",
                "url": url_for("admin.contact_detail", id=item.id),
            }
        )

    for item in (
        BookingRequest.query.filter_by(status=BookingRequest.STATUS_NEW)
        .order_by(BookingRequest.submitted_at.desc())
        .limit(6)
        .all()
    ):
        priority_queue.append(
            {
                "priority": "High",
                "priority_rank": 1,
                "title": f"New booking: {item.couple_name}",
                "subtitle": item.email,
                "timestamp": item.submitted_at or datetime.min,
                "action_label": "Review booking",
                "url": url_for("admin.booking_detail", id=item.id),
            }
        )

    for item in (
        ServiceRequest.query.filter(
            ServiceRequest.status.in_(
                [ServiceRequest.STATUS_NEW, ServiceRequest.STATUS_REVIEWING]
            )
        )
        .order_by(ServiceRequest.submitted_at.desc())
        .limit(6)
        .all()
    ):
        priority_queue.append(
            {
                "priority": "Medium",
                "priority_rank": 2,
                "title": f"Open service request: {item.name}",
                "subtitle": f"{item.request_type.title()} • {item.status.title()}",
                "timestamp": item.submitted_at or datetime.min,
                "action_label": "Open request",
                "url": url_for("admin.service_request_detail", id=item.id),
            }
        )

    for item in (
        Payment.query.filter_by(status=Payment.STATUS_PENDING)
        .order_by(Payment.created_at.desc())
        .limit(6)
        .all()
    ):
        priority_queue.append(
            {
                "priority": "Medium",
                "priority_rank": 2,
                "title": f"Pending transaction #{item.id}",
                "subtitle": f"${item.amount_dollars:.2f}",
                "timestamp": item.created_at or datetime.min,
                "action_label": "Open payments",
                "url": url_for("admin.payments", status=Payment.STATUS_PENDING),
            }
        )

    priority_queue.sort(
        key=lambda item: (item["priority_rank"], -(item["timestamp"].timestamp() if item["timestamp"] != datetime.min else 0))
    )
    priority_queue = priority_queue[:10]

    command_center_actions = [
        {
            "title": "Triage unread leads",
            "detail": "Respond to new inquiries first to maximize conversion speed.",
            "url": url_for("admin.contacts", unread=1),
            "cta": "Open lead inbox",
        },
        {
            "title": "Advance booking pipeline",
            "detail": "Move new bookings into reviewing or confirmed with one pass.",
            "url": url_for("admin.bookings", status=BookingRequest.STATUS_NEW),
            "cta": "Open new bookings",
        },
        {
            "title": "Clear pending transactions",
            "detail": "Follow up on pending payments and close daily revenue gaps.",
            "url": url_for("admin.payments", status=Payment.STATUS_PENDING),
            "cta": "Open pending payments",
        },
    ]

    reminders = []
    if stats["unread_contacts"] > 0:
        reminders.append(
            {
                "level": "high",
                "title": "Unread contact messages",
                "detail": f"{stats['unread_contacts']} lead(s) need a response.",
                "url": url_for("admin.contacts", unread=1),
            }
        )
    if stats["new_bookings"] > 0:
        reminders.append(
            {
                "level": "high",
                "title": "New booking requests",
                "detail": f"{stats['new_bookings']} booking(s) are waiting for review.",
                "url": url_for("admin.bookings", status=BookingRequest.STATUS_NEW),
            }
        )
    if stats["pending_payments"] > 0:
        reminders.append(
            {
                "level": "medium",
                "title": "Pending transactions",
                "detail": f"{stats['pending_payments']} payment(s) still pending.",
                "url": url_for("admin.payments", status=Payment.STATUS_PENDING),
            }
        )
    open_service_requests = ServiceRequest.query.filter(
        ServiceRequest.status.in_(
            [ServiceRequest.STATUS_NEW, ServiceRequest.STATUS_REVIEWING]
        )
    ).count()
    if open_service_requests > 0:
        reminders.append(
            {
                "level": "medium",
                "title": "Open service requests",
                "detail": f"{open_service_requests} request(s) need follow-up.",
                "url": url_for("admin.service_requests", status="open"),
            }
        )
    if upcoming_weddings_30 > 0:
        reminders.append(
            {
                "level": "low",
                "title": "Upcoming weddings in 30 days",
                "detail": f"{upcoming_weddings_30} wedding date(s) are approaching.",
                "url": url_for("admin.bookings", status=BookingRequest.STATUS_CONFIRMED),
            }
        )

    # Current month calendar grid with event count per day.
    cal = calendar.Calendar(firstweekday=6)
    month_weeks = cal.monthdatescalendar(today.year, today.month)
    day_event_counts: dict[date, int] = {}
    for event in upcoming_events:
        if event["date"] and event["date"].month == today.month and event["date"].year == today.year:
            day_event_counts[event["date"]] = day_event_counts.get(event["date"], 0) + 1

    calendar_weeks = []
    for week in month_weeks:
        row = []
        for day in week:
            row.append(
                {
                    "day": day.day,
                    "is_current_month": day.month == today.month,
                    "is_today": day == today,
                    "event_count": day_event_counts.get(day, 0),
                }
            )
        calendar_weeks.append(row)

    recent_contacts = (
        ContactSubmission.query.order_by(ContactSubmission.submitted_at.desc())
        .limit(5)
        .all()
    )
    recent_bookings = (
        BookingRequest.query.order_by(BookingRequest.submitted_at.desc())
        .limit(5)
        .all()
    )
    recent_payments = (
        Payment.query.order_by(Payment.created_at.desc()).limit(5).all()
    )
    recent_service_requests = (
        ServiceRequest.query.order_by(ServiceRequest.submitted_at.desc()).limit(5).all()
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        total_leads=total_leads,
        lead_to_booking_rate=round(lead_to_booking_rate, 1),
        booking_confirm_rate=round(booking_confirm_rate, 1),
        avg_paid_ticket_dollars=round(avg_paid_ticket_cents / 100, 2),
        avg_days_to_wedding=avg_days_to_wedding,
        top_service_type=top_service_type,
        open_service_requests=open_service_requests,
        upcoming_weddings_30=upcoming_weddings_30,
        booking_status_counts=booking_status_counts,
        service_type_counts=service_type_counts,
        month_labels=trend_labels,
        leads_by_month=leads_by_trend,
        contacts_by_month=contacts_by_trend,
        bookings_by_month=bookings_by_trend,
        services_by_month=services_by_trend,
        revenue_by_month_dollars=[round(v / 100, 2) for v in revenue_by_trend_cents],
        reminders=reminders,
        upcoming_events=upcoming_events,
        calendar_weeks=calendar_weeks,
        month_title=today.strftime("%B %Y"),
        recent_contacts=recent_contacts,
        recent_bookings=recent_bookings,
        recent_payments=recent_payments,
        recent_service_requests=recent_service_requests,
        selected_window=selected_window,
        selected_window_label=selected_window_meta["label"],
        trend_window_options=trend_window_options,
        priority_queue=priority_queue,
        high_priority_count=sum(1 for item in priority_queue if item["priority"] == "High"),
        command_center_actions=command_center_actions,
    )


@admin_bp.route("/site-manager")
@login_required
def site_manager():
    announcements = SiteAnnouncement.query.order_by(SiteAnnouncement.created_at.desc()).all()
    return render_template("admin/site_manager.html", announcements=announcements)


@admin_bp.route("/autopilot", methods=["GET", "POST"])
@login_required
def autopilot():
    config = get_admin_automation_config()

    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()

        if action == "save-settings":
            if not current_user.is_owner:
                abort(403)

            config.is_enabled = bool(request.form.get("is_enabled"))
            config.auto_mark_stale_bookings_reviewing = bool(
                request.form.get("auto_mark_stale_bookings_reviewing")
            )
            config.stale_booking_days = max(
                1, request.form.get("stale_booking_days", type=int) or 3
            )
            config.unread_contacts_threshold = max(
                1, request.form.get("unread_contacts_threshold", type=int) or 8
            )
            config.open_service_requests_threshold = max(
                1, request.form.get("open_service_requests_threshold", type=int) or 8
            )
            config.pending_payments_threshold = max(
                1, request.form.get("pending_payments_threshold", type=int) or 5
            )
            config.updated_by_id = current_user.id

            _record_admin_audit(
                action="autopilot.settings.updated",
                entity_type="admin_autopilot",
                entity_id=config.id,
            )
            db.session.commit()
            flash("Autopilot settings updated.", "success")
            return redirect(url_for("admin.autopilot"))

        if action == "run-now":
            result = run_admin_autopilot(
                trigger="manual",
                actor_admin_user_id=current_user.id,
            )
            flash(
                "Autopilot run complete. "
                f"Auto-transitioned stale bookings: {result['auto_transitioned_to_reviewing']}",
                "success",
            )
            return redirect(url_for("admin.autopilot"))

        flash("Unsupported autopilot action.", "error")
        return redirect(url_for("admin.autopilot"))

    recent_runs = (
        AdminAuditLog.query.filter_by(action="autopilot.run")
        .order_by(AdminAuditLog.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "admin/autopilot.html",
        config=config,
        recent_runs=recent_runs,
    )


@admin_bp.route("/vendors")
@login_required
def vendors():
    records = Vendor.query.order_by(Vendor.created_at.desc()).all()
    vendor_rows = []
    total_gross_cents = 0
    total_net_cents = 0

    for vendor in records:
        lead_count = VendorLead.query.filter_by(vendor_id=vendor.id).count()
        quote_count = VendorQuote.query.filter_by(vendor_id=vendor.id).count()
        booking_count = VendorBooking.query.filter_by(vendor_id=vendor.id).count()
        package_count = VendorPackage.query.filter_by(vendor_id=vendor.id).count()
        payout = VendorPayoutAccount.query.filter_by(vendor_id=vendor.id).first()
        succeeded_tx = VendorTransaction.query.filter_by(
            vendor_id=vendor.id,
            status=VendorTransaction.STATUS_SUCCEEDED,
        ).all()

        gross_cents = sum(item.gross_cents for item in succeeded_tx)
        net_cents = sum(item.vendor_net_cents for item in succeeded_tx)
        total_gross_cents += gross_cents
        total_net_cents += net_cents

        vendor_rows.append(
            {
                "vendor": vendor,
                "lead_count": lead_count,
                "quote_count": quote_count,
                "booking_count": booking_count,
                "package_count": package_count,
                "gross_cents": gross_cents,
                "net_cents": net_cents,
                "payout": payout,
            }
        )

    return render_template(
        "admin/vendors.html",
        vendor_rows=vendor_rows,
        vendor_count=len(records),
        active_count=sum(1 for v in records if v.status == Vendor.STATUS_ACTIVE),
        suspended_count=sum(1 for v in records if v.status == Vendor.STATUS_SUSPENDED),
        total_gross_dollars=round(total_gross_cents / 100, 2),
        total_net_dollars=round(total_net_cents / 100, 2),
    )


@admin_bp.route("/vendors/<int:vendor_id>")
@login_required
def vendor_detail(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    payout = VendorPayoutAccount.query.filter_by(vendor_id=vendor_id).first()
    rule = VendorPaymentPlan.query.join(
        VendorBooking, VendorBooking.id == VendorPaymentPlan.booking_id
    ).filter(VendorBooking.vendor_id == vendor_id)

    recent_leads = (
        VendorLead.query.filter_by(vendor_id=vendor_id)
        .order_by(VendorLead.created_at.desc())
        .limit(6)
        .all()
    )
    recent_quotes = (
        VendorQuote.query.filter_by(vendor_id=vendor_id)
        .order_by(VendorQuote.created_at.desc())
        .limit(6)
        .all()
    )
    recent_bookings = (
        VendorBooking.query.filter_by(vendor_id=vendor_id)
        .order_by(VendorBooking.created_at.desc())
        .limit(6)
        .all()
    )
    recent_transactions = (
        VendorTransaction.query.filter_by(vendor_id=vendor_id)
        .order_by(VendorTransaction.created_at.desc())
        .limit(8)
        .all()
    )

    return render_template(
        "admin/vendor_detail.html",
        vendor=vendor,
        payout=payout,
        payment_plan_count=rule.count(),
        package_count=VendorPackage.query.filter_by(vendor_id=vendor_id).count(),
        recent_leads=recent_leads,
        recent_quotes=recent_quotes,
        recent_bookings=recent_bookings,
        recent_transactions=recent_transactions,
    )


@admin_bp.route("/vendors/<int:vendor_id>/status", methods=["POST"])
@login_required
@owner_required
def vendor_status(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    next_status = (request.form.get("status") or "").strip().lower()
    valid_status = {Vendor.STATUS_DRAFT, Vendor.STATUS_ACTIVE, Vendor.STATUS_SUSPENDED}
    if next_status not in valid_status:
        flash("Invalid vendor status.", "error")
        return redirect(url_for("admin.vendor_detail", vendor_id=vendor_id))

    vendor.status = next_status
    db.session.commit()
    flash("Vendor status updated.", "success")
    return redirect(url_for("admin.vendor_detail", vendor_id=vendor_id))


@admin_bp.route("/site-manager/announcements", methods=["POST"])
@login_required
def create_site_announcement():
    title = request.form.get("title", "").strip()
    message = request.form.get("message", "").strip()
    starts_at = _parse_optional_datetime_local(request.form.get("starts_at"))
    ends_at = _parse_optional_datetime_local(request.form.get("ends_at"))
    is_active = bool(request.form.get("is_active"))

    if not title or not message:
        flash("Title and message are required.", "error")
        return redirect(url_for("admin.site_manager"))

    if starts_at and ends_at and ends_at < starts_at:
        flash("End date must be after the start date.", "error")
        return redirect(url_for("admin.site_manager"))

    announcement = SiteAnnouncement(
        title=title,
        message=message,
        starts_at=starts_at,
        ends_at=ends_at,
        is_active=is_active,
        created_by_id=getattr(current_user, "id", None),
    )
    db.session.add(announcement)
    db.session.commit()
    flash("Announcement posted.", "success")
    return redirect(url_for("admin.site_manager"))


@admin_bp.route("/site-manager/announcements/<int:id>/toggle", methods=["POST"])
@login_required
def toggle_site_announcement(id):
    announcement = SiteAnnouncement.query.get_or_404(id)
    announcement.is_active = not announcement.is_active
    db.session.commit()
    flash(
        f"Announcement {'activated' if announcement.is_active else 'paused'}.",
        "success",
    )
    return redirect(url_for("admin.site_manager"))


@admin_bp.route("/site-manager/announcements/<int:id>/delete", methods=["POST"])
@login_required
def delete_site_announcement(id):
    announcement = SiteAnnouncement.query.get_or_404(id)
    db.session.delete(announcement)
    db.session.commit()
    flash("Announcement deleted.", "success")
    return redirect(url_for("admin.site_manager"))


# ---------------------------------------------------------------------------
# Contact Submissions
# ---------------------------------------------------------------------------

@admin_bp.route("/contacts")
@login_required
def contacts():
    page = request.args.get("page", 1, type=int)
    filter_unread = request.args.get("unread")
    source = request.args.get("source", "").strip().lower()
    q = request.args.get("q", "").strip()
    query = ContactSubmission.query.order_by(ContactSubmission.submitted_at.desc())
    if filter_unread:
        query = query.filter_by(is_read=False)
    if source == "portal":
        query = query.filter(
            db.or_(
                ContactSubmission.services_interested.ilike("portal_message:%"),
                ContactSubmission.subject.ilike("Portal %"),
            )
        )
    if q:
        term = f"%{q}%"
        query = query.filter(
            db.or_(
                ContactSubmission.name.ilike(term),
                ContactSubmission.email.ilike(term),
                ContactSubmission.subject.ilike(term),
            )
        )
    submissions = query.paginate(page=page, per_page=20)
    board_links: dict[int, int] = {}
    for item in submissions.items:
        board = _find_inspiration_for_contact(item)
        if board:
            board_links[item.id] = board.id
    return render_template(
        "admin/contacts.html",
        submissions=submissions,
        unread=bool(filter_unread),
        source=source,
        board_links=board_links,
        q=q,
    )


@admin_bp.route("/contacts/<int:id>")
@login_required
def contact_detail(id):
    submission = ContactSubmission.query.get_or_404(id)
    if not submission.is_read:
        submission.is_read = True
        db.session.commit()
    inspiration_board = _find_inspiration_for_contact(submission)
    email_norm = (submission.email or "").strip().lower()
    thread_items = (
        ContactSubmission.query.filter(ContactSubmission.email.ilike(email_norm))
        .filter(ContactSubmission.subject.ilike("Portal %"))
        .order_by(ContactSubmission.submitted_at.desc())
        .limit(30)
        .all()
        if email_norm
        else []
    )
    return render_template(
        "admin/contact_detail.html",
        submission=submission,
        inspiration_board=inspiration_board,
        thread_items=thread_items,
    )


@admin_bp.route("/contacts/<int:id>/notes", methods=["POST"])
@login_required
def contact_notes(id):
    submission = ContactSubmission.query.get_or_404(id)
    submission.admin_notes = request.form.get("notes", "")
    _record_admin_audit(
        action="contact.notes.updated",
        entity_type="contact_submission",
        entity_id=submission.id,
    )
    db.session.commit()
    flash("Notes saved.", "success")
    return redirect(url_for("admin.contact_detail", id=id))


@admin_bp.route("/contacts/<int:id>/reply", methods=["POST"])
@login_required
def contact_reply(id):
    source = ContactSubmission.query.get_or_404(id)
    msg_type = request.form.get("message_type", "update").strip().lower()
    subject = request.form.get("subject", "").strip()
    message = request.form.get("message", "").strip()
    valid_types = {"question", "feedback", "request", "update", "urgent"}
    if msg_type not in valid_types:
        msg_type = "update"

    if not message:
        flash("Reply message cannot be empty.", "error")
        return redirect(url_for("admin.contact_detail", id=id))

    reply = ContactSubmission(
        client_id=source.client_id,
        name=current_user.name,
        email=source.email,
        phone=None,
        subject=f"Portal {msg_type.title()}: {subject or 'Planner Reply'}",
        services_interested=f"portal_message:admin_reply:{msg_type}",
        message=message,
        is_read=False,
    )
    db.session.add(reply)
    db.session.flush()

    uploaded_any = False
    for file_obj in request.files.getlist("attachments"):
        if not file_obj or not file_obj.filename:
            continue
        result = build_contact_attachment(
            file_obj=file_obj,
            submission_id=reply.id,
            uploaded_by="admin",
        )
        if result.error == "type":
            flash(f"File type not allowed: {result.filename}", "error")
            continue
        if result.error == "size":
            flash(f"File too large (max 8MB): {result.filename}", "error")
            continue
        if result.error:
            flash(f"Attachment upload failed: {result.filename or 'unknown file'}", "error")
            continue

        db.session.add(result.attachment)
        uploaded_any = True

    _record_admin_audit(
        action="contact.reply.sent",
        entity_type="contact_submission",
        entity_id=source.id,
        detail=f"type={msg_type};attachments={'yes' if uploaded_any else 'no'}",
    )
    db.session.commit()
    flash(
        "Reply sent to client portal."
        + (" Attachments were included." if uploaded_any else ""),
        "success",
    )
    return redirect(url_for("admin.contact_detail", id=id))


@admin_bp.route("/contacts/attachments/<int:attachment_id>/download")
@login_required
def download_contact_attachment(attachment_id):
    attachment = ContactAttachment.query.get_or_404(attachment_id)
    return send_file(
        BytesIO(attachment.data),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=attachment.filename,
    )


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

@admin_bp.route("/bookings")
@login_required
def bookings():
    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status")
    q = request.args.get("q", "").strip()
    query = BookingRequest.query.order_by(BookingRequest.submitted_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    if q:
        term = f"%{q}%"
        query = query.filter(
            db.or_(
                BookingRequest.couple_name.ilike(term),
                BookingRequest.email.ilike(term),
                BookingRequest.package_id.ilike(term),
            )
        )
    bookings_page = query.paginate(page=page, per_page=20)
    return render_template(
        "admin/bookings.html",
        bookings=bookings_page,
        status_filter=status_filter,
        q=q,
        statuses=[
            BookingRequest.STATUS_NEW,
            BookingRequest.STATUS_REVIEWING,
            BookingRequest.STATUS_CONFIRMED,
            BookingRequest.STATUS_CANCELLED,
        ],
    )


@admin_bp.route("/bookings/<int:id>")
@login_required
def booking_detail(id):
    booking = BookingRequest.query.get_or_404(id)
    planning_client_id = booking.client_id
    if not planning_client_id and booking.email:
        matched_client = ClientUser.query.filter_by(
            email=booking.email.strip().lower()
        ).first()
        planning_client_id = matched_client.id if matched_client else None
    return render_template(
        "admin/booking_detail.html",
        booking=booking,
        planning_client_id=planning_client_id,
    )


@admin_bp.route("/bookings/<int:id>/status", methods=["POST"])
@login_required
def booking_status(id):
    booking = BookingRequest.query.get_or_404(id)
    new_status = request.form.get("status")
    previous_status = booking.status
    valid = [
        BookingRequest.STATUS_NEW,
        BookingRequest.STATUS_REVIEWING,
        BookingRequest.STATUS_CONFIRMED,
        BookingRequest.STATUS_CANCELLED,
    ]
    if new_status in valid:
        booking.status = new_status
        _record_admin_audit(
            action="booking.status.updated",
            entity_type="booking_request",
            entity_id=booking.id,
            detail=f"{previous_status}->{new_status}",
        )
        db.session.commit()
        flash(f"Booking status updated to '{new_status}'.", "success")
    return redirect(url_for("admin.booking_detail", id=id))


@admin_bp.route("/bookings/<int:id>/notes", methods=["POST"])
@login_required
def booking_notes(id):
    booking = BookingRequest.query.get_or_404(id)
    booking.admin_notes = request.form.get("notes", "")
    _record_admin_audit(
        action="booking.notes.updated",
        entity_type="booking_request",
        entity_id=booking.id,
    )
    db.session.commit()
    flash("Notes saved.", "success")
    return redirect(url_for("admin.booking_detail", id=id))


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

@admin_bp.route("/payments")
@login_required
def payments():
    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "").strip()
    query = Payment.query.order_by(Payment.created_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    payments_page = query.paginate(
        page=page, per_page=20
    )
    summary = {
        "paid_count": Payment.query.filter_by(status=Payment.STATUS_PAID).count(),
        "pending_count": Payment.query.filter_by(
            status=Payment.STATUS_PENDING
        ).count(),
        "failed_count": Payment.query.filter_by(status=Payment.STATUS_FAILED).count(),
        "refunded_count": Payment.query.filter_by(
            status=Payment.STATUS_REFUNDED
        ).count(),
        "paid_revenue_cents": db.session.query(db.func.sum(Payment.amount_cents))
        .filter_by(status=Payment.STATUS_PAID)
        .scalar()
        or 0,
    }
    return render_template(
        "admin/payments.html",
        payments=payments_page,
        status_filter=status_filter,
        summary=summary,
        statuses=[
            Payment.STATUS_PENDING,
            Payment.STATUS_PAID,
            Payment.STATUS_FAILED,
            Payment.STATUS_REFUNDED,
        ],
    )


@admin_bp.route("/service-requests")
@login_required
def service_requests():
    page = request.args.get("page", 1, type=int)
    request_type = request.args.get("type", "").strip()
    status_filter = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip()

    query = ServiceRequest.query.order_by(ServiceRequest.submitted_at.desc())
    if request_type:
        query = query.filter_by(request_type=request_type)
    if status_filter == "open":
        query = query.filter(
            ServiceRequest.status.in_(
                [ServiceRequest.STATUS_NEW, ServiceRequest.STATUS_REVIEWING]
            )
        )
    elif status_filter:
        query = query.filter_by(status=status_filter)
    if q:
        term = f"%{q}%"
        query = query.filter(
            db.or_(
                ServiceRequest.name.ilike(term),
                ServiceRequest.email.ilike(term),
                ServiceRequest.selected_service.ilike(term),
            )
        )

    page_obj = query.paginate(page=page, per_page=20)
    return render_template(
        "admin/service_requests.html",
        requests_page=page_obj,
        request_type=request_type,
        status_filter=status_filter,
        q=q,
        types=[
            ServiceRequest.TYPE_PACKAGE,
            ServiceRequest.TYPE_VENUE,
            ServiceRequest.TYPE_CATERING,
            ServiceRequest.TYPE_FLORALS,
        ],
        statuses=[
            "open",
            ServiceRequest.STATUS_NEW,
            ServiceRequest.STATUS_REVIEWING,
            ServiceRequest.STATUS_CONTACTED,
            ServiceRequest.STATUS_CLOSED,
        ],
    )


@admin_bp.route("/service-requests/<int:id>")
@login_required
def service_request_detail(id):
    item = ServiceRequest.query.get_or_404(id)
    return render_template("admin/service_request_detail.html", item=item)


@admin_bp.route("/service-requests/<int:id>/status", methods=["POST"])
@login_required
def service_request_status(id):
    item = ServiceRequest.query.get_or_404(id)
    new_status = request.form.get("status")
    previous_status = item.status
    valid = [
        ServiceRequest.STATUS_NEW,
        ServiceRequest.STATUS_REVIEWING,
        ServiceRequest.STATUS_CONTACTED,
        ServiceRequest.STATUS_CLOSED,
    ]
    if new_status in valid:
        item.status = new_status
        _record_admin_audit(
            action="service_request.status.updated",
            entity_type="service_request",
            entity_id=item.id,
            detail=f"{previous_status}->{new_status}",
        )
        db.session.commit()
        flash("Service request status updated.", "success")
    return redirect(url_for("admin.service_request_detail", id=id))


@admin_bp.route("/service-requests/<int:id>/notes", methods=["POST"])
@login_required
def service_request_notes(id):
    item = ServiceRequest.query.get_or_404(id)
    item.admin_notes = request.form.get("notes", "")
    _record_admin_audit(
        action="service_request.notes.updated",
        entity_type="service_request",
        entity_id=item.id,
    )
    db.session.commit()
    flash("Notes saved.", "success")
    return redirect(url_for("admin.service_request_detail", id=id))


@admin_bp.route("/inspiration-boards")
@login_required
def inspiration_boards():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()

    query = ClientInspiration.query.join(ClientInspiration.client).order_by(
        ClientInspiration.updated_at.desc()
    )
    if q:
        term = f"%{q}%"
        query = query.filter(
            db.or_(
                ClientInspiration.colors.ilike(term),
                ClientInspiration.themes.ilike(term),
                ClientInspiration.florals.ilike(term),
                ClientInspiration.notes.ilike(term),
                ClientUser.email.ilike(term),
                ClientUser.full_name.ilike(term),
            )
        )

    boards = query.paginate(page=page, per_page=20)
    return render_template("admin/inspiration_boards.html", boards=boards, q=q)


@admin_bp.route("/inspiration-boards/<int:id>")
@login_required
def inspiration_board_detail(id):
    board = ClientInspiration.query.get_or_404(id)
    return render_template("admin/inspiration_board_detail.html", board=board)


@admin_bp.route("/planning-ops", methods=["GET", "POST"])
@login_required
def planning_ops():
    clients = ClientUser.query.order_by(
        db.func.coalesce(ClientUser.full_name, ClientUser.email).asc()
    ).all()

    selected_client_id = request.args.get("client_id", type=int)
    if request.method == "POST":
        selected_client_id = request.form.get("client_id", type=int) or selected_client_id
    if not selected_client_id and clients:
        selected_client_id = clients[0].id

    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()
        if not selected_client_id:
            flash("Please select a client first.", "error")
            return redirect(url_for("admin.planning_ops"))

        if action == "add-logistics-task":
            title = (request.form.get("title") or "").strip()
            category = (request.form.get("category") or "").strip() or "Logistics"
            due_date_raw = (request.form.get("due_date") or "").strip()
            notes = (request.form.get("notes") or "").strip() or None
            is_required = bool(request.form.get("is_required"))

            if not title:
                flash("Task title is required.", "error")
            else:
                parsed_due = None
                if due_date_raw:
                    try:
                        parsed_due = datetime.strptime(due_date_raw, "%Y-%m-%d").date()
                    except ValueError:
                        parsed_due = None

                db.session.add(
                    ClientPlanTask(
                        client_id=selected_client_id,
                        title=title,
                        category=category,
                        due_date=parsed_due,
                        notes=notes,
                        is_required=is_required,
                        is_completed=False,
                    )
                )
                db.session.commit()
                flash("Logistics task added.", "success")

        elif action == "toggle-logistics-task":
            task_id = request.form.get("task_id", type=int)
            task = ClientPlanTask.query.filter_by(
                id=task_id, client_id=selected_client_id
            ).first_or_404()
            task.is_completed = not task.is_completed
            db.session.commit()
            flash("Task status updated.", "success")

        elif action == "save-seating-plan":
            plan_id = request.form.get("plan_id", type=int)
            title = (request.form.get("title") or "").strip() or "Seating Plan"
            venue_area = (request.form.get("venue_area") or "").strip() or None
            final_guest_count = request.form.get("final_guest_count", type=int) or 0
            notes = (request.form.get("notes") or "").strip() or None
            table_layout_json = _parse_table_layout(request.form.get("table_layout") or "")
            rsvp_json = _parse_rsvp(request.form.get("rsvp_status") or "")

            client_obj = ClientUser.query.get_or_404(selected_client_id)
            latest_booking = (
                BookingRequest.query.filter(
                    db.or_(
                        BookingRequest.client_id == client_obj.id,
                        BookingRequest.email.ilike(client_obj.email),
                    )
                )
                .order_by(BookingRequest.submitted_at.desc())
                .first()
            )

            if plan_id:
                plan = SeatingPlan.query.filter_by(
                    id=plan_id, client_id=selected_client_id
                ).first_or_404()
            else:
                plan = SeatingPlan(client_id=selected_client_id)
                db.session.add(plan)

            plan.booking_id = latest_booking.id if latest_booking else None
            plan.title = title
            plan.venue_area = venue_area
            plan.final_guest_count = max(final_guest_count, 0)
            plan.table_layout_json = table_layout_json or None
            plan.rsvp_json = rsvp_json or None
            plan.notes = notes

            if table_layout_json:
                guest_map = {
                    item.full_name.strip().lower(): item
                    for item in ClientRsvpGuest.query.filter_by(client_id=selected_client_id).all()
                }
                for table_name, guest_names in table_layout_json.items():
                    if not isinstance(guest_names, list):
                        continue
                    for guest_name in guest_names:
                        key = str(guest_name or "").strip().lower()
                        if key in guest_map:
                            guest_map[key].table_name = table_name

            if rsvp_json:
                guest_map = {
                    item.full_name.strip().lower(): item
                    for item in ClientRsvpGuest.query.filter_by(client_id=selected_client_id).all()
                }
                for guest_name, raw_status in rsvp_json.items():
                    key = str(guest_name or "").strip().lower()
                    if key not in guest_map:
                        continue
                    guest = guest_map[key]
                    normalized = _normalize_rsvp_status(raw_status)
                    if guest.status != normalized and normalized != ClientRsvpGuest.STATUS_PENDING:
                        guest.responded_at = datetime.utcnow()
                    guest.status = normalized

            db.session.commit()
            flash("Seating plan saved.", "success")

        elif action == "add-rsvp-guest":
            full_name = (request.form.get("full_name") or "").strip()
            email = (request.form.get("email") or "").strip().lower() or None
            phone = (request.form.get("phone") or "").strip() or None
            group_label = (request.form.get("group_label") or "").strip() or None

            if not full_name:
                flash("RSVP guest name is required.", "error")
            else:
                duplicate = ClientRsvpGuest.query.filter_by(
                    client_id=selected_client_id,
                    full_name=full_name,
                ).first()
                if duplicate:
                    flash("That RSVP guest already exists.", "info")
                else:
                    db.session.add(
                        ClientRsvpGuest(
                            client_id=selected_client_id,
                            full_name=full_name,
                            email=email,
                            phone=phone,
                            group_label=group_label,
                            status=ClientRsvpGuest.STATUS_PENDING,
                        )
                    )
                    db.session.commit()
                    flash("RSVP guest added.", "success")

        elif action == "update-rsvp-guest":
            guest_id = request.form.get("guest_id", type=int)
            guest = ClientRsvpGuest.query.filter_by(
                id=guest_id,
                client_id=selected_client_id,
            ).first_or_404()
            new_status = _normalize_rsvp_status(request.form.get("status"))
            previous_status = guest.status

            guest.meal_choice = (request.form.get("meal_choice") or "").strip() or None
            guest.notes = (request.form.get("notes") or "").strip() or None
            guest.table_name = (request.form.get("table_name") or "").strip() or None
            guest.status = new_status
            if new_status != ClientRsvpGuest.STATUS_PENDING and previous_status != new_status:
                guest.responded_at = datetime.utcnow()
            db.session.commit()
            flash("RSVP guest updated.", "success")

        elif action == "delete-rsvp-guest":
            guest_id = request.form.get("guest_id", type=int)
            guest = ClientRsvpGuest.query.filter_by(
                id=guest_id,
                client_id=selected_client_id,
            ).first_or_404()
            db.session.delete(guest)
            db.session.commit()
            flash("RSVP guest deleted.", "success")

        elif action == "sync-rsvp-from-seating":
            seating_messages = (
                ContactSubmission.query.filter(
                    db.or_(
                        ContactSubmission.client_id == selected_client_id,
                        ContactSubmission.subject.ilike("%seating%"),
                    )
                )
                .filter(
                    db.or_(
                        ContactSubmission.services_interested == "portal_message:seating_list",
                        ContactSubmission.message.ilike("%guest list%"),
                    )
                )
                .order_by(ContactSubmission.submitted_at.desc())
                .limit(20)
                .all()
            )
            existing = {
                item.full_name.strip().lower()
                for item in ClientRsvpGuest.query.filter_by(client_id=selected_client_id).all()
            }
            created_count = 0
            for message in seating_messages:
                for guest_name in _extract_guest_names_from_text(message.message):
                    canonical = guest_name.strip().lower()
                    if not canonical or canonical in existing:
                        continue
                    db.session.add(
                        ClientRsvpGuest(
                            client_id=selected_client_id,
                            full_name=guest_name.strip(),
                            status=ClientRsvpGuest.STATUS_PENDING,
                        )
                    )
                    existing.add(canonical)
                    created_count += 1
            db.session.commit()
            flash(f"RSVP sync complete. Added {created_count} guest(s).", "success")

        elif action == "send-rsvp-checkin":
            client_obj = ClientUser.query.get_or_404(selected_client_id)
            guests = (
                ClientRsvpGuest.query.filter_by(client_id=selected_client_id)
                .order_by(ClientRsvpGuest.full_name.asc())
                .all()
            )
            counts = {
                ClientRsvpGuest.STATUS_ATTENDING: 0,
                ClientRsvpGuest.STATUS_PENDING: 0,
                ClientRsvpGuest.STATUS_DECLINED: 0,
                ClientRsvpGuest.STATUS_MAYBE: 0,
            }
            for guest in guests:
                counts[_normalize_rsvp_status(guest.status)] += 1

            subject = "ELDA Wedding Sites RSVP Check-In"
            body = (
                f"Hello {client_obj.full_name or 'Client'},\n\n"
                "Here is your latest RSVP status snapshot:\n"
                f"- Attending: {counts[ClientRsvpGuest.STATUS_ATTENDING]}\n"
                f"- Pending: {counts[ClientRsvpGuest.STATUS_PENDING]}\n"
                f"- Declined: {counts[ClientRsvpGuest.STATUS_DECLINED]}\n"
                f"- Maybe: {counts[ClientRsvpGuest.STATUS_MAYBE]}\n\n"
                "Please log into your client portal to update any pending guests.\n"
                f"{url_for('client.plan', _external=True)}\n\n"
                "ELDA Wedding Sites Planning Team"
            )
            result = send_bulk_message(
                recipients=[client_obj.email],
                subject=subject,
                body=body,
                sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
            )
            if result.get("sent"):
                now_dt = datetime.utcnow()
                for guest in guests:
                    if not guest.invited_at:
                        guest.invited_at = now_dt
                db.session.commit()
            flash(
                "RSVP check-in sent to client."
                if result.get("sent")
                else "RSVP check-in failed. Check SMTP credentials.",
                "success" if result.get("sent") else "error",
            )

        elif action == "delete-seating-plan":
            plan_id = request.form.get("plan_id", type=int)
            plan = SeatingPlan.query.filter_by(
                id=plan_id, client_id=selected_client_id
            ).first_or_404()
            db.session.delete(plan)
            db.session.commit()
            flash("Seating plan deleted.", "success")

        else:
            flash("Unknown planning operation.", "error")

        return redirect(url_for("admin.planning_ops", client_id=selected_client_id))

    selected_client = (
        ClientUser.query.get(selected_client_id) if selected_client_id else None
    )
    tasks = []
    progress_percent = 0
    completed_count = 0
    total_count = 0
    overdue_count = 0
    due_soon_count = 0
    seating_plans = []
    active_plan = None
    active_layout_text = ""
    active_rsvp_text = ""
    active_booking = None
    workflow_labels = ["Completed", "Open", "Overdue", "Due in 30 Days"]
    workflow_values = [0, 0, 0, 0]
    category_labels: list[str] = []
    category_values: list[int] = []
    due_labels = ["Overdue", "Due in 7 Days", "Due in 30 Days", "Future", "No Due Date"]
    due_values = [0, 0, 0, 0, 0]
    seating_table_labels: list[str] = []
    seating_table_values: list[int] = []
    rsvp_labels = ["Attending", "Pending", "Declined", "Other"]
    rsvp_values = [0, 0, 0, 0]
    seating_source_guest_lines: list[str] = []
    rsvp_guests: list[ClientRsvpGuest] = []
    rsvp_pending_long_count = 0

    if selected_client:
        tasks = (
            ClientPlanTask.query.filter_by(client_id=selected_client.id)
            .order_by(
                ClientPlanTask.is_completed.asc(),
                ClientPlanTask.due_date.asc(),
                ClientPlanTask.created_at.asc(),
            )
            .all()
        )
        total_count = len(tasks)
        completed_count = sum(1 for task in tasks if task.is_completed)
        progress_percent = int((completed_count / total_count) * 100) if total_count else 0

        today = date.today()
        overdue_count = sum(
            1
            for task in tasks
            if (not task.is_completed and task.due_date and task.due_date < today)
        )
        due_soon_count = sum(
            1
            for task in tasks
            if (
                not task.is_completed
                and task.due_date
                and today <= task.due_date <= (today + timedelta(days=30))
            )
        )
        open_count = max(total_count - completed_count, 0)
        workflow_values = [completed_count, open_count, overdue_count, due_soon_count]

        category_counts: dict[str, int] = {}
        for task in tasks:
            category_key = (task.category or "General").strip() or "General"
            category_counts[category_key] = category_counts.get(category_key, 0) + 1
        sorted_categories = sorted(
            category_counts.items(), key=lambda item: item[1], reverse=True
        )[:8]
        category_labels = [item[0] for item in sorted_categories]
        category_values = [item[1] for item in sorted_categories]

        for task in tasks:
            if task.is_completed:
                continue
            if not task.due_date:
                due_values[4] += 1
                continue
            days_until_due = (task.due_date - today).days
            if days_until_due < 0:
                due_values[0] += 1
            elif days_until_due <= 7:
                due_values[1] += 1
            elif days_until_due <= 30:
                due_values[2] += 1
            else:
                due_values[3] += 1

        seating_plans = (
            SeatingPlan.query.filter_by(client_id=selected_client.id)
            .order_by(SeatingPlan.updated_at.desc())
            .all()
        )

        active_plan_id = request.args.get("plan_id", type=int)
        active_plan = next(
            (plan for plan in seating_plans if plan.id == active_plan_id),
            seating_plans[0] if seating_plans else None,
        )
        if active_plan:
            active_layout_text = _layout_to_text(active_plan.table_layout_json)
            active_rsvp_text = _rsvp_to_text(active_plan.rsvp_json)
            layout_data = active_plan.table_layout_json if isinstance(active_plan.table_layout_json, dict) else {}
            seating_table_labels = list(layout_data.keys())[:12]
            seating_table_values = [
                len(layout_data.get(table_name, []))
                if isinstance(layout_data.get(table_name, []), list)
                else 0
                for table_name in seating_table_labels
            ]

            rsvp_data = active_plan.rsvp_json if isinstance(active_plan.rsvp_json, dict) else {}
            for raw_status in rsvp_data.values():
                status = str(raw_status or "").strip().lower()
                if status in {"attending", "yes", "confirmed"}:
                    rsvp_values[0] += 1
                elif status in {"pending", "maybe", "awaiting"}:
                    rsvp_values[1] += 1
                elif status in {"declined", "no", "cannot attend"}:
                    rsvp_values[2] += 1
                else:
                    rsvp_values[3] += 1

        rsvp_guests = (
            ClientRsvpGuest.query.filter_by(client_id=selected_client.id)
            .order_by(ClientRsvpGuest.full_name.asc())
            .all()
        )
        if rsvp_guests:
            active_rsvp_text = "\n".join(
                f"{guest.full_name}: {_rsvp_status_label(guest.status)}" for guest in rsvp_guests
            )
            rsvp_values = [0, 0, 0, 0]
            for guest in rsvp_guests:
                normalized = _normalize_rsvp_status(guest.status)
                if normalized == ClientRsvpGuest.STATUS_ATTENDING:
                    rsvp_values[0] += 1
                elif normalized == ClientRsvpGuest.STATUS_PENDING:
                    rsvp_values[1] += 1
                elif normalized == ClientRsvpGuest.STATUS_DECLINED:
                    rsvp_values[2] += 1
                else:
                    rsvp_values[3] += 1
                if normalized == ClientRsvpGuest.STATUS_PENDING and guest.created_at <= datetime.utcnow() - timedelta(days=14):
                    rsvp_pending_long_count += 1

        active_booking = (
            BookingRequest.query.filter(
                db.or_(
                    BookingRequest.client_id == selected_client.id,
                    BookingRequest.email.ilike(selected_client.email),
                )
            )
            .order_by(BookingRequest.submitted_at.desc())
            .first()
        )

        seating_messages = (
            ContactSubmission.query.filter(
                db.or_(
                    ContactSubmission.client_id == selected_client.id,
                    ContactSubmission.email.ilike(selected_client.email),
                )
            )
            .filter(
                db.or_(
                    ContactSubmission.services_interested == "portal_message:seating_list",
                    ContactSubmission.subject.ilike("%seating%"),
                    ContactSubmission.message.ilike("%guest list%"),
                )
            )
            .order_by(ContactSubmission.submitted_at.desc())
            .limit(20)
            .all()
        )
        for item in seating_messages:
            for name in _extract_guest_names_from_text(item.message):
                if name not in seating_source_guest_lines:
                    seating_source_guest_lines.append(name)

    return render_template(
        "admin/planning_ops.html",
        clients=clients,
        selected_client=selected_client,
        tasks=tasks,
        progress_percent=progress_percent,
        completed_count=completed_count,
        total_count=total_count,
        overdue_count=overdue_count,
        due_soon_count=due_soon_count,
        seating_plans=seating_plans,
        active_plan=active_plan,
        active_layout_text=active_layout_text,
        active_rsvp_text=active_rsvp_text,
        active_booking=active_booking,
        workflow_labels=workflow_labels,
        workflow_values=workflow_values,
        category_labels=category_labels,
        category_values=category_values,
        due_labels=due_labels,
        due_values=due_values,
        seating_table_labels=seating_table_labels,
        seating_table_values=seating_table_values,
        rsvp_labels=rsvp_labels,
        rsvp_values=rsvp_values,
        seating_source_guest_lines=seating_source_guest_lines,
        rsvp_guests=rsvp_guests,
        rsvp_pending_long_count=rsvp_pending_long_count,
        rsvp_status_options=[
            (ClientRsvpGuest.STATUS_PENDING, "Pending"),
            (ClientRsvpGuest.STATUS_ATTENDING, "Attending"),
            (ClientRsvpGuest.STATUS_DECLINED, "Declined"),
            (ClientRsvpGuest.STATUS_MAYBE, "Maybe"),
        ],
    )


@admin_bp.route("/email-campaigns", methods=["GET", "POST"])
@login_required
def email_campaigns():
    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()
        batch_size = max(1, current_app.config.get("EMAIL_CAMPAIGN_BATCH_SIZE", 500))

        if action == "send-automated-update":
            subject, body, html = automated_subscriber_update_content()
            subscribers = (
                EmailSubscriber.query.filter_by(is_active=True)
                .order_by(EmailSubscriber.subscribed_at.asc())
                .limit(batch_size)
                .all()
            )
            result = send_bulk_message(
                recipients=[item.email for item in subscribers],
                subject=subject,
                body=body,
                html=html,
                sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
            )
            if result.get("recipient_count", 0) > 0:
                now_dt = datetime.utcnow()
                for item in subscribers:
                    item.last_email_sent_at = now_dt
                db.session.commit()
            flash(
                f"Automated update sent to {result.get('recipient_count', 0)} subscriber(s).",
                "success" if result.get("sent") else "error",
            )

        elif action == "send-custom-email":
            subject = (request.form.get("subject") or "").strip()
            body = (request.form.get("body") or "").strip()
            audience = (request.form.get("audience") or "active").strip().lower()
            test_email = (request.form.get("test_email") or "").strip().lower()

            if not subject or not body:
                flash("Custom email requires subject and message body.", "error")
                return redirect(url_for("admin.email_campaigns"))

            recipients: list[str] = []
            if audience == "test":
                if not test_email:
                    flash("Provide a test recipient email.", "error")
                    return redirect(url_for("admin.email_campaigns"))
                recipients = [test_email]
            else:
                subscribers = (
                    EmailSubscriber.query.filter_by(is_active=True)
                    .order_by(EmailSubscriber.subscribed_at.asc())
                    .limit(batch_size)
                    .all()
                )
                recipients = [item.email for item in subscribers]

            result = send_bulk_message(
                recipients=recipients,
                subject=subject,
                body=body,
                sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
            )
            if audience != "test" and result.get("recipient_count", 0) > 0:
                now_dt = datetime.utcnow()
                EmailSubscriber.query.filter(
                    EmailSubscriber.email.in_(recipients)
                ).update({EmailSubscriber.last_email_sent_at: now_dt}, synchronize_session=False)
                db.session.commit()

            flash(
                f"Custom email sent to {result.get('recipient_count', 0)} recipient(s).",
                "success" if result.get("sent") else "error",
            )

        else:
            flash("Unknown email campaign action.", "error")

        return redirect(url_for("admin.email_campaigns"))

    subscribers = (
        EmailSubscriber.query.order_by(EmailSubscriber.subscribed_at.desc())
        .limit(200)
        .all()
    )
    summary = {
        "active_count": EmailSubscriber.query.filter_by(is_active=True).count(),
        "inactive_count": EmailSubscriber.query.filter_by(is_active=False).count(),
        "never_contacted_count": EmailSubscriber.query.filter(
            EmailSubscriber.is_active == True,
            EmailSubscriber.last_email_sent_at.is_(None),
        ).count(),
    }
    return render_template(
        "admin/email_campaigns.html",
        subscribers=subscribers,
        summary=summary,
        default_sender=current_app.config.get("MAIL_DEFAULT_SENDER", "info@eldaweddingsites.example"),
    )


@admin_bp.route("/communications-center", methods=["GET", "POST"])
@login_required
def communications_center():
    ensure_default_email_templates()

    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()

        if action == "run-automation-now":
            queued_result = evaluate_automation_rules()
            sent_result = dispatch_due_communications(limit=200)
            flash(
                "Automation run complete "
                f"(queued={queued_result.get('queued', 0)}, sent={sent_result.get('sent', 0)}, failed={sent_result.get('failed', 0)}).",
                "success",
            )
            return redirect(url_for("admin.communications_center"))

        if action == "cancel-queued-email":
            log_id = request.form.get("log_id", type=int)
            log = CommunicationLog.query.get_or_404(log_id)
            if cancel_queued_communication(log):
                _record_admin_audit(
                    action="communications.cancel",
                    entity_type="communication_log",
                    entity_id=log.id,
                    detail=f"recipient={log.recipient_email}",
                )
                db.session.commit()
                flash("Queued email cancelled.", "success")
            else:
                flash("Only queued emails can be cancelled.", "error")
            return redirect(url_for("admin.communications_center"))

        if action == "send-template":
            template_id = request.form.get("template_id", type=int)
            template = EmailTemplate.query.get_or_404(template_id)

            recipient_type = (request.form.get("recipient_type") or "client").strip().lower()
            custom_recipient_email = (request.form.get("custom_recipient_email") or "").strip().lower()
            client_id = request.form.get("client_id", type=int)
            vendor_booking_id = request.form.get("vendor_booking_id", type=int)
            payment_id = request.form.get("payment_id", type=int)
            custom_message = (request.form.get("custom_message") or "").strip()

            subject_override = (request.form.get("subject_override") or "").strip() or None
            body_override = (request.form.get("body_override") or "").strip() or None
            send_now = (request.form.get("send_now") or "").strip().lower() == "true"

            recipient_email = ""
            recipient_name = ""
            booking = None
            vendor_booking = None
            context = {
                "custom_message": custom_message,
                "payment_amount": "",
                "wedding_date": "TBD",
                "event_date": "TBD",
                "client_name": "",
                "vendor_name": "",
                "arrival_time": "TBD",
            }

            if recipient_type == "client":
                client = ClientUser.query.get_or_404(client_id)
                booking = _latest_booking_for_client(client.id, client.email)
                recipient_email = client.email
                recipient_name = client.full_name or client.email
                context["client_name"] = recipient_name
                if booking and booking.wedding_date:
                    context["wedding_date"] = booking.wedding_date.strftime("%B %d, %Y")

            elif recipient_type == "vendor-booking":
                vendor_booking = VendorBooking.query.get_or_404(vendor_booking_id)
                vendor = Vendor.query.get(vendor_booking.vendor_id)
                lead = VendorLead.query.get(vendor_booking.lead_id)
                if not lead:
                    flash("Selected vendor booking is missing lead contact email.", "error")
                    return redirect(url_for("admin.communications_center"))
                recipient_email = lead.inquiry_email
                recipient_name = lead.inquiry_name
                context["client_name"] = lead.inquiry_name
                context["vendor_name"] = vendor.business_name if vendor else "Vendor"
                if vendor_booking.event_date:
                    context["event_date"] = vendor_booking.event_date.strftime("%B %d, %Y")
                if vendor_booking.event_start_at:
                    context["arrival_time"] = vendor_booking.event_start_at.strftime("%I:%M %p")

            else:
                recipient_email = custom_recipient_email
                recipient_name = custom_recipient_email

            if not recipient_email:
                flash("Recipient email is required.", "error")
                return redirect(url_for("admin.communications_center"))

            payment = Payment.query.get(payment_id) if payment_id else None
            if payment:
                context["payment_amount"] = f"USD {payment.amount_dollars:,.2f}"

            if booking and booking.wedding_date:
                context["event_date"] = booking.wedding_date.strftime("%B %d, %Y")

            subject_preview = render_template_string(subject_override or template.subject_template, context)
            body_preview = render_template_string(body_override or template.body_html_template, context)
            if request.form.get("preview_only"):
                flash("Preview updated below. No email queued.", "info")
                templates = EmailTemplate.query.filter_by(is_active=True).order_by(EmailTemplate.name.asc()).all()
                queued_logs = (
                    CommunicationLog.query.filter_by(status=CommunicationLog.STATUS_QUEUED)
                    .order_by(CommunicationLog.scheduled_for.asc())
                    .limit(100)
                    .all()
                )
                recent_logs = (
                    CommunicationLog.query.order_by(CommunicationLog.created_at.desc())
                    .limit(100)
                    .all()
                )
                return render_template(
                    "admin/communications_center.html",
                    templates=templates,
                    queued_logs=queued_logs,
                    recent_logs=recent_logs,
                    clients=ClientUser.query.order_by(ClientUser.created_at.desc()).limit(150).all(),
                    vendor_bookings=VendorBooking.query.order_by(VendorBooking.created_at.desc()).limit(150).all(),
                    automation_rules=AutomationRule.query.order_by(AutomationRule.name.asc()).all(),
                    selected_template=template,
                    preview_subject=subject_preview,
                    preview_body=body_preview,
                    default_undo_minutes=current_app.config.get("EMAIL_COMMUNICATION_UNDO_MINUTES", 5),
                )

            undo_minutes = max(0, current_app.config.get("EMAIL_COMMUNICATION_UNDO_MINUTES", 5))
            scheduled_for = datetime.utcnow() if send_now else (datetime.utcnow() + timedelta(minutes=undo_minutes))

            log = enqueue_template_email(
                template=template,
                recipient_email=recipient_email,
                context=context,
                idempotency_key=(
                    f"manual:{template.id}:{recipient_email}:{scheduled_for.strftime('%Y%m%d%H%M')}:{current_user.id}"
                ),
                scheduled_for=scheduled_for,
                trigger_source=CommunicationLog.TRIGGER_MANUAL,
                lifecycle_key="manual_template_send",
                client_user_id=client_id if recipient_type == "client" else None,
                vendor_id=vendor_booking.vendor_id if vendor_booking else None,
                vendor_booking_id=vendor_booking.id if vendor_booking else None,
                booking_id=booking.id if booking else None,
                payment_id=payment.id if payment else None,
                created_by_admin_id=current_user.id,
                subject_template_override=subject_override,
                body_html_template_override=body_override,
                body_markdown_template_override=body_override,
            )
            db.session.commit()
            _record_admin_audit(
                action="communications.manual_send_queued",
                entity_type="communication_log",
                entity_id=log.id,
                detail=f"template={template.key};recipient={recipient_email};scheduled_for={log.scheduled_for.isoformat()}",
            )
            db.session.commit()

            flash(
                "Email queued for delivery now."
                if send_now
                else f"Email queued with {undo_minutes}-minute undo buffer.",
                "success",
            )
            return redirect(url_for("admin.communications_center"))

        flash("Unknown communication action.", "error")
        return redirect(url_for("admin.communications_center"))

    templates = EmailTemplate.query.filter_by(is_active=True).order_by(EmailTemplate.name.asc()).all()
    selected_template = templates[0] if templates else None
    default_context = {
        "client_name": "Demo Client",
        "wedding_date": "June 21, 2026",
        "payment_amount": "USD 1,500.00",
        "event_date": "June 21, 2026",
        "vendor_name": "Demo Vendor",
        "arrival_time": "03:00 PM",
        "custom_message": "Please update this message before sending.",
    }
    preview = _communication_template_preview(selected_template, default_context) if selected_template else {"subject": "", "body_html": ""}

    queued_logs = (
        CommunicationLog.query.filter_by(status=CommunicationLog.STATUS_QUEUED)
        .order_by(CommunicationLog.scheduled_for.asc())
        .limit(100)
        .all()
    )
    recent_logs = (
        CommunicationLog.query.order_by(CommunicationLog.created_at.desc())
        .limit(100)
        .all()
    )
    return render_template(
        "admin/communications_center.html",
        templates=templates,
        queued_logs=queued_logs,
        recent_logs=recent_logs,
        clients=ClientUser.query.order_by(ClientUser.created_at.desc()).limit(150).all(),
        vendor_bookings=VendorBooking.query.order_by(VendorBooking.created_at.desc()).limit(150).all(),
        automation_rules=AutomationRule.query.order_by(AutomationRule.name.asc()).all(),
        selected_template=selected_template,
        preview_subject=preview["subject"],
        preview_body=preview["body_html"],
        default_undo_minutes=current_app.config.get("EMAIL_COMMUNICATION_UNDO_MINUTES", 5),
    )


@admin_bp.route("/how-do-i")
@login_required
def how_do_i():
    return render_template("admin/how_do_i.html")


def _csv_response(filename: str, rows: list[list[str]]):
    sio = StringIO()
    writer = csv.writer(sio)
    writer.writerows(rows)
    return Response(
        sio.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_bp.route("/exports/contacts.csv")
@login_required
def export_contacts_csv():
    rows = [[
        "id",
        "name",
        "email",
        "phone",
        "subject",
        "services_interested",
        "submitted_at",
        "is_read",
    ]]
    for item in ContactSubmission.query.order_by(ContactSubmission.submitted_at.desc()):
        rows.append(
            [
                item.id,
                item.name,
                item.email,
                item.phone or "",
                item.subject or "",
                item.services_interested or "",
                item.submitted_at.isoformat() if item.submitted_at else "",
                "yes" if item.is_read else "no",
            ]
        )
    return _csv_response("contacts_export.csv", rows)


@admin_bp.route("/exports/bookings.csv")
@login_required
def export_bookings_csv():
    rows = [
        [
            "id",
            "couple_name",
            "email",
            "phone",
            "wedding_date",
            "package_id",
            "guest_count",
            "status",
            "submitted_at",
        ]
    ]
    for item in BookingRequest.query.order_by(BookingRequest.submitted_at.desc()):
        rows.append(
            [
                item.id,
                item.couple_name,
                item.email,
                item.phone or "",
                item.wedding_date.isoformat() if item.wedding_date else "",
                item.package_id or "",
                item.guest_count or "",
                item.status,
                item.submitted_at.isoformat() if item.submitted_at else "",
            ]
        )
    return _csv_response("bookings_export.csv", rows)


@admin_bp.route("/exports/payments.csv")
@login_required
def export_payments_csv():
    rows = [
        [
            "id",
            "booking_id",
            "stripe_payment_intent_id",
            "amount_cents",
            "currency",
            "status",
            "description",
            "paid_at",
            "created_at",
        ]
    ]
    for item in Payment.query.order_by(Payment.created_at.desc()):
        rows.append(
            [
                item.id,
                item.booking_id or "",
                item.stripe_payment_intent_id or "",
                item.amount_cents,
                item.currency,
                item.status,
                item.description or "",
                item.paid_at.isoformat() if item.paid_at else "",
                item.created_at.isoformat() if item.created_at else "",
            ]
        )
    return _csv_response("payments_export.csv", rows)


@admin_bp.route("/exports/service_requests.csv")
@login_required
def export_service_requests_csv():
    rows = [
        [
            "id",
            "request_type",
            "name",
            "email",
            "phone",
            "event_date",
            "guest_count",
            "selected_service",
            "status",
            "submitted_at",
        ]
    ]
    for item in ServiceRequest.query.order_by(ServiceRequest.submitted_at.desc()):
        rows.append(
            [
                item.id,
                item.request_type,
                item.name,
                item.email,
                item.phone or "",
                item.event_date.isoformat() if item.event_date else "",
                item.guest_count or "",
                item.selected_service or "",
                item.status,
                item.submitted_at.isoformat() if item.submitted_at else "",
            ]
        )
    return _csv_response("service_requests_export.csv", rows)


@admin_bp.route("/reports/weekly")
@login_required
def weekly_report():
    week_ending = _parse_optional_date(request.args.get("week_ending")) or date.today()
    include_unpaid = bool(request.args.get("include_unpaid"))
    service_type_filter = request.args.get("service_type", "all").strip().lower() or "all"
    report = _weekly_report_with_comparison(
        week_ending=week_ending,
        include_unpaid=include_unpaid,
        service_type_filter=service_type_filter,
    )
    return render_template(
        "admin/weekly_report.html",
        report=report,
        filter_week_ending=week_ending.isoformat(),
        filter_include_unpaid=include_unpaid,
        filter_service_type=service_type_filter,
        service_type_options=[
            "all",
            ServiceRequest.TYPE_PACKAGE,
            ServiceRequest.TYPE_VENUE,
            ServiceRequest.TYPE_CATERING,
            ServiceRequest.TYPE_FLORALS,
        ],
    )


@admin_bp.route("/reports/weekly/export.csv")
@login_required
def weekly_report_export_csv():
    week_ending = _parse_optional_date(request.args.get("week_ending")) or date.today()
    include_unpaid = bool(request.args.get("include_unpaid"))
    service_type_filter = request.args.get("service_type", "all").strip().lower() or "all"
    report = _weekly_report_with_comparison(
        week_ending=week_ending,
        include_unpaid=include_unpaid,
        service_type_filter=service_type_filter,
    )

    rows = [["metric", "value"]]
    rows.extend(
        [
            ["window_start", report["week_start"].isoformat()],
            ["window_end", report["week_ending"].isoformat()],
            ["total_leads", report["kpi"]["total_leads"]],
            ["bookings", report["kpi"]["bookings"]],
            ["services", report["kpi"]["services"]],
            ["payments", report["kpi"]["payments"]],
            ["paid_revenue_dollars", report["kpi"]["paid_revenue_dollars"]],
            ["pending_revenue_dollars", report["kpi"]["pending_revenue_dollars"]],
            ["realized_revenue_dollars", report["kpi"]["realized_revenue_dollars"]],
            ["booking_conversion_pct", report["kpi"]["booking_conversion_pct"]],
            ["confirmed_bookings", report["kpi"]["confirmed_bookings"]],
            ["unread_contacts", report["kpi"]["unread_contacts"]],
            ["wow_leads_pct", report["comparison"]["leads_pct"]],
            ["wow_bookings_pct", report["comparison"]["bookings_pct"]],
            ["wow_revenue_pct", report["comparison"]["revenue_pct"]],
            ["wow_conversion_points", report["comparison"]["conversion_pct"]],
        ]
    )
    rows.append([])
    rows.append(["day", "contacts", "bookings", "services", "revenue"])
    for i in range(len(report["day_labels"])):
        rows.append(
            [
                report["day_labels"][i],
                report["contacts_daily"][i],
                report["bookings_daily"][i],
                report["services_daily"][i],
                report["revenue_daily"][i],
            ]
        )
    return _csv_response(
        f"bbb_weekly_report_{week_ending.isoformat()}.csv",
        rows,
    )


@admin_bp.route("/reports/weekly/export")
@login_required
def weekly_report_export():
    week_ending = _parse_optional_date(request.args.get("week_ending")) or date.today()
    include_unpaid = bool(request.args.get("include_unpaid"))
    service_type_filter = request.args.get("service_type", "all").strip().lower() or "all"
    report = _weekly_report_with_comparison(
        week_ending=week_ending,
        include_unpaid=include_unpaid,
        service_type_filter=service_type_filter,
    )
    html = render_template(
        "admin/weekly_report_export.html",
        report=report,
        generated_at=datetime.utcnow(),
    )
    filename = f"bbb_weekly_report_{week_ending.isoformat()}.html"
    return Response(
        html,
        mimetype="text/html",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_bp.route("/reports/studio", methods=["GET", "POST"])
@login_required
def report_studio():
    selected_template_id = request.args.get("template_id", type=int)
    selected_template = (
        db.session.get(AdminReportTemplate, selected_template_id)
        if selected_template_id
        else None
    )

    if request.method == "POST":
        action = (request.form.get("action") or "generate").strip().lower()
        inputs = _report_studio_inputs(request.form)

        if action == "save-template":
            name = (request.form.get("template_name") or "").strip()
            if not name:
                flash("Template name is required.", "error")
            else:
                template = AdminReportTemplate(
                    name=name,
                    dataset=inputs["dataset"],
                    fields_csv=",".join(inputs["selected_fields"]),
                    status_filter=inputs["status_filter"],
                    date_start=inputs["date_start"],
                    date_end=inputs["date_end"],
                    viz_type=inputs["viz_type"],
                    created_by_id=current_user.id,
                )
                db.session.add(template)
                db.session.commit()
                _record_admin_audit(
                    action="report_studio.template_saved",
                    entity_type="admin_report_template",
                    entity_id=template.id,
                    detail=f"dataset={template.dataset}",
                )
                db.session.commit()
                flash("Report template saved.", "success")
                return redirect(url_for("admin.report_studio", template_id=template.id))

        report = build_report(
            dataset=inputs["dataset"],
            fields=inputs["selected_fields"],
            status_filter=inputs["status_filter"],
            date_start=inputs["date_start"],
            date_end=inputs["date_end"],
            viz_type=inputs["viz_type"],
        )

        templates = AdminReportTemplate.query.order_by(AdminReportTemplate.updated_at.desc()).all()
        return render_template(
            "admin/report_studio.html",
            report=report,
            dataset_meta=DATASET_CONFIG[inputs["dataset"]],
            dataset=inputs["dataset"],
            selected_fields=inputs["selected_fields"],
            status_filter=inputs["status_filter"],
            date_start=inputs["date_start"].isoformat() if inputs["date_start"] else "",
            date_end=inputs["date_end"].isoformat() if inputs["date_end"] else "",
            viz_type=inputs["viz_type"],
            datasets=dataset_options(),
            templates=templates,
            selected_template_id=selected_template_id,
        )

    if selected_template:
        dataset = selected_template.dataset
        selected_fields = parse_fields(dataset, selected_template.field_list())
        status_filter = selected_template.status_filter
        date_start = selected_template.date_start
        date_end = selected_template.date_end
        viz_type = selected_template.viz_type
    else:
        dataset = "contacts"
        selected_fields = parse_fields(dataset, None)
        status_filter = "all"
        date_start = None
        date_end = None
        viz_type = "daily_volume"

    report = build_report(
        dataset=dataset,
        fields=selected_fields,
        status_filter=status_filter,
        date_start=date_start,
        date_end=date_end,
        viz_type=viz_type,
    )
    templates = AdminReportTemplate.query.order_by(AdminReportTemplate.updated_at.desc()).all()
    return render_template(
        "admin/report_studio.html",
        report=report,
        dataset_meta=DATASET_CONFIG[dataset],
        dataset=dataset,
        selected_fields=selected_fields,
        status_filter=status_filter,
        date_start=date_start.isoformat() if date_start else "",
        date_end=date_end.isoformat() if date_end else "",
        viz_type=viz_type,
        datasets=dataset_options(),
        templates=templates,
        selected_template_id=selected_template_id,
    )


@admin_bp.route("/reports/studio/export.csv")
@login_required
def report_studio_export_csv():
    inputs = _report_studio_inputs(request.args)
    report = build_report(
        dataset=inputs["dataset"],
        fields=inputs["selected_fields"],
        status_filter=inputs["status_filter"],
        date_start=inputs["date_start"],
        date_end=inputs["date_end"],
        viz_type=inputs["viz_type"],
    )

    rows = [report["selected_fields"]]
    for row in report["rows"]:
        rows.append([row.get(field, "") for field in report["selected_fields"]])

    return _csv_response(f"bbb_{inputs['dataset']}_report.csv", rows)


@admin_bp.route("/reports/studio/export")
@login_required
def report_studio_export_document():
    inputs = _report_studio_inputs(request.args)
    report = build_report(
        dataset=inputs["dataset"],
        fields=inputs["selected_fields"],
        status_filter=inputs["status_filter"],
        date_start=inputs["date_start"],
        date_end=inputs["date_end"],
        viz_type=inputs["viz_type"],
    )
    html = render_template(
        "admin/report_studio_export.html",
        report=report,
        generated_at=datetime.utcnow(),
        dataset_label=inputs["dataset"].replace("_", " ").title(),
    )
    return Response(
        html,
        mimetype="text/html",
        headers={"Content-Disposition": f"attachment; filename=bbb_{inputs['dataset']}_report.html"},
    )


# ---------------------------------------------------------------------------
# Admin Users (owner-only)
# ---------------------------------------------------------------------------

@admin_bp.route("/users")
@login_required
@owner_required
def users():
    all_users = AdminUser.query.order_by(AdminUser.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@login_required
@owner_required
def new_user():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "staff")
        password = request.form.get("password", "")

        if AdminUser.query.filter_by(email=email).first():
            flash("An admin with that email already exists.", "error")
        elif not password or len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        else:
            user = AdminUser(email=email, name=name, role=role)
            user.set_password(password)
            db.session.add(user)
            _record_admin_audit(
                action="admin_user.created",
                entity_type="admin_user",
                entity_id=email,
                detail=f"role={role}",
            )
            db.session.commit()
            flash(f"Admin user '{name}' created.", "success")
            return redirect(url_for("admin.users"))

    return render_template("admin/new_user.html")


@admin_bp.route("/users/<int:id>/toggle", methods=["POST"])
@login_required
@owner_required
def toggle_user(id):
    user = AdminUser.query.get_or_404(id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
    else:
        user.is_active = not user.is_active
        _record_admin_audit(
            action="admin_user.toggled",
            entity_type="admin_user",
            entity_id=user.id,
            detail=f"is_active={user.is_active}",
        )
        db.session.commit()
        state = "activated" if user.is_active else "deactivated"
        flash(f"User '{user.name}' {state}.", "success")
    return redirect(url_for("admin.users"))
