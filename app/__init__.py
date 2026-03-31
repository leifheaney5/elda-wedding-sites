import click
from datetime import datetime
import random
from urllib.parse import urlparse
from flask import Flask, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix
from config import config_map

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
oauth = OAuth()
limiter = Limiter(key_func=get_remote_address)

login_manager.login_view = "admin.login"
login_manager.login_message = "Please log in to access the admin panel."
login_manager.login_message_category = "warning"


def create_app(env="default"):
    app = Flask(__name__)
    app.config.from_object(config_map[env])
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    oauth.init_app(app)
    limiter.init_app(app)

    # Import models so Flask-Migrate detects them
    from app.models import (  # noqa: F401
        admin_user,
        client_user,
        client_inspiration,
        client_plan_task,
        client_rsvp_guest,
        planning_submission,
        seating_plan,
        contact,
        booking,
        payment,
        service_request,
        site_announcement,
        admin_automation_config,
        admin_report_template,
        email_subscriber,
        email_template,
        automation_rule,
        communication_log,
        vendor,
    )

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.packages import packages_bp
    from app.routes.venue import venue_bp
    from app.routes.florals import florals_bp
    from app.routes.catering import catering_bp
    from app.routes.contact import contact_bp
    from app.routes.booking import booking_bp
    from app.routes.about import about_bp
    from app.routes.admin import admin_bp
    from app.routes.client import client_bp
    from app.routes.vendor_api import vendor_api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(packages_bp, url_prefix="/packages")
    app.register_blueprint(venue_bp, url_prefix="/venue")
    app.register_blueprint(florals_bp)
    app.register_blueprint(catering_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(about_bp, url_prefix="/about")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(client_bp, url_prefix="/client")
    app.register_blueprint(vendor_api_bp, url_prefix="/api")

    @app.context_processor
    def inject_template_globals():
        from app.models.site_announcement import SiteAnnouncement
        from sqlalchemy.exc import OperationalError, ProgrammingError

        now = datetime.utcnow()
        try:
            active_announcement = (
                SiteAnnouncement.query.filter_by(is_active=True)
                .filter(
                    db.or_(
                        SiteAnnouncement.starts_at.is_(None),
                        SiteAnnouncement.starts_at <= now,
                    )
                )
                .filter(
                    db.or_(
                        SiteAnnouncement.ends_at.is_(None),
                        SiteAnnouncement.ends_at >= now,
                    )
                )
                .order_by(SiteAnnouncement.created_at.desc())
                .first()
            )
        except (OperationalError, ProgrammingError):
            active_announcement = None
        return {
            "now": now,
            "site_url": app.config.get("SITE_URL", ""),
            "client_self_registration_enabled": app.config.get(
                "CLIENT_SELF_REGISTRATION_ENABLED", False
            ),
            "site_announcement": active_announcement,
        }

    @app.before_request
    def enforce_canonical_host():
        if not app.config.get("ENFORCE_CANONICAL_HOST", False):
            return None
        canonical_site_url = app.config.get("SITE_URL", "")
        parsed = urlparse(canonical_site_url)
        canonical_host = (parsed.netloc or "").lower()
        if not canonical_host:
            return None

        incoming_host = (request.host or "").lower()
        if incoming_host == canonical_host:
            return None
        if incoming_host.startswith("localhost") or incoming_host.startswith("127.0.0.1"):
            return None

        path = request.full_path if request.query_string else request.path
        return redirect(f"{parsed.scheme or 'https'}://{canonical_host}{path}", code=301)

    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "X-XSS-Protection", app.config["SECURITY_X_XSS_PROTECTION"]
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        response.headers.setdefault("Content-Security-Policy", app.config["SECURITY_CSP"])
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower()
        if request.is_secure or forwarded_proto == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={app.config['SECURITY_HSTS_SECONDS']}; includeSubDomains; preload",
            )
        return response

    # CLI commands
    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True)
    @click.option(
        "--password", prompt=True, hide_input=True, confirmation_prompt=True
    )
    def create_admin(email, name, password):
        """Create the first admin user."""
        from app.models.admin_user import AdminUser

        if AdminUser.query.filter_by(email=email).first():
            click.echo(f"Admin with email {email} already exists.")
            return
        user = AdminUser(email=email, name=name, role="owner")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin user '{name}' ({email}) created successfully.")

    @app.cli.command("seed-historical-demo")
    @click.option("--months", default=12, show_default=True, type=int)
    @click.option("--per-month", default=8, show_default=True, type=int)
    @click.option(
        "--email-domain", default="demo.bbb.local", show_default=True, type=str
    )
    def seed_historical_demo(months, per_month, email_domain):
        """Seed demo contacts/bookings/service requests/payments over prior months."""
        from app.models.contact import ContactSubmission
        from app.models.booking import BookingRequest
        from app.models.service_request import ServiceRequest
        from app.models.payment import Payment

        if months < 1 or per_month < 1:
            click.echo("months and per-month must be >= 1")
            return

        rng = random.Random(42)
        now = datetime.utcnow()
        cursor = datetime(now.year, now.month, 1)

        package_options = ["package-a", "package-b", "package-c", "package-d"]
        venue_options = ["venue-option-a", "venue-option-b", "venue-option-c"]
        service_types = [
            ServiceRequest.TYPE_PACKAGE,
            ServiceRequest.TYPE_VENUE,
            ServiceRequest.TYPE_CATERING,
            ServiceRequest.TYPE_FLORALS,
        ]
        created = {"contacts": 0, "bookings": 0, "services": 0, "payments": 0}

        booking_ids_for_payments: list[int] = []

        for month_offset in range(months):
            period = datetime(cursor.year, cursor.month, 1)
            idx_prefix = period.strftime("%Y%m")

            for item_idx in range(per_month):
                day = 1 + ((item_idx * 3) % 26)
                submitted_dt = datetime(period.year, period.month, day, 9 + (item_idx % 8), 15)
                suffix = f"{idx_prefix}-{item_idx+1:02d}"

                contact_email = f"lead-{suffix}@{email_domain}"
                contact_subject = f"Demo Inquiry {suffix}"
                exists_contact = ContactSubmission.query.filter_by(
                    email=contact_email, subject=contact_subject
                ).first()
                if not exists_contact:
                    db.session.add(
                        ContactSubmission(
                            name=f"Demo Lead {suffix}",
                            email=contact_email,
                            phone="555-0100",
                            subject=contact_subject,
                            services_interested="package,venue",
                            message="Demo seeded contact for admin dashboard trends.",
                            submitted_at=submitted_dt,
                            is_read=(item_idx % 3 == 0),
                        )
                    )
                    created["contacts"] += 1

            booking_count = max(2, per_month // 2)
            for item_idx in range(booking_count):
                day = 2 + ((item_idx * 5) % 24)
                submitted_dt = datetime(period.year, period.month, day, 10 + (item_idx % 6), 0)
                suffix = f"{idx_prefix}-b{item_idx+1:02d}"
                booking_email = f"booking-{suffix}@{email_domain}"
                exists_booking = BookingRequest.query.filter_by(
                    email=booking_email,
                    couple_name=f"Demo Couple {suffix}",
                ).first()
                if exists_booking:
                    booking_ids_for_payments.append(exists_booking.id)
                    continue

                booking = BookingRequest(
                    couple_name=f"Demo Couple {suffix}",
                    email=booking_email,
                    phone="555-0200",
                    wedding_date=(submitted_dt.date()),
                    package_id=package_options[item_idx % len(package_options)],
                    guest_count=10 + (item_idx * 8),
                    venue_preference=venue_options[item_idx % len(venue_options)],
                    status=[
                        BookingRequest.STATUS_NEW,
                        BookingRequest.STATUS_REVIEWING,
                        BookingRequest.STATUS_CONFIRMED,
                    ][item_idx % 3],
                    submitted_at=submitted_dt,
                )
                db.session.add(booking)
                db.session.flush()
                booking_ids_for_payments.append(booking.id)
                created["bookings"] += 1

            service_count = max(2, per_month // 2)
            for item_idx in range(service_count):
                day = 3 + ((item_idx * 4) % 23)
                submitted_dt = datetime(period.year, period.month, day, 11 + (item_idx % 5), 30)
                suffix = f"{idx_prefix}-s{item_idx+1:02d}"
                service_email = f"service-{suffix}@{email_domain}"
                service_type = service_types[item_idx % len(service_types)]
                exists_service = ServiceRequest.query.filter_by(
                    email=service_email,
                    request_type=service_type,
                    name=f"Demo Service {suffix}",
                ).first()
                if exists_service:
                    continue

                db.session.add(
                    ServiceRequest(
                        request_type=service_type,
                        name=f"Demo Service {suffix}",
                        email=service_email,
                        phone="555-0300",
                        event_date=submitted_dt.date(),
                        guest_count=20 + (item_idx * 5),
                        selected_service="Demo package",
                        details="Demo seeded service request for trend reporting.",
                        status=[
                            ServiceRequest.STATUS_NEW,
                            ServiceRequest.STATUS_REVIEWING,
                            ServiceRequest.STATUS_CONTACTED,
                            ServiceRequest.STATUS_CLOSED,
                        ][item_idx % 4],
                        submitted_at=submitted_dt,
                    )
                )
                created["services"] += 1

            if cursor.month == 1:
                cursor = datetime(cursor.year - 1, 12, 1)
            else:
                cursor = datetime(cursor.year, cursor.month - 1, 1)

        db.session.flush()

        for booking_id in booking_ids_for_payments:
            if rng.random() > 0.65:
                continue
            booking = BookingRequest.query.get(booking_id)
            if not booking:
                continue
            created_dt = booking.submitted_at or datetime.utcnow()
            status = Payment.STATUS_PAID if rng.random() > 0.25 else Payment.STATUS_PENDING
            amount_cents = rng.choice([15000, 25000, 50000, 75000])
            payment_key = f"demo_pi_{booking.id}_{created_dt.strftime('%Y%m')}"
            if Payment.query.filter_by(stripe_payment_intent_id=payment_key).first():
                continue
            db.session.add(
                Payment(
                    booking_id=booking.id,
                    stripe_payment_intent_id=payment_key,
                    amount_cents=amount_cents,
                    currency="usd",
                    status=status,
                    description="Demo seeded payment",
                    created_at=created_dt,
                    paid_at=created_dt if status == Payment.STATUS_PAID else None,
                )
            )
            created["payments"] += 1

        db.session.commit()
        click.echo(
            "Seed complete: "
            + ", ".join([f"{key}={value}" for key, value in created.items()])
        )

    @app.cli.command("send-weekly-admin-update")
    @click.option("--recipient", "recipients", multiple=True)
    @click.option("--week-ending", default="", type=str)
    @click.option("--include-unpaid/--paid-only", default=True)
    def send_weekly_admin_update(recipients, week_ending, include_unpaid):
        """Send weekly business digest to active admins/staff or override recipient list."""
        from datetime import datetime as dt
        from app.utils.email import send_weekly_admin_staff_update

        parsed_date = None
        if week_ending:
            try:
                parsed_date = dt.strptime(week_ending.strip(), "%Y-%m-%d").date()
            except ValueError:
                click.echo("Invalid --week-ending format. Use YYYY-MM-DD")
                return

        try:
            result = send_weekly_admin_staff_update(
                week_ending=parsed_date,
                include_unpaid=include_unpaid,
                recipients_override=list(recipients) if recipients else None,
            )
        except Exception as exc:
            click.echo(f"Weekly update failed: {exc}")
            return

        if result.get("sent"):
            click.echo(
                "Weekly update sent to "
                + ", ".join(result.get("recipients", []))
            )
        else:
            click.echo(f"Weekly update not sent: {result.get('reason', 'unknown')}")

    @app.cli.command("run-admin-autopilot")
    def run_admin_autopilot_cli():
        """Run admin autopilot rules and print a compact summary."""
        from app.services.admin_autopilot import run_admin_autopilot

        result = run_admin_autopilot(trigger="cli", actor_admin_user_id=None)
        click.echo(
            "Autopilot run complete: "
            f"enabled={result['enabled']} "
            f"unread={result['unread_contacts']} "
            f"open_services={result['open_service_requests']} "
            f"pending_payments={result['pending_payments']} "
            f"auto_transitioned={result['auto_transitioned_to_reviewing']}"
        )

    @app.cli.command("seed-communication-templates")
    def seed_communication_templates_cli():
        """Create default communication templates and automation rules."""
        from app.services.communication_templates import ensure_default_email_templates
        from app.services.communication_automation import evaluate_automation_rules

        created_templates = ensure_default_email_templates()
        evaluate_automation_rules(dry_run=True)
        click.echo(f"Default communication templates created: {created_templates}")

    @app.cli.command("run-communication-automation")
    @click.option("--dry-run", is_flag=True, default=False)
    @click.option("--dispatch-limit", default=200, show_default=True, type=int)
    def run_communication_automation_cli(dry_run: bool, dispatch_limit: int):
        """Evaluate communication triggers and send due queued emails."""
        from app.services.communication_templates import ensure_default_email_templates
        from app.services.communication_automation import evaluate_automation_rules
        from app.services.communications import dispatch_due_communications

        ensure_default_email_templates()
        queued_result = evaluate_automation_rules(dry_run=dry_run)
        if dry_run:
            click.echo(f"[dry-run] Candidate emails queued: {queued_result.get('queued', 0)}")
            return

        sent_result = dispatch_due_communications(limit=max(1, dispatch_limit))
        click.echo(
            "Communication worker complete "
            f"(queued={queued_result.get('queued', 0)}, "
            f"sent={sent_result.get('sent', 0)}, failed={sent_result.get('failed', 0)})"
        )

    return app
