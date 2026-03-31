from datetime import datetime, date, timedelta
from app import db


class Vendor(db.Model):
    __tablename__ = "vendors"

    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"

    id = db.Column(db.Integer, primary_key=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), nullable=True)
    business_name = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_DRAFT)
    timezone = db.Column(db.String(80), nullable=False, default="America/New_York")
    phone = db.Column(db.String(30), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VendorMembership(db.Model):
    __tablename__ = "vendor_memberships"

    ROLE_VENDOR_ADMIN = "vendor_admin"
    ROLE_VENDOR_STAFF = "vendor_staff"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False, index=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), nullable=False, index=True)
    role = db.Column(db.String(30), nullable=False, default=ROLE_VENDOR_STAFF)
    permissions_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("vendor_id", "admin_user_id", name="uq_vendor_membership"),)


class VendorPayoutAccount(db.Model):
    __tablename__ = "vendor_payout_accounts"

    ACCOUNT_STANDARD = "standard"
    ACCOUNT_EXPRESS = "express"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False, index=True)
    stripe_account_id = db.Column(db.String(120), nullable=False, unique=True, index=True)
    account_type = db.Column(db.String(20), nullable=False, default=ACCOUNT_EXPRESS)
    charges_enabled = db.Column(db.Boolean, nullable=False, default=False)
    payouts_enabled = db.Column(db.Boolean, nullable=False, default=False)
    onboarding_status = db.Column(db.String(30), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VendorPackage(db.Model):
    __tablename__ = "vendor_packages"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    base_price_cents = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="usd")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VendorPackageAddon(db.Model):
    __tablename__ = "vendor_package_addons"

    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey("vendor_packages.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price_cents = db.Column(db.Integer, nullable=False)
    is_optional = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class VendorAvailabilityRule(db.Model):
    __tablename__ = "vendor_availability_rules"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False, unique=True, index=True)
    min_lead_days = db.Column(db.Integer, nullable=False, default=7)
    max_advance_days = db.Column(db.Integer, nullable=False, default=365)
    blackout_dates_json = db.Column(db.JSON, nullable=True)
    weekly_hours_json = db.Column(db.JSON, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VendorCalendarConnection(db.Model):
    __tablename__ = "vendor_calendar_connections"

    PROVIDER_GOOGLE = "google"
    PROVIDER_ICAL = "ical"

    DIRECTION_INBOUND = "inbound"
    DIRECTION_OUTBOUND = "outbound"
    DIRECTION_BIDIRECTIONAL = "bidirectional"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False, index=True)
    provider = db.Column(db.String(20), nullable=False)
    external_calendar_id = db.Column(db.String(255), nullable=False)
    sync_direction = db.Column(db.String(20), nullable=False, default=DIRECTION_BIDIRECTIONAL)
    access_token_enc = db.Column(db.Text, nullable=True)
    refresh_token_enc = db.Column(db.Text, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VendorAvailabilitySlot(db.Model):
    __tablename__ = "vendor_availability_slots"

    SOURCE_MANUAL = "manual"
    SOURCE_BOOKING = "booking"
    SOURCE_CALENDAR_SYNC = "calendar_sync"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False, index=True)
    starts_at = db.Column(db.DateTime, nullable=False)
    ends_at = db.Column(db.DateTime, nullable=False)
    is_blocked = db.Column(db.Boolean, nullable=False, default=True)
    source = db.Column(db.String(30), nullable=False, default=SOURCE_MANUAL)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class VendorLead(db.Model):
    __tablename__ = "vendor_leads"

    STAGE_INQUIRY = "inquiry"
    STAGE_QUOTE_SENT = "quote_sent"
    STAGE_DEPOSIT_PAID = "deposit_paid"
    STAGE_BOOKED = "booked"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False, index=True)
    inquiry_name = db.Column(db.String(150), nullable=False)
    inquiry_email = db.Column(db.String(150), nullable=False)
    inquiry_phone = db.Column(db.String(30), nullable=True)
    source = db.Column(db.String(40), nullable=True)
    stage = db.Column(db.String(30), nullable=False, default=STAGE_INQUIRY)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VendorQuote(db.Model):
    __tablename__ = "vendor_quotes"

    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_ACCEPTED = "accepted"
    STATUS_EXPIRED = "expired"
    STATUS_DECLINED = "declined"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("vendor_leads.id"), nullable=False, index=True)
    package_id = db.Column(db.Integer, db.ForeignKey("vendor_packages.id"), nullable=True, index=True)
    subtotal_cents = db.Column(db.Integer, nullable=False, default=0)
    tax_cents = db.Column(db.Integer, nullable=False, default=0)
    total_cents = db.Column(db.Integer, nullable=False, default=0)
    currency = db.Column(db.String(10), nullable=False, default="usd")
    status = db.Column(db.String(20), nullable=False, default=STATUS_DRAFT)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VendorQuoteLineItem(db.Model):
    __tablename__ = "vendor_quote_line_items"

    TYPE_PACKAGE = "package"
    TYPE_ADDON = "addon"
    TYPE_CUSTOM = "custom"

    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("vendor_quotes.id"), nullable=False, index=True)
    item_type = db.Column(db.String(20), nullable=False, default=TYPE_CUSTOM)
    ref_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(160), nullable=False)
    qty = db.Column(db.Integer, nullable=False, default=1)
    unit_price_cents = db.Column(db.Integer, nullable=False, default=0)
    total_price_cents = db.Column(db.Integer, nullable=False, default=0)


class VendorBooking(db.Model):
    __tablename__ = "vendor_bookings"

    STATUS_TENTATIVE = "tentative"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("vendor_leads.id"), nullable=False, index=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("vendor_quotes.id"), nullable=True, index=True)
    event_date = db.Column(db.Date, nullable=True)
    event_start_at = db.Column(db.DateTime, nullable=True)
    event_end_at = db.Column(db.DateTime, nullable=True)
    guest_count = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_TENTATIVE)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VendorPaymentPlan(db.Model):
    __tablename__ = "vendor_payment_plans"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("vendor_bookings.id"), nullable=False, unique=True, index=True)
    deposit_due_at = db.Column(db.DateTime, nullable=True)
    deposit_amount_cents = db.Column(db.Integer, nullable=False, default=0)
    final_due_at = db.Column(db.DateTime, nullable=True)
    final_amount_cents = db.Column(db.Integer, nullable=False, default=0)
    auto_schedule_enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VendorTransaction(db.Model):
    __tablename__ = "vendor_transactions"

    STATUS_REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    STATUS_REQUIRES_CONFIRMATION = "requires_confirmation"
    STATUS_PROCESSING = "processing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CANCELED = "canceled"

    MILESTONE_DEPOSIT = "deposit"
    MILESTONE_FINAL = "final"
    MILESTONE_OTHER = "other"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False, index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("vendor_bookings.id"), nullable=False, index=True)
    milestone = db.Column(db.String(20), nullable=False, default=MILESTONE_OTHER)
    stripe_payment_intent_id = db.Column(db.String(200), nullable=False, unique=True, index=True)
    currency = db.Column(db.String(10), nullable=False, default="usd")
    gross_cents = db.Column(db.Integer, nullable=False, default=0)
    platform_fee_cents = db.Column(db.Integer, nullable=False, default=0)
    vendor_net_cents = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(40), nullable=False, default=STATUS_REQUIRES_PAYMENT_METHOD)
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def validate_booking_against_availability(rule: VendorAvailabilityRule | None, event_day: date | None) -> str | None:
    if not event_day or not rule:
        return None

    today = date.today()
    min_day = today + timedelta(days=rule.min_lead_days)
    max_day = today + timedelta(days=rule.max_advance_days)

    if min_day and event_day < min_day:
        return "Event date violates minimum lead time."
    if max_day and event_day > max_day:
        return "Event date exceeds max advance booking window."
    return None


def has_booking_date_conflict(vendor_id: int, event_day: date | None) -> bool:
    if not event_day:
        return False
    conflict = (
        VendorBooking.query.filter_by(vendor_id=vendor_id, event_date=event_day)
        .filter(VendorBooking.status.in_([VendorBooking.STATUS_TENTATIVE, VendorBooking.STATUS_CONFIRMED]))
        .first()
    )
    return conflict is not None
