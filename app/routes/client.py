from datetime import datetime, date, timedelta
from functools import wraps
from flask import (
    Blueprint,
    render_template,
    redirect,
    request,
    url_for,
    flash,
    current_app,
    send_file,
    abort,
)
from io import BytesIO
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask_login import login_user, logout_user, current_user
from flask_limiter.util import get_remote_address
from app import db, oauth, limiter
from app.models.client_user import ClientUser
from app.models.booking import BookingRequest
from app.models.contact import ContactSubmission, ContactAttachment
from app.models.service_request import ServiceRequest
from app.models.payment import Payment
from app.models.client_inspiration import ClientInspiration
from app.models.client_plan_task import ClientPlanTask
from app.models.client_rsvp_guest import ClientRsvpGuest
from app.services.attachments import (
    ALLOWED_ATTACHMENT_EXTENSIONS,
    build_contact_attachment,
)
from app.utils.background import run_in_background
from app.utils.email import send_client_password_reset_email

client_bp = Blueprint("client", __name__)

INSPO_COLOR_OPTIONS = [
    "Soft Blush + Sand",
    "Powder Blue + Ivory",
    "Champagne + White",
    "Sage + Cream",
    "Terracotta + Beige",
    "Monochrome White",
    "Dusty Blue + Silver",
    "Sunset Coral + Gold",
    "Pearl + Sage",
    "Black Tie Neutrals",
    "Lavender + Linen",
    "Mauve + Champagne",
    "Navy + Gold",
    "Slate Blue + Driftwood",
    "Rosewood + Cream",
    "Emerald + Ivory",
]
INSPO_THEME_OPTIONS = [
    "Elegant Modern",
    "Classic Romantic",
    "Boho Garden",
    "Tropical Modern",
    "Minimal Luxury",
    "Sunset Glam",
    "Garden Romantic",
    "Modern Editorial",
    "Timeless Black Tie",
    "Candlelit Intimate",
    "Whimsical Garden",
    "Minimal Modern",
    "Old Money Classic",
    "Soft Vintage",
]
INSPO_FLORAL_OPTIONS = [
    "White Roses + Eucalyptus",
    "Orchids + Palm Greens",
    "Wildflower Color Pop",
    "Neutral Dried Florals",
    "Hydrangea + Rose Mix",
    "Baby's Breath Minimal",
    "Peony + Garden Rose",
    "Lush Greenery Runner",
    "Tropical Anthurium Feature",
    "Classic White Orchid Arch",
    "Blue Hydrangea + Rose",
    "Cascading Green + White",
    "Romantic Blush Garden Mix",
    "Textural Pampas + Palm",
]
PLANNER_MESSAGE_TYPES = [
    ("question", "Question"),
    ("feedback", "Feedback"),
    ("request", "Request"),
    ("update", "Update"),
    ("urgent", "Urgent"),
]

RSVP_STATUS_OPTIONS = [
    (ClientRsvpGuest.STATUS_PENDING, "Pending"),
    (ClientRsvpGuest.STATUS_ATTENDING, "Attending"),
    (ClientRsvpGuest.STATUS_DECLINED, "Declined"),
    (ClientRsvpGuest.STATUS_MAYBE, "Maybe"),
]


def _normalize_rsvp_status(raw_status: str | None) -> str:
    allowed = {
        ClientRsvpGuest.STATUS_PENDING,
        ClientRsvpGuest.STATUS_ATTENDING,
        ClientRsvpGuest.STATUS_DECLINED,
        ClientRsvpGuest.STATUS_MAYBE,
    }
    normalized = (raw_status or "").strip().lower()
    return normalized if normalized in allowed else ClientRsvpGuest.STATUS_PENDING


def _client_login_rate_limit_key() -> str:
    email = (request.form.get("email") or "").strip().lower()
    remote = get_remote_address() or (request.remote_addr or "unknown")
    return f"{remote}:{email}" if email else remote


def _recommended_task_templates(wedding_date: date | None) -> list[dict]:
    def due(days_before: int) -> date | None:
        if not wedding_date:
            return None
        return wedding_date - timedelta(days=days_before)

    return [
        {"title": "Finalize ceremony package selection", "category": "Planning", "due_date": due(180)},
        {"title": "Submit venue permit details", "category": "Permits", "due_date": due(120)},
        {"title": "Confirm guest count", "category": "Guest List", "due_date": due(60)},
        {"title": "Choose catering menu and dietary needs", "category": "Catering", "due_date": due(45)},
        {"title": "Approve florals and decor design board", "category": "Florals", "due_date": due(40)},
        {"title": "Apply for marriage license", "category": "Legal", "due_date": due(45)},
        {"title": "Finalize ceremony timeline", "category": "Timeline", "due_date": due(14)},
        {"title": "Review weather backup plan", "category": "Weather Plan", "due_date": due(7)},
        {"title": "Confirm vendor communications", "category": "Vendors", "due_date": due(10)},
        {"title": "Final balance due", "category": "Finance", "due_date": due(30)},
    ]


def _ensure_default_plan_tasks(client_id: int, wedding_date: date | None):
    existing_required = ClientPlanTask.query.filter_by(
        client_id=client_id, is_required=True
    ).count()
    if existing_required:
        return

    for template in _recommended_task_templates(wedding_date):
        task = ClientPlanTask(
            client_id=client_id,
            title=template["title"],
            category=template["category"],
            due_date=template["due_date"],
            is_required=True,
            is_completed=False,
        )
        db.session.add(task)
    db.session.commit()


def client_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("client.login", next=request.full_path.rstrip("?")), code=302)
        if getattr(current_user, "user_type", None) != "client":
            flash("Please sign in with a client account to continue.", "error")
            return redirect(url_for("client.login"), code=302)
        return f(*args, **kwargs)

    return wrapped


def _google_oauth_client():
    existing = oauth.create_client("google")
    if existing:
        return existing

    client_id = current_app.config.get("GOOGLE_CLIENT_ID", "")
    client_secret = current_app.config.get("GOOGLE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return None

    oauth.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth.create_client("google")


def _get_client_by_email(email: str) -> ClientUser | None:
    if not email:
        return None
    return ClientUser.query.filter_by(email=email.strip().lower()).first()


def _password_reset_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def _generate_password_reset_token(email: str) -> str:
    serializer = _password_reset_serializer()
    return serializer.dumps(email, salt="client-password-reset")


def _verify_password_reset_token(token: str) -> str | None:
    serializer = _password_reset_serializer()
    max_age = current_app.config.get("PASSWORD_RESET_TOKEN_MAX_AGE", 3600)
    try:
        return serializer.loads(token, salt="client-password-reset", max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


@client_bp.route("/")
def index():
    return redirect(url_for("client.dashboard"))


@client_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(lambda: current_app.config.get("CLIENT_LOGIN_GET_LIMIT", "120 per hour"), methods=["GET"])
@limiter.limit(
    lambda: current_app.config.get("CLIENT_LOGIN_POST_LIMIT", "5 per 15 minutes"),
    methods=["POST"],
    key_func=_client_login_rate_limit_key,
)
def login():
    if current_user.is_authenticated:
        if getattr(current_user, "user_type", None) == "client":
            return redirect(url_for("client.dashboard"))
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = ClientUser.query.filter_by(email=email, is_active=True).first()
        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("client.dashboard"))

        flash("Invalid email or password.", "error")

    google_enabled = bool(
        current_app.config.get("GOOGLE_CLIENT_ID")
        and current_app.config.get("GOOGLE_CLIENT_SECRET")
    )
    return render_template("client/login.html", google_enabled=google_enabled)


@client_bp.route("/register", methods=["GET", "POST"])
@limiter.limit(lambda: current_app.config.get("CLIENT_REGISTER_GET_LIMIT", "120 per hour"), methods=["GET"])
@limiter.limit(lambda: current_app.config.get("CLIENT_REGISTER_POST_LIMIT", "3 per hour"), methods=["POST"])
def register():
    if current_user.is_authenticated and getattr(current_user, "user_type", None) == "client":
        return redirect(url_for("client.dashboard"))

    if not current_app.config.get("CLIENT_SELF_REGISTRATION_ENABLED", False):
        if request.method == "POST":
            abort(403)
        return render_template("client/register_disabled.html"), 403

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not password:
            flash("Email and password are required.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif ClientUser.query.filter_by(email=email).first():
            flash("An account with this email already exists. Please sign in.", "error")
        else:
            user = ClientUser(
                email=email,
                full_name=full_name or None,
                auth_provider="email",
                is_active=True,
                last_login=datetime.utcnow(),
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            flash("Your client portal account is ready.", "success")
            return redirect(url_for("client.dashboard"))

    google_enabled = bool(
        current_app.config.get("GOOGLE_CLIENT_ID")
        and current_app.config.get("GOOGLE_CLIENT_SECRET")
    )
    return render_template("client/register.html", google_enabled=google_enabled)


@client_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        try:
            user = ClientUser.query.filter_by(email=email, is_active=True).first()
            if user:
                token = _generate_password_reset_token(user.email)
                app_obj = current_app._get_current_object()
                recipient_email = user.email
                recipient_name = user.full_name

                def send_job():
                    send_client_password_reset_email(
                        recipient_email, recipient_name, token
                    )

                run_in_background(
                    app_obj, send_job, "client password reset email"
                )
        except Exception:
            current_app.logger.exception("Forgot-password flow failed")
        flash(
            "If an account exists for that email, password reset instructions were sent.",
            "info",
        )
        return redirect(url_for("client.login"))
    return render_template("client/forgot_password.html")


@client_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    email = _verify_password_reset_token(token)
    if not email:
        flash("Password reset link is invalid or has expired.", "error")
        return redirect(url_for("client.forgot_password"))

    user = ClientUser.query.filter_by(email=email, is_active=True).first()
    if not user:
        flash("Unable to reset password for this account.", "error")
        return redirect(url_for("client.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            user.set_password(password)
            db.session.commit()
            flash("Your password has been reset. Please sign in.", "success")
            return redirect(url_for("client.login"))

    return render_template("client/reset_password.html", token=token)


@client_bp.route("/auth/google")
def auth_google():
    google = _google_oauth_client()
    if not google:
        flash("Google login is not configured yet.", "error")
        return redirect(url_for("client.login"))

    redirect_uri = url_for("client.auth_google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


@client_bp.route("/auth/google/callback")
@limiter.limit("10 per 15 minutes")
def auth_google_callback():
    google = _google_oauth_client()
    if not google:
        flash("Google login is not configured yet.", "error")
        return redirect(url_for("client.login"))

    token = google.authorize_access_token()
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = google.get("https://openidconnect.googleapis.com/v1/userinfo").json()

    email = (userinfo.get("email") or "").strip().lower()
    if not email:
        flash("Google login failed to provide an email address.", "error")
        return redirect(url_for("client.login"))

    oauth_subject = userinfo.get("sub")
    full_name = userinfo.get("name") or userinfo.get("given_name")
    avatar_url = userinfo.get("picture")

    user = _get_client_by_email(email)
    if not user and oauth_subject:
        user = ClientUser.query.filter_by(oauth_subject=oauth_subject).first()

    if not user and not current_app.config.get("CLIENT_SELF_REGISTRATION_ENABLED", False):
        flash("New account sign-up is invite-only. Please contact your planner.", "error")
        return redirect(url_for("client.login"))

    if not user:
        user = ClientUser(
            email=email,
            full_name=full_name,
            auth_provider="google",
            oauth_subject=oauth_subject,
            avatar_url=avatar_url,
            is_active=True,
        )
        db.session.add(user)
    else:
        user.full_name = user.full_name or full_name
        user.auth_provider = "google"
        user.oauth_subject = user.oauth_subject or oauth_subject
        user.avatar_url = avatar_url or user.avatar_url
        user.is_active = True

    user.last_login = datetime.utcnow()
    db.session.commit()

    login_user(user, remember=True)
    flash("Welcome to your client portal.", "success")
    return redirect(url_for("client.dashboard"))


@client_bp.route("/dashboard")
@client_required
def dashboard():
    email = current_user.email
    bookings = (
        BookingRequest.query.filter(
            db.or_(
                BookingRequest.client_id == current_user.id,
                BookingRequest.email.ilike(email),
            )
        )
        .order_by(BookingRequest.submitted_at.desc())
        .all()
    )
    service_requests = (
        ServiceRequest.query.filter(
            db.or_(
                ServiceRequest.client_id == current_user.id,
                ServiceRequest.email.ilike(email),
            )
        )
        .order_by(ServiceRequest.submitted_at.desc())
        .all()
    )
    contacts = (
        ContactSubmission.query.filter(
            db.or_(
                ContactSubmission.client_id == current_user.id,
                ContactSubmission.email.ilike(email),
            )
        )
        .order_by(ContactSubmission.submitted_at.desc())
        .all()
    )

    booking_ids = [item.id for item in bookings]
    payments = []
    if booking_ids:
        payments = (
            Payment.query.filter(Payment.booking_id.in_(booking_ids))
            .order_by(Payment.created_at.desc())
            .all()
        )

    total_paid_cents = sum(
        p.amount_cents for p in payments if p.status == Payment.STATUS_PAID
    )
    total_pending_cents = sum(
        p.amount_cents for p in payments if p.status == Payment.STATUS_PENDING
    )
    total_failed_cents = sum(
        p.amount_cents for p in payments if p.status == Payment.STATUS_FAILED
    )

    plan_selections = []
    for booking in bookings:
        if booking.package_id:
            plan_selections.append(
                {
                    "category": "Wedding Package",
                    "name": booking.package_id,
                    "date": booking.wedding_date,
                    "submitted_at": booking.submitted_at,
                    "status": booking.status,
                }
            )
    for req in service_requests:
        if req.selected_service:
            plan_selections.append(
                {
                    "category": f"{req.request_type.title()} Request",
                    "name": req.selected_service,
                    "date": req.event_date,
                    "submitted_at": req.submitted_at,
                    "status": req.status,
                }
            )

    communications = []
    for contact in contacts:
        communications.append(
            {
                "channel": "Contact Form",
                "subject": contact.subject or "General Inquiry",
                "message": contact.message,
                "date": contact.submitted_at,
            }
        )
    for req in service_requests:
        communications.append(
            {
                "channel": "Service Request",
                "subject": f"{req.request_type.title()} - {req.selected_service or 'General'}",
                "message": req.details or "Details pending.",
                "date": req.submitted_at,
            }
        )
    for booking in bookings:
        communications.append(
            {
                "channel": "Booking Request",
                "subject": f"Status: {booking.status.title()}",
                "message": booking.special_requests or "Booking submitted.",
                "date": booking.submitted_at,
            }
        )
    communications.sort(key=lambda item: item["date"], reverse=True)

    completed_tasks = ClientPlanTask.query.filter_by(
        client_id=current_user.id, is_completed=True
    ).count()
    total_tasks = ClientPlanTask.query.filter_by(client_id=current_user.id).count()
    progress_percent = int((completed_tasks / total_tasks) * 100) if total_tasks else 0

    next_task = (
        ClientPlanTask.query.filter_by(client_id=current_user.id, is_completed=False)
        .filter(ClientPlanTask.due_date.isnot(None))
        .order_by(ClientPlanTask.due_date.asc())
        .first()
    )
    open_service_requests = sum(
        1
        for r in service_requests
        if r.status in {ServiceRequest.STATUS_NEW, ServiceRequest.STATUS_REVIEWING}
    )
    action_queue_count = (
        open_service_requests
        + sum(1 for p in payments if p.status == Payment.STATUS_PENDING)
        + max(total_tasks - completed_tasks, 0)
    )

    today = date.today()
    upcoming_events = []
    for b in bookings:
        if b.wedding_date and b.wedding_date >= today:
            upcoming_events.append(
                {
                    "date": b.wedding_date,
                    "label": "Wedding Day",
                    "detail": b.package_id or "Selected package",
                }
            )
    for req in service_requests:
        if req.event_date and req.event_date >= today:
            upcoming_events.append(
                {
                    "date": req.event_date,
                    "label": f"{req.request_type.title()} Event",
                    "detail": req.selected_service or "Custom service",
                }
            )
    upcoming_events.sort(key=lambda item: item["date"])
    next_event = upcoming_events[0] if upcoming_events else None

    return render_template(
        "client/dashboard.html",
        bookings=bookings,
        service_requests=service_requests,
        payments=payments,
        total_paid_cents=total_paid_cents,
        total_pending_cents=total_pending_cents,
        total_failed_cents=total_failed_cents,
        plan_selections=plan_selections,
        communications=communications[:20],
        completed_tasks=completed_tasks,
        total_tasks=total_tasks,
        progress_percent=progress_percent,
        next_task=next_task,
        next_event=next_event,
        upcoming_events=upcoming_events[:8],
        action_queue_count=action_queue_count,
        open_service_requests=open_service_requests,
    )


@client_bp.route("/inspiration", methods=["GET", "POST"])
@client_required
def inspiration():
    record = ClientInspiration.query.filter_by(client_id=current_user.id).first()

    if request.method == "POST":
        action = request.form.get("action", "save").strip().lower()
        colors = request.form.getlist("colors")
        themes = request.form.getlist("themes")
        florals = request.form.getlist("florals")
        notes = request.form.get("notes", "").strip()
        custom_palette = request.form.get("custom_palette", "").strip()

        if not record:
            record = ClientInspiration(client_id=current_user.id)
            db.session.add(record)

        record.colors = ", ".join(colors) if colors else None
        record.themes = ", ".join(themes) if themes else None
        record.florals = ", ".join(florals) if florals else None
        if custom_palette:
            palette_line = f"Custom Palette: {custom_palette}"
            if notes:
                if palette_line not in notes:
                    notes = f"{notes}\n\n{palette_line}"
            else:
                notes = palette_line

        record.notes = notes or None
        db.session.commit()

        if action == "send-admin":
            summary_parts = [
                f"Client: {current_user.full_name or current_user.email}",
                f"Email: {current_user.email}",
                "",
                f"Selected Colors: {record.colors or 'None selected'}",
                f"Selected Themes: {record.themes or 'None selected'}",
                f"Selected Florals: {record.florals or 'None selected'}",
                "",
                f"Style Notes: {record.notes or 'None provided'}",
            ]
            admin_message = ContactSubmission(
                client_id=current_user.id,
                name=current_user.full_name or "Client User",
                email=current_user.email,
                subject="Inspiration Board Submission",
                services_interested="elda_florals, ceremony_packages, catering_menus",
                message="\n".join(summary_parts),
                is_read=False,
            )
            db.session.add(admin_message)
            db.session.commit()
            flash(
                "Your inspiration board has been sent to the planning team.",
                "success",
            )
        else:
            flash("Your wedding inspiration board has been updated.", "success")
        return redirect(url_for("client.inspiration"))

    selected_colors = set((record.colors or "").split(", ")) if record and record.colors else set()
    selected_themes = set((record.themes or "").split(", ")) if record and record.themes else set()
    selected_florals = set((record.florals or "").split(", ")) if record and record.florals else set()
    initial_custom_palette = ""
    if record and record.notes:
        marker = "Custom Palette:"
        for line in record.notes.splitlines():
            if line.strip().startswith(marker):
                initial_custom_palette = line.split(marker, 1)[1].strip()
                break

    return render_template(
        "client/inspiration.html",
        record=record,
        color_options=INSPO_COLOR_OPTIONS,
        theme_options=INSPO_THEME_OPTIONS,
        floral_options=INSPO_FLORAL_OPTIONS,
        selected_colors=selected_colors,
        selected_themes=selected_themes,
        selected_florals=selected_florals,
        initial_custom_palette=initial_custom_palette,
    )


@client_bp.route("/plan", methods=["GET", "POST"])
@client_required
def plan():
    latest_booking = (
        BookingRequest.query.filter(
            db.or_(
                BookingRequest.client_id == current_user.id,
                BookingRequest.email.ilike(current_user.email),
            )
        )
        .order_by(BookingRequest.submitted_at.desc())
        .first()
    )
    wedding_date = latest_booking.wedding_date if latest_booking else None
    _ensure_default_plan_tasks(current_user.id, wedding_date)

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add-task":
            title = request.form.get("title", "").strip()
            category = request.form.get("category", "").strip()
            due_date_raw = request.form.get("due_date", "").strip()
            notes = request.form.get("notes", "").strip()

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
                        client_id=current_user.id,
                        title=title,
                        category=category or "Custom",
                        due_date=parsed_due,
                        notes=notes or None,
                        is_required=False,
                    )
                )
                db.session.commit()
                flash("Custom task added.", "success")
        elif action == "submit-seating-list":
            seating_title = (request.form.get("seating_title") or "").strip() or "Seating List"
            guest_list = (request.form.get("guest_list") or "").strip()
            seating_notes = (request.form.get("seating_notes") or "").strip()

            if not guest_list:
                flash("Please provide at least one guest name for seating collaboration.", "error")
            else:
                lines = [line.strip() for line in guest_list.splitlines() if line.strip()]
                normalized_list = "\n".join(lines)
                payload = (
                    f"Guest List:\n{normalized_list}\n\n"
                    f"Notes:\n{seating_notes or 'None'}"
                )
                submission = ContactSubmission(
                    client_id=current_user.id,
                    name=current_user.full_name or "Client User",
                    email=current_user.email,
                    subject=f"Portal Request: {seating_title}",
                    services_interested="portal_message:seating_list",
                    message=payload,
                    is_read=False,
                )
                db.session.add(submission)
                db.session.commit()
                flash("Seating list sent to your planner.", "success")
        elif action == "add-rsvp-guest":
            full_name = (request.form.get("full_name") or "").strip()
            email = (request.form.get("email") or "").strip().lower() or None
            phone = (request.form.get("phone") or "").strip() or None
            group_label = (request.form.get("group_label") or "").strip() or None
            meal_choice = (request.form.get("meal_choice") or "").strip() or None
            notes = (request.form.get("notes") or "").strip() or None

            if not full_name:
                flash("Guest name is required.", "error")
            else:
                duplicate = ClientRsvpGuest.query.filter_by(
                    client_id=current_user.id,
                    full_name=full_name,
                ).first()
                if duplicate:
                    flash("That guest already exists in your RSVP list.", "info")
                else:
                    db.session.add(
                        ClientRsvpGuest(
                            client_id=current_user.id,
                            full_name=full_name,
                            email=email,
                            phone=phone,
                            group_label=group_label,
                            meal_choice=meal_choice,
                            notes=notes,
                            status=ClientRsvpGuest.STATUS_PENDING,
                        )
                    )
                    db.session.commit()
                    flash("Guest added to RSVP list.", "success")
        elif action == "update-rsvp-guest":
            guest_id = request.form.get("guest_id", type=int)
            guest = ClientRsvpGuest.query.filter_by(
                id=guest_id, client_id=current_user.id
            ).first_or_404()

            status = _normalize_rsvp_status(request.form.get("status"))
            meal_choice = (request.form.get("meal_choice") or "").strip() or None
            notes = (request.form.get("notes") or "").strip() or None
            table_name = (request.form.get("table_name") or "").strip() or None

            previous_status = guest.status
            guest.status = status
            guest.meal_choice = meal_choice
            guest.notes = notes
            guest.table_name = table_name
            if status != ClientRsvpGuest.STATUS_PENDING and previous_status != status:
                guest.responded_at = datetime.utcnow()

            db.session.commit()
            flash("RSVP guest updated.", "success")
        elif action == "delete-rsvp-guest":
            guest_id = request.form.get("guest_id", type=int)
            guest = ClientRsvpGuest.query.filter_by(
                id=guest_id, client_id=current_user.id
            ).first_or_404()
            db.session.delete(guest)
            db.session.commit()
            flash("Guest removed from RSVP list.", "success")
        return redirect(url_for("client.plan"))

    tasks = (
        ClientPlanTask.query.filter_by(client_id=current_user.id)
        .order_by(ClientPlanTask.due_date.asc().nulls_last(), ClientPlanTask.created_at.asc())
        .all()
    )
    completed = sum(1 for t in tasks if t.is_completed)
    progress_percent = int((completed / len(tasks)) * 100) if tasks else 0
    today = date.today()
    overdue = [
        t for t in tasks if not t.is_completed and t.due_date and t.due_date < today
    ]
    due_soon = [
        t
        for t in tasks
        if not t.is_completed and t.due_date and today <= t.due_date <= (today + timedelta(days=30))
    ]
    completed_recent = [
        t for t in tasks if t.is_completed
    ][:8]

    rsvp_guests = (
        ClientRsvpGuest.query.filter_by(client_id=current_user.id)
        .order_by(ClientRsvpGuest.full_name.asc())
        .all()
    )
    rsvp_counts = {
        ClientRsvpGuest.STATUS_ATTENDING: 0,
        ClientRsvpGuest.STATUS_PENDING: 0,
        ClientRsvpGuest.STATUS_DECLINED: 0,
        ClientRsvpGuest.STATUS_MAYBE: 0,
    }
    for guest in rsvp_guests:
        rsvp_counts[_normalize_rsvp_status(guest.status)] += 1

    important_dates = []
    if wedding_date:
        important_dates = [
            ("Wedding Day", wedding_date),
            ("Final Payment Target", wedding_date - timedelta(days=30)),
            ("License Application Window", wedding_date - timedelta(days=45)),
            ("Final Timeline Review", wedding_date - timedelta(days=14)),
        ]

    return render_template(
        "client/plan.html",
        tasks=tasks,
        progress_percent=progress_percent,
        completed=completed,
        total=len(tasks),
        overdue_count=len(overdue),
        due_soon_count=len(due_soon),
        completed_recent=completed_recent,
        wedding_date=wedding_date,
        important_dates=important_dates,
        rsvp_guests=rsvp_guests,
        rsvp_counts=rsvp_counts,
        rsvp_status_options=RSVP_STATUS_OPTIONS,
    )


@client_bp.route("/plan/task/<int:task_id>/toggle", methods=["POST"])
@client_required
def toggle_task(task_id):
    task = ClientPlanTask.query.filter_by(id=task_id, client_id=current_user.id).first_or_404()
    task.is_completed = not task.is_completed
    db.session.commit()
    return redirect(url_for("client.plan"))


@client_bp.route("/messages", methods=["GET", "POST"])
@client_required
def messages():
    if request.method == "POST":
        msg_type = request.form.get("message_type", "question").strip().lower()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        valid_types = {key for key, _ in PLANNER_MESSAGE_TYPES}
        if msg_type not in valid_types:
            msg_type = "question"

        if not message:
            flash("Please enter a message.", "error")
            return redirect(url_for("client.messages"))

        tagged_subject = f"Portal {msg_type.title()}: {subject or 'Message'}"
        submission = ContactSubmission(
            client_id=current_user.id,
            name=current_user.full_name or "Client User",
            email=current_user.email,
            subject=tagged_subject,
            services_interested=f"portal_message:{msg_type}",
            message=message,
            is_read=False,
        )
        db.session.add(submission)
        db.session.flush()

        uploaded_any = False
        for file_obj in request.files.getlist("attachments"):
            if not file_obj or not file_obj.filename:
                continue
            result = build_contact_attachment(
                file_obj=file_obj,
                submission_id=submission.id,
                uploaded_by="client",
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

        db.session.commit()
        flash(
            "Your message has been sent to your planner."
            + (" Attachments were included." if uploaded_any else ""),
            "success",
        )
        return redirect(url_for("client.messages"))

    messages_query = (
        ContactSubmission.query.filter(
            db.or_(
                ContactSubmission.client_id == current_user.id,
                ContactSubmission.email.ilike(current_user.email),
            )
        )
        .filter(ContactSubmission.subject.ilike("Portal %"))
        .order_by(ContactSubmission.submitted_at.desc())
    )
    items = messages_query.limit(30).all()

    return render_template(
        "client/messages.html",
        messages=items,
        message_types=PLANNER_MESSAGE_TYPES,
    )


@client_bp.route("/messages/attachments/<int:attachment_id>/download")
@client_required
def download_message_attachment(attachment_id):
    attachment = ContactAttachment.query.get_or_404(attachment_id)
    submission = attachment.submission
    if not submission:
        abort(404)

    allowed = False
    if submission.client_id == current_user.id:
        allowed = True
    elif submission.email and submission.email.strip().lower() == current_user.email.strip().lower():
        allowed = True

    if not allowed:
        abort(403)

    return send_file(
        BytesIO(attachment.data),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=attachment.filename,
    )


@client_bp.route("/logout")
@client_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))
