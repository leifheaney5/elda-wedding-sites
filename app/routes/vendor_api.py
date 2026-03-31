import csv
from datetime import datetime, timedelta
from io import StringIO
from flask import Blueprint, jsonify, request, Response
from flask_login import login_required, current_user

from app import db, csrf
from app.models.vendor import (
    Vendor,
    VendorMembership,
    VendorPayoutAccount,
    VendorPackage,
    VendorPackageAddon,
    VendorAvailabilityRule,
    VendorCalendarConnection,
    VendorAvailabilitySlot,
    VendorLead,
    VendorQuote,
    VendorQuoteLineItem,
    VendorBooking,
    VendorPaymentPlan,
    VendorTransaction,
    validate_booking_against_availability,
    has_booking_date_conflict,
)
from app.services.vendor_payments import (
    create_connect_onboarding_link,
    create_vendor_milestone_payment_intent,
    process_connect_webhook,
)

vendor_api_bp = Blueprint("vendor_api", __name__)


def _admin_only():
    return current_user.is_authenticated and getattr(current_user, "user_type", None) == "admin"


def _is_vendor_member(vendor_id: int) -> bool:
    if getattr(current_user, "is_owner", False):
        return True
    membership = VendorMembership.query.filter_by(
        vendor_id=vendor_id, admin_user_id=current_user.id
    ).first()
    return membership is not None


def _parse_iso_date_or_none(raw_value: str | None):
    raw = (raw_value or "").strip()
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _vendor_ops_tasks(vendor_id: int):
    now = datetime.utcnow()
    tasks = []

    stale_inquiries = VendorLead.query.filter(
        VendorLead.vendor_id == vendor_id,
        VendorLead.stage == VendorLead.STAGE_INQUIRY,
        VendorLead.created_at <= now - timedelta(days=5),
    ).count()
    if stale_inquiries:
        tasks.append(
            {
                "priority": "high",
                "title": "Follow up stale inquiries",
                "detail": f"{stale_inquiries} inquiry lead(s) are older than 5 days.",
                "action": "review_leads",
            }
        )

    expiring_quotes = VendorQuote.query.filter(
        VendorQuote.vendor_id == vendor_id,
        VendorQuote.status == VendorQuote.STATUS_SENT,
        VendorQuote.expires_at.isnot(None),
        VendorQuote.expires_at <= now + timedelta(days=3),
    ).count()
    if expiring_quotes:
        tasks.append(
            {
                "priority": "medium",
                "title": "Rescue expiring quotes",
                "detail": f"{expiring_quotes} quote(s) expire in 3 days or less.",
                "action": "follow_up_quotes",
            }
        )

    payout = VendorPayoutAccount.query.filter_by(vendor_id=vendor_id).first()
    if not payout or not payout.payouts_enabled:
        tasks.append(
            {
                "priority": "high",
                "title": "Complete payout onboarding",
                "detail": "Vendor payouts are not yet enabled in Stripe Connect.",
                "action": "complete_connect_onboarding",
            }
        )

    return tasks


@vendor_api_bp.route("/vendors", methods=["POST"])
@login_required
def create_vendor():
    if not _admin_only():
        return jsonify({"error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    business_name = (payload.get("business_name") or "").strip()
    slug = (payload.get("slug") or "").strip().lower()
    timezone = (payload.get("timezone") or "America/New_York").strip()

    if not business_name or not slug:
        return jsonify({"error": "business_name and slug are required"}), 400

    if Vendor.query.filter_by(slug=slug).first():
        return jsonify({"error": "slug already exists"}), 409

    vendor = Vendor(
        owner_user_id=current_user.id,
        business_name=business_name,
        slug=slug,
        status=Vendor.STATUS_ACTIVE,
        timezone=timezone,
    )
    db.session.add(vendor)
    db.session.flush()

    db.session.add(
        VendorMembership(
            vendor_id=vendor.id,
            admin_user_id=current_user.id,
            role=VendorMembership.ROLE_VENDOR_ADMIN,
            permissions_json={"manage_bookings": True, "manage_payments": True},
        )
    )
    db.session.add(VendorAvailabilityRule(vendor_id=vendor.id, min_lead_days=7, max_advance_days=365))
    db.session.commit()

    return jsonify({"id": vendor.id, "business_name": vendor.business_name, "slug": vendor.slug}), 201


@vendor_api_bp.route("/vendors/<int:vendor_id>/packages", methods=["POST"])
@login_required
def create_vendor_package(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    base_price_cents = int(payload.get("base_price_cents") or 0)
    if not name or base_price_cents < 0:
        return jsonify({"error": "invalid package payload"}), 400

    item = VendorPackage(
        vendor_id=vendor_id,
        name=name,
        description=(payload.get("description") or "").strip() or None,
        base_price_cents=base_price_cents,
        currency=(payload.get("currency") or "usd").strip().lower(),
        is_active=True,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"id": item.id, "name": item.name, "base_price_cents": item.base_price_cents}), 201


@vendor_api_bp.route("/vendors/<int:vendor_id>/packages/<int:package_id>/addons", methods=["POST"])
@login_required
def create_package_addon(vendor_id: int, package_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    package = VendorPackage.query.filter_by(id=package_id, vendor_id=vendor_id).first()
    if not package:
        return jsonify({"error": "package not found"}), 404

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    price_cents = int(payload.get("price_cents") or 0)
    if not name or price_cents < 0:
        return jsonify({"error": "invalid addon payload"}), 400

    addon = VendorPackageAddon(
        package_id=package.id,
        name=name,
        description=(payload.get("description") or "").strip() or None,
        price_cents=price_cents,
        is_optional=bool(payload.get("is_optional", True)),
        is_active=True,
    )
    db.session.add(addon)
    db.session.commit()
    return jsonify({"id": addon.id, "name": addon.name, "price_cents": addon.price_cents}), 201


@vendor_api_bp.route("/vendors/<int:vendor_id>/leads", methods=["POST"])
@login_required
def create_vendor_lead(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    inquiry_name = (payload.get("inquiry_name") or "").strip()
    inquiry_email = (payload.get("inquiry_email") or "").strip().lower()
    if not inquiry_name or not inquiry_email:
        return jsonify({"error": "inquiry_name and inquiry_email are required"}), 400

    lead = VendorLead(
        vendor_id=vendor_id,
        inquiry_name=inquiry_name,
        inquiry_email=inquiry_email,
        inquiry_phone=(payload.get("inquiry_phone") or "").strip() or None,
        source=(payload.get("source") or "admin").strip() or None,
        stage=VendorLead.STAGE_INQUIRY,
    )
    db.session.add(lead)
    db.session.commit()
    return jsonify({"id": lead.id, "stage": lead.stage}), 201


@vendor_api_bp.route("/vendors/<int:vendor_id>/quotes", methods=["POST"])
@login_required
def create_vendor_quote(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    lead_id = int(payload.get("lead_id") or 0)
    package_id = payload.get("package_id")
    expires_days = int(payload.get("expires_in_days") or 14)
    tax_cents = int(payload.get("tax_cents") or 0)

    lead = VendorLead.query.filter_by(id=lead_id, vendor_id=vendor_id).first()
    if not lead:
        return jsonify({"error": "lead not found"}), 404

    package = None
    subtotal_cents = 0
    if package_id:
        package = VendorPackage.query.filter_by(id=int(package_id), vendor_id=vendor_id).first()
        if not package:
            return jsonify({"error": "package not found"}), 404
        subtotal_cents += package.base_price_cents

    line_items_payload = payload.get("line_items") or []
    normalized_items = []
    for raw in line_items_payload:
        qty = int(raw.get("qty") or 1)
        unit_price = int(raw.get("unit_price_cents") or 0)
        total = qty * unit_price
        subtotal_cents += total
        normalized_items.append(
            {
                "item_type": (raw.get("item_type") or VendorQuoteLineItem.TYPE_CUSTOM).strip().lower(),
                "ref_id": raw.get("ref_id"),
                "name": (raw.get("name") or "Custom Item").strip(),
                "qty": qty,
                "unit_price_cents": unit_price,
                "total_price_cents": total,
            }
        )

    total_cents = subtotal_cents + max(tax_cents, 0)
    quote = VendorQuote(
        vendor_id=vendor_id,
        lead_id=lead.id,
        package_id=package.id if package else None,
        subtotal_cents=subtotal_cents,
        tax_cents=max(tax_cents, 0),
        total_cents=total_cents,
        currency=(payload.get("currency") or "usd").strip().lower(),
        status=VendorQuote.STATUS_SENT,
        expires_at=datetime.utcnow() + timedelta(days=max(1, expires_days)),
    )
    db.session.add(quote)
    db.session.flush()

    if package:
        db.session.add(
            VendorQuoteLineItem(
                quote_id=quote.id,
                item_type=VendorQuoteLineItem.TYPE_PACKAGE,
                ref_id=package.id,
                name=package.name,
                qty=1,
                unit_price_cents=package.base_price_cents,
                total_price_cents=package.base_price_cents,
            )
        )

    for item in normalized_items:
        db.session.add(
            VendorQuoteLineItem(
                quote_id=quote.id,
                item_type=item["item_type"],
                ref_id=item["ref_id"],
                name=item["name"],
                qty=item["qty"],
                unit_price_cents=item["unit_price_cents"],
                total_price_cents=item["total_price_cents"],
            )
        )

    lead.stage = VendorLead.STAGE_QUOTE_SENT
    db.session.commit()

    return jsonify({"id": quote.id, "total_cents": quote.total_cents, "status": quote.status}), 201


@vendor_api_bp.route("/vendors/<int:vendor_id>/bookings", methods=["POST"])
@login_required
def create_vendor_booking(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    lead_id = int(payload.get("lead_id") or 0)
    quote_id = int(payload.get("quote_id") or 0)
    event_date_raw = (payload.get("event_date") or "").strip()

    lead = VendorLead.query.filter_by(id=lead_id, vendor_id=vendor_id).first()
    quote = VendorQuote.query.filter_by(id=quote_id, vendor_id=vendor_id).first()
    if not lead or not quote:
        return jsonify({"error": "lead or quote not found"}), 404

    event_date = None
    if event_date_raw:
        try:
            event_date = datetime.strptime(event_date_raw, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "event_date must be YYYY-MM-DD"}), 400

    rule = VendorAvailabilityRule.query.filter_by(vendor_id=vendor_id).first()
    availability_error = validate_booking_against_availability(rule, event_date)
    if availability_error:
        return jsonify({"error": availability_error}), 400

    if rule and event_date and isinstance(rule.blackout_dates_json, list):
        if event_date.isoformat() in set(rule.blackout_dates_json):
            return jsonify({"error": "Event date falls on blackout date"}), 400

    if has_booking_date_conflict(vendor_id, event_date):
        return jsonify({"error": "Event date is not available"}), 409

    booking = VendorBooking(
        vendor_id=vendor_id,
        lead_id=lead.id,
        quote_id=quote.id,
        event_date=event_date,
        guest_count=payload.get("guest_count"),
        status=VendorBooking.STATUS_CONFIRMED,
        notes=(payload.get("notes") or "").strip() or None,
    )
    db.session.add(booking)

    lead.stage = VendorLead.STAGE_BOOKED
    quote.status = VendorQuote.STATUS_ACCEPTED

    db.session.commit()
    return jsonify({"id": booking.id, "status": booking.status}), 201


@vendor_api_bp.route("/vendors/<int:vendor_id>/bookings/<int:booking_id>/payment-plan", methods=["POST"])
@login_required
def set_payment_plan(vendor_id: int, booking_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    booking = VendorBooking.query.filter_by(id=booking_id, vendor_id=vendor_id).first()
    if not booking:
        return jsonify({"error": "booking not found"}), 404

    payload = request.get_json(silent=True) or {}
    deposit_cents = int(payload.get("deposit_amount_cents") or 0)
    final_cents = int(payload.get("final_amount_cents") or 0)

    plan = VendorPaymentPlan.query.filter_by(booking_id=booking.id).first()
    if not plan:
        plan = VendorPaymentPlan(booking_id=booking.id)
        db.session.add(plan)

    plan.deposit_amount_cents = max(0, deposit_cents)
    plan.final_amount_cents = max(0, final_cents)
    plan.auto_schedule_enabled = bool(payload.get("auto_schedule_enabled", True))

    deposit_due_at_raw = payload.get("deposit_due_at")
    final_due_at_raw = payload.get("final_due_at")
    if deposit_due_at_raw:
        try:
            plan.deposit_due_at = datetime.fromisoformat(deposit_due_at_raw)
        except ValueError:
            return jsonify({"error": "deposit_due_at must be ISO datetime"}), 400
    if final_due_at_raw:
        try:
            plan.final_due_at = datetime.fromisoformat(final_due_at_raw)
        except ValueError:
            return jsonify({"error": "final_due_at must be ISO datetime"}), 400

    db.session.commit()
    return jsonify(
        {
            "booking_id": booking.id,
            "deposit_amount_cents": plan.deposit_amount_cents,
            "final_amount_cents": plan.final_amount_cents,
            "auto_schedule_enabled": plan.auto_schedule_enabled,
        }
    )


@vendor_api_bp.route("/vendors/<int:vendor_id>/availability/rules", methods=["GET", "PUT"])
@login_required
def vendor_availability_rules(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    rule = VendorAvailabilityRule.query.filter_by(vendor_id=vendor_id).first()
    if not rule:
        rule = VendorAvailabilityRule(vendor_id=vendor_id)
        db.session.add(rule)
        db.session.commit()

    if request.method == "PUT":
        payload = request.get_json(silent=True) or {}
        min_lead_days = int(payload.get("min_lead_days") or rule.min_lead_days)
        max_advance_days = int(payload.get("max_advance_days") or rule.max_advance_days)
        if min_lead_days < 0 or max_advance_days < 1:
            return jsonify({"error": "invalid availability rule values"}), 400

        rule.min_lead_days = min_lead_days
        rule.max_advance_days = max_advance_days
        rule.blackout_dates_json = payload.get("blackout_dates_json")
        rule.weekly_hours_json = payload.get("weekly_hours_json")
        db.session.commit()

    return jsonify(
        {
            "vendor_id": vendor_id,
            "min_lead_days": rule.min_lead_days,
            "max_advance_days": rule.max_advance_days,
            "blackout_dates_json": rule.blackout_dates_json,
            "weekly_hours_json": rule.weekly_hours_json,
        }
    )


@vendor_api_bp.route("/vendors/<int:vendor_id>/calendar/connections", methods=["GET", "POST"])
@login_required
def vendor_calendar_connections(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        provider = (payload.get("provider") or "").strip().lower()
        external_calendar_id = (payload.get("external_calendar_id") or "").strip()
        sync_direction = (
            payload.get("sync_direction")
            or VendorCalendarConnection.DIRECTION_BIDIRECTIONAL
        )
        sync_direction = sync_direction.strip().lower()

        valid_providers = {
            VendorCalendarConnection.PROVIDER_GOOGLE,
            VendorCalendarConnection.PROVIDER_ICAL,
        }
        valid_directions = {
            VendorCalendarConnection.DIRECTION_INBOUND,
            VendorCalendarConnection.DIRECTION_OUTBOUND,
            VendorCalendarConnection.DIRECTION_BIDIRECTIONAL,
        }

        if provider not in valid_providers or not external_calendar_id:
            return jsonify({"error": "invalid provider or external_calendar_id"}), 400
        if sync_direction not in valid_directions:
            return jsonify({"error": "invalid sync_direction"}), 400

        record = VendorCalendarConnection(
            vendor_id=vendor_id,
            provider=provider,
            external_calendar_id=external_calendar_id,
            sync_direction=sync_direction,
            access_token_enc=payload.get("access_token_enc"),
            refresh_token_enc=payload.get("refresh_token_enc"),
            is_active=bool(payload.get("is_active", True)),
        )
        db.session.add(record)
        db.session.commit()

    records = (
        VendorCalendarConnection.query.filter_by(vendor_id=vendor_id)
        .order_by(VendorCalendarConnection.created_at.desc())
        .all()
    )
    return jsonify(
        [
            {
                "id": item.id,
                "provider": item.provider,
                "external_calendar_id": item.external_calendar_id,
                "sync_direction": item.sync_direction,
                "is_active": item.is_active,
                "last_synced_at": item.last_synced_at.isoformat()
                if item.last_synced_at
                else None,
            }
            for item in records
        ]
    )


@vendor_api_bp.route("/vendors/<int:vendor_id>/calendar/sync", methods=["POST"])
@login_required
def vendor_calendar_sync(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    now = datetime.utcnow()
    connections = VendorCalendarConnection.query.filter_by(
        vendor_id=vendor_id, is_active=True
    ).all()
    for conn in connections:
        conn.last_synced_at = now
    db.session.commit()

    return jsonify(
        {
            "queued": True,
            "connection_count": len(connections),
            "synced_at": now.isoformat(),
        }
    )


@vendor_api_bp.route("/vendors/<int:vendor_id>/availability/slots", methods=["GET"])
@login_required
def vendor_availability_slots(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    from_raw = (request.args.get("from") or "").strip()
    to_raw = (request.args.get("to") or "").strip()
    try:
        from_day = (
            datetime.strptime(from_raw, "%Y-%m-%d").date()
            if from_raw
            else datetime.utcnow().date()
        )
        to_day = (
            datetime.strptime(to_raw, "%Y-%m-%d").date()
            if to_raw
            else (from_day + timedelta(days=30))
        )
    except ValueError:
        return jsonify({"error": "from/to must be YYYY-MM-DD"}), 400

    if to_day < from_day:
        return jsonify({"error": "to must be >= from"}), 400

    rule = VendorAvailabilityRule.query.filter_by(vendor_id=vendor_id).first()
    blackout = set((rule.blackout_dates_json or [])) if rule else set()

    blocked_slots = VendorAvailabilitySlot.query.filter(
        VendorAvailabilitySlot.vendor_id == vendor_id,
        VendorAvailabilitySlot.is_blocked == True,
        VendorAvailabilitySlot.starts_at
        >= datetime.combine(from_day, datetime.min.time()),
        VendorAvailabilitySlot.starts_at
        <= datetime.combine(to_day, datetime.max.time()),
    ).all()
    blocked_days = {slot.starts_at.date() for slot in blocked_slots if slot.starts_at}

    results = []
    cursor = from_day
    while cursor <= to_day:
        reason = None
        available = True

        if rule:
            error = validate_booking_against_availability(rule, cursor)
            if error:
                available = False
                reason = error

        if available and cursor.isoformat() in blackout:
            available = False
            reason = "Blackout date"

        if available and cursor in blocked_days:
            available = False
            reason = "Blocked slot"

        if available and has_booking_date_conflict(vendor_id, cursor):
            available = False
            reason = "Existing booking conflict"

        results.append(
            {
                "date": cursor.isoformat(),
                "available": available,
                "reason": reason,
            }
        )
        cursor += timedelta(days=1)

    return jsonify(results)


@vendor_api_bp.route("/vendors/<int:vendor_id>/stripe/connect-status", methods=["GET"])
@login_required
def vendor_connect_status(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    payout = VendorPayoutAccount.query.filter_by(vendor_id=vendor_id).first()
    if not payout:
        return jsonify({"connected": False, "onboarding_status": "not_started"})

    return jsonify(
        {
            "connected": True,
            "stripe_account_id": payout.stripe_account_id,
            "account_type": payout.account_type,
            "charges_enabled": payout.charges_enabled,
            "payouts_enabled": payout.payouts_enabled,
            "onboarding_status": payout.onboarding_status,
        }
    )


@vendor_api_bp.route("/vendors/<int:vendor_id>/ops/scorecard", methods=["GET"])
@login_required
def vendor_ops_scorecard(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    leads_total = VendorLead.query.filter_by(vendor_id=vendor_id).count()
    leads_inquiry = VendorLead.query.filter_by(
        vendor_id=vendor_id,
        stage=VendorLead.STAGE_INQUIRY,
    ).count()
    quotes_sent = VendorQuote.query.filter_by(
        vendor_id=vendor_id,
        status=VendorQuote.STATUS_SENT,
    ).count()
    bookings_confirmed = VendorBooking.query.filter_by(
        vendor_id=vendor_id,
        status=VendorBooking.STATUS_CONFIRMED,
    ).count()

    succeeded_transactions = VendorTransaction.query.filter_by(
        vendor_id=vendor_id,
        status=VendorTransaction.STATUS_SUCCEEDED,
    ).all()
    pending_transactions = VendorTransaction.query.filter(
        VendorTransaction.vendor_id == vendor_id,
        VendorTransaction.status.in_(
            [
                VendorTransaction.STATUS_REQUIRES_PAYMENT_METHOD,
                VendorTransaction.STATUS_REQUIRES_CONFIRMATION,
                VendorTransaction.STATUS_PROCESSING,
            ]
        ),
    ).count()

    gross_cents = sum(item.gross_cents for item in succeeded_transactions)
    fee_cents = sum(item.platform_fee_cents for item in succeeded_transactions)
    net_cents = sum(item.vendor_net_cents for item in succeeded_transactions)

    tasks = _vendor_ops_tasks(vendor_id)
    health_score = 100
    health_score -= min(leads_inquiry * 3, 30)
    health_score -= min(pending_transactions * 2, 20)
    health_score -= 25 if any(item["priority"] == "high" for item in tasks) else 0
    health_score = max(0, health_score)

    return jsonify(
        {
            "vendor_id": vendor_id,
            "pipeline": {
                "leads_total": leads_total,
                "leads_inquiry": leads_inquiry,
                "quotes_sent": quotes_sent,
                "bookings_confirmed": bookings_confirmed,
                "lead_to_booking_pct": round((bookings_confirmed / leads_total) * 100, 1)
                if leads_total
                else 0,
            },
            "finance": {
                "gross_cents": gross_cents,
                "platform_fee_cents": fee_cents,
                "vendor_net_cents": net_cents,
                "pending_transaction_count": pending_transactions,
            },
            "ops": {
                "health_score": health_score,
                "high_priority_task_count": sum(1 for item in tasks if item["priority"] == "high"),
            },
        }
    )


@vendor_api_bp.route("/vendors/<int:vendor_id>/ops/tasks", methods=["GET"])
@login_required
def vendor_ops_tasks(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    tasks = _vendor_ops_tasks(vendor_id)
    return jsonify({"vendor_id": vendor_id, "count": len(tasks), "tasks": tasks})


@vendor_api_bp.route("/vendors/<int:vendor_id>/ops/expire-overdue-quotes", methods=["POST"])
@login_required
def vendor_ops_expire_overdue_quotes(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    now = datetime.utcnow()
    stale_quotes = VendorQuote.query.filter(
        VendorQuote.vendor_id == vendor_id,
        VendorQuote.status == VendorQuote.STATUS_SENT,
        VendorQuote.expires_at.isnot(None),
        VendorQuote.expires_at < now,
    ).all()

    for quote in stale_quotes:
        quote.status = VendorQuote.STATUS_EXPIRED

    db.session.commit()
    return jsonify(
        {
            "vendor_id": vendor_id,
            "updated": len(stale_quotes),
            "status": VendorQuote.STATUS_EXPIRED,
        }
    )


@vendor_api_bp.route("/vendors/<int:vendor_id>/finance/summary", methods=["GET"])
@login_required
def vendor_finance_summary(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    succeeded_transactions = VendorTransaction.query.filter_by(
        vendor_id=vendor_id,
        status=VendorTransaction.STATUS_SUCCEEDED,
    ).all()
    all_transactions = VendorTransaction.query.filter_by(vendor_id=vendor_id).all()

    status_counts = {
        VendorTransaction.STATUS_REQUIRES_PAYMENT_METHOD: 0,
        VendorTransaction.STATUS_REQUIRES_CONFIRMATION: 0,
        VendorTransaction.STATUS_PROCESSING: 0,
        VendorTransaction.STATUS_SUCCEEDED: 0,
        VendorTransaction.STATUS_FAILED: 0,
        VendorTransaction.STATUS_CANCELED: 0,
    }
    milestone_counts = {
        VendorTransaction.MILESTONE_DEPOSIT: 0,
        VendorTransaction.MILESTONE_FINAL: 0,
        VendorTransaction.MILESTONE_OTHER: 0,
    }

    for item in all_transactions:
        if item.status in status_counts:
            status_counts[item.status] += 1
        if item.milestone in milestone_counts:
            milestone_counts[item.milestone] += 1

    gross_collected_cents = sum(item.gross_cents for item in succeeded_transactions)
    platform_fees_cents = sum(item.platform_fee_cents for item in succeeded_transactions)
    vendor_net_cents = sum(item.vendor_net_cents for item in succeeded_transactions)

    plan_rows = (
        db.session.query(VendorPaymentPlan, VendorBooking)
        .join(VendorBooking, VendorBooking.id == VendorPaymentPlan.booking_id)
        .filter(VendorBooking.vendor_id == vendor_id)
        .all()
    )
    paid_tx_by_booking = {
        (item.booking_id, item.milestone)
        for item in all_transactions
        if item.status == VendorTransaction.STATUS_SUCCEEDED
    }

    outstanding_deposit_cents = 0
    outstanding_final_cents = 0
    now = datetime.utcnow()
    due_next_30_days = []

    for plan, booking in plan_rows:
        if plan.deposit_amount_cents and (booking.id, VendorTransaction.MILESTONE_DEPOSIT) not in paid_tx_by_booking:
            outstanding_deposit_cents += plan.deposit_amount_cents
            if plan.deposit_due_at and now <= plan.deposit_due_at <= (now + timedelta(days=30)):
                due_next_30_days.append(
                    {
                        "booking_id": booking.id,
                        "milestone": VendorTransaction.MILESTONE_DEPOSIT,
                        "due_at": plan.deposit_due_at.isoformat(),
                        "amount_cents": plan.deposit_amount_cents,
                    }
                )
        if plan.final_amount_cents and (booking.id, VendorTransaction.MILESTONE_FINAL) not in paid_tx_by_booking:
            outstanding_final_cents += plan.final_amount_cents
            if plan.final_due_at and now <= plan.final_due_at <= (now + timedelta(days=30)):
                due_next_30_days.append(
                    {
                        "booking_id": booking.id,
                        "milestone": VendorTransaction.MILESTONE_FINAL,
                        "due_at": plan.final_due_at.isoformat(),
                        "amount_cents": plan.final_amount_cents,
                    }
                )

    due_next_30_days.sort(key=lambda row: row["due_at"])

    return jsonify(
        {
            "vendor_id": vendor_id,
            "transaction_count": len(all_transactions),
            "status_counts": status_counts,
            "milestone_counts": milestone_counts,
            "gross_collected_cents": gross_collected_cents,
            "platform_fees_cents": platform_fees_cents,
            "vendor_net_cents": vendor_net_cents,
            "outstanding_deposit_cents": outstanding_deposit_cents,
            "outstanding_final_cents": outstanding_final_cents,
            "outstanding_total_cents": outstanding_deposit_cents + outstanding_final_cents,
            "due_next_30_days": due_next_30_days,
        }
    )


@vendor_api_bp.route("/vendors/<int:vendor_id>/finance/reconciliation", methods=["GET"])
@login_required
def vendor_finance_reconciliation(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    status_filter = (request.args.get("status") or "").strip().lower()
    milestone_filter = (request.args.get("milestone") or "").strip().lower()
    limit = min(max(int(request.args.get("limit") or 200), 1), 1000)

    try:
        from_day = _parse_iso_date_or_none(request.args.get("from"))
        to_day = _parse_iso_date_or_none(request.args.get("to"))
    except ValueError:
        return jsonify({"error": "from/to must be YYYY-MM-DD"}), 400

    query = VendorTransaction.query.filter_by(vendor_id=vendor_id)
    if status_filter:
        query = query.filter(VendorTransaction.status == status_filter)
    if milestone_filter:
        query = query.filter(VendorTransaction.milestone == milestone_filter)
    if from_day:
        query = query.filter(VendorTransaction.created_at >= datetime.combine(from_day, datetime.min.time()))
    if to_day:
        query = query.filter(VendorTransaction.created_at <= datetime.combine(to_day, datetime.max.time()))

    records = query.order_by(VendorTransaction.created_at.desc()).limit(limit).all()
    booking_ids = [item.booking_id for item in records]
    bookings = VendorBooking.query.filter(VendorBooking.id.in_(booking_ids)).all() if booking_ids else []
    leads = (
        VendorLead.query.filter(VendorLead.id.in_([item.lead_id for item in bookings if item.lead_id]))
        .all()
        if bookings
        else []
    )

    booking_map = {item.id: item for item in bookings}
    lead_map = {item.id: item for item in leads}

    rows = []
    for item in records:
        booking = booking_map.get(item.booking_id)
        lead = lead_map.get(booking.lead_id) if booking else None
        rows.append(
            {
                "id": item.id,
                "booking_id": item.booking_id,
                "customer_name": lead.inquiry_name if lead else None,
                "event_date": booking.event_date.isoformat() if booking and booking.event_date else None,
                "milestone": item.milestone,
                "status": item.status,
                "currency": item.currency,
                "gross_cents": item.gross_cents,
                "platform_fee_cents": item.platform_fee_cents,
                "vendor_net_cents": item.vendor_net_cents,
                "stripe_payment_intent_id": item.stripe_payment_intent_id,
                "paid_at": item.paid_at.isoformat() if item.paid_at else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
        )

    return jsonify(
        {
            "vendor_id": vendor_id,
            "filters": {
                "status": status_filter or None,
                "milestone": milestone_filter or None,
                "from": from_day.isoformat() if from_day else None,
                "to": to_day.isoformat() if to_day else None,
                "limit": limit,
            },
            "count": len(rows),
            "totals": {
                "gross_cents": sum(item["gross_cents"] for item in rows),
                "platform_fee_cents": sum(item["platform_fee_cents"] for item in rows),
                "vendor_net_cents": sum(item["vendor_net_cents"] for item in rows),
            },
            "transactions": rows,
        }
    )


@vendor_api_bp.route("/vendors/<int:vendor_id>/finance/reconciliation.csv", methods=["GET"])
@login_required
def vendor_finance_reconciliation_csv(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    status_filter = (request.args.get("status") or "").strip().lower()
    milestone_filter = (request.args.get("milestone") or "").strip().lower()

    query = VendorTransaction.query.filter_by(vendor_id=vendor_id)
    if status_filter:
        query = query.filter(VendorTransaction.status == status_filter)
    if milestone_filter:
        query = query.filter(VendorTransaction.milestone == milestone_filter)

    records = query.order_by(VendorTransaction.created_at.desc()).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "transaction_id",
            "booking_id",
            "milestone",
            "status",
            "currency",
            "gross_cents",
            "platform_fee_cents",
            "vendor_net_cents",
            "stripe_payment_intent_id",
            "paid_at",
            "created_at",
        ]
    )

    for item in records:
        writer.writerow(
            [
                item.id,
                item.booking_id,
                item.milestone,
                item.status,
                item.currency,
                item.gross_cents,
                item.platform_fee_cents,
                item.vendor_net_cents,
                item.stripe_payment_intent_id,
                item.paid_at.isoformat() if item.paid_at else "",
                item.created_at.isoformat() if item.created_at else "",
            ]
        )

    csv_body = output.getvalue()
    output.close()

    return Response(
        csv_body,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=vendor_{vendor_id}_reconciliation.csv"
        },
    )


@vendor_api_bp.route("/vendors/<int:vendor_id>/stripe/connect-onboarding-link", methods=["POST"])
@login_required
def vendor_connect_onboarding_link(vendor_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    vendor = Vendor.query.get(vendor_id)
    if not vendor:
        return jsonify({"error": "vendor not found"}), 404

    try:
        result = create_connect_onboarding_link(vendor)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        return jsonify({"error": f"failed to create onboarding link: {exc}"}), 400

    return jsonify(result), 201


@vendor_api_bp.route("/vendors/<int:vendor_id>/bookings/<int:booking_id>/payments/intent", methods=["POST"])
@login_required
def create_vendor_booking_payment_intent(vendor_id: int, booking_id: int):
    if not _admin_only() or not _is_vendor_member(vendor_id):
        return jsonify({"error": "forbidden"}), 403

    vendor = Vendor.query.get(vendor_id)
    booking = VendorBooking.query.filter_by(id=booking_id, vendor_id=vendor_id).first()
    if not vendor or not booking:
        return jsonify({"error": "vendor or booking not found"}), 404

    payload = request.get_json(silent=True) or {}
    milestone = (payload.get("milestone") or "").strip().lower()
    currency = (payload.get("currency") or "usd").strip().lower()

    try:
        result = create_vendor_milestone_payment_intent(
            vendor=vendor,
            booking=booking,
            milestone=milestone,
            currency=currency,
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"failed to create payment intent: {exc}"}), 400

    lead = VendorLead.query.filter_by(id=booking.lead_id, vendor_id=vendor_id).first()
    if lead and milestone == VendorTransaction.MILESTONE_DEPOSIT:
        lead.stage = VendorLead.STAGE_DEPOSIT_PAID
        db.session.commit()

    return jsonify(result), 201


@vendor_api_bp.route("/webhooks/stripe/connect", methods=["POST"])
@csrf.exempt
def stripe_connect_webhook():
    payload = request.get_data()
    signature = request.headers.get("Stripe-Signature")
    try:
        result = process_connect_webhook(payload=payload, signature=signature)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception:
        return jsonify({"error": "invalid webhook"}), 400
    return jsonify(result), 200
