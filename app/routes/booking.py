from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask import current_app
from flask_mail import Message
from app import db, mail
from app.models.booking import BookingRequest
from app.models.service_request import ServiceRequest
from app.utils.background import run_in_background
from app.utils.client_accounts import get_or_create_client_by_email

booking_bp = Blueprint("booking", __name__)

PACKAGE_CHOICES = [
    ("package-a", "Ceremony Package A"),
    ("package-b", "Ceremony Package B"),
    ("package-c", "Ceremony Package C"),
    ("other", "Other / Not Sure Yet"),
]

SERVICE_REQUEST_CONFIG = {
    ServiceRequest.TYPE_PACKAGE: {
        "title": "Package Request",
        "heading": "Request a Ceremony Package",
        "subtitle": "Tell us which package you are considering and your preferred date.",
        "choices": [
            ("package-a", "Ceremony Package A"),
            ("package-b", "Ceremony Package B"),
            ("package-c", "Ceremony Package C"),
        ],
    },
    ServiceRequest.TYPE_VENUE: {
        "title": "Venue Request",
        "heading": "Request Venue Availability",
        "subtitle": "Share the venue option and event details you need.",
        "choices": [
            ("venue-option-a", "Venue Option A"),
            ("venue-option-b", "Venue Option B"),
            ("venue-option-c", "Venue Option C"),
            ("venue-gallery", "Venue Gallery / Tour"),
        ],
    },
    ServiceRequest.TYPE_CATERING: {
        "title": "Catering Request",
        "heading": "Request Catering Menus",
        "subtitle": "Select a menu style and tell us your guest needs.",
        "choices": [
            ("menu-a", "Menu Option A"),
            ("menu-b", "Menu Option B"),
            ("menu-c", "Menu Option C"),
            ("custom", "Custom Menu Consultation"),
        ],
    },
    ServiceRequest.TYPE_FLORALS: {
        "title": "Floral Request",
        "heading": "Request Floral Design Services",
        "subtitle": "Tell us your floral vision, colors, and scope.",
        "choices": [
            ("bouquet-boutonniere", "Bouquets & Boutonnieres"),
            ("ceremony-florals", "Ceremony Floral Design"),
            ("reception-centerpieces", "Reception Centerpieces"),
            ("full-styling", "Full Styling Package"),
        ],
    },
}


def _safe_rollback():
    try:
        db.session.rollback()
    except Exception:
        current_app.logger.exception("DB rollback failed after booking-route error")


@booking_bp.route("/book", methods=["GET", "POST"])
def book():
    selected_package = request.args.get("package", "").strip()

    if request.method == "POST":
        couple_name = request.form.get("couple_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        wedding_date_str = request.form.get("wedding_date", "").strip()
        package_id = request.form.get("package_id", "").strip()
        guest_count_str = request.form.get("guest_count", "").strip()
        venue_preference = request.form.get("venue_preference", "").strip()
        ceremony_time = request.form.get("ceremony_time", "").strip()
        special_requests = request.form.get("special_requests", "").strip()

        # Basic validation
        if not couple_name or not email:
            flash("Please fill in your name and email address.", "error")
            return render_template(
                "booking.html",
                package_choices=PACKAGE_CHOICES,
                selected_package=package_id or selected_package,
                form_data=request.form,
            )

        # Parse date
        wedding_date = None
        if wedding_date_str:
            try:
                wedding_date = datetime.strptime(wedding_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        guest_count = None
        if guest_count_str.isdigit():
            guest_count = int(guest_count_str)

        persisted = False
        try:
            client = get_or_create_client_by_email(email=email, full_name=couple_name)
            booking = BookingRequest(
                client_id=client.id if client else None,
                couple_name=couple_name,
                email=email,
                phone=phone or None,
                wedding_date=wedding_date,
                package_id=package_id or None,
                guest_count=guest_count,
                venue_preference=venue_preference or None,
                ceremony_time=ceremony_time or None,
                special_requests=special_requests or None,
            )
            db.session.add(booking)
            db.session.commit()
            persisted = True
        except Exception:
            _safe_rollback()
            current_app.logger.exception("Booking persistence failed")

        # Dispatch notification asynchronously so SMTP latency doesn't cause 5xx.
        try:
            recipient = current_app.config.get("CONTACT_RECIPIENT")
            if recipient:
                app_obj = current_app._get_current_object()
                msg = Message(
                    subject=f"New Booking Request — {couple_name}",
                    recipients=[recipient],
                    body=(
                        f"Couple: {couple_name}\n"
                        f"Email: {email}\n"
                        f"Phone: {phone or 'N/A'}\n"
                        f"Wedding Date: {wedding_date or 'TBD'}\n"
                        f"Package: {package_id or 'Not specified'}\n"
                        f"Guest Count: {guest_count or 'N/A'}\n"
                        f"Venue Preference: {venue_preference or 'N/A'}\n"
                        f"Ceremony Time: {ceremony_time or 'N/A'}\n\n"
                        f"Special Requests:\n{special_requests or 'None'}"
                    ),
                )

                def send_job():
                    mail.send(msg)

                run_in_background(app_obj, send_job, "booking notification email")
        except Exception:
            current_app.logger.exception("Booking email dispatch setup failed")

        if persisted:
            flash(
                "Your booking request has been submitted! We'll contact you within 24 hours "
                "to confirm availability and next steps.",
                "success",
            )
        else:
            flash(
                "Your booking inquiry was received, but we hit a temporary save issue. Our team was notified.",
                "info",
            )
        return redirect(url_for("booking.book"))

    return render_template(
        "booking.html",
        package_choices=PACKAGE_CHOICES,
        selected_package=selected_package,
        form_data=None,
    )


@booking_bp.route("/request/<request_type>", methods=["GET", "POST"])
def service_request(request_type):
    config = SERVICE_REQUEST_CONFIG.get(request_type)
    if not config:
        flash("Invalid request type.", "error")
        return redirect(url_for("booking.book"))

    selected = request.args.get("service", "").strip()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        event_date_str = request.form.get("event_date", "").strip()
        guest_count_str = request.form.get("guest_count", "").strip()
        selected_service = request.form.get("selected_service", "").strip()
        details = request.form.get("details", "").strip()

        if not name or not email:
            flash("Please include your name and email address.", "error")
            return render_template(
                "booking_service.html",
                request_type=request_type,
                config=config,
                selected_service=selected_service or selected,
                form_data=request.form,
            )

        event_date = None
        if event_date_str:
            try:
                event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        guest_count = int(guest_count_str) if guest_count_str.isdigit() else None

        persisted = False
        try:
            client = get_or_create_client_by_email(email=email, full_name=name)
            inquiry = ServiceRequest(
                client_id=client.id if client else None,
                request_type=request_type,
                name=name,
                email=email,
                phone=phone or None,
                event_date=event_date,
                guest_count=guest_count,
                selected_service=selected_service or None,
                details=details or None,
            )
            db.session.add(inquiry)
            db.session.commit()
            persisted = True
        except Exception:
            _safe_rollback()
            current_app.logger.exception("Service request persistence failed")

        try:
            recipient = current_app.config.get("CONTACT_RECIPIENT")
            if recipient:
                app_obj = current_app._get_current_object()
                msg = Message(
                    subject=f"New {config['title']} — {name}",
                    recipients=[recipient],
                    body=(
                        f"Type: {request_type}\n"
                        f"Name: {name}\n"
                        f"Email: {email}\n"
                        f"Phone: {phone or 'N/A'}\n"
                        f"Date: {event_date or 'TBD'}\n"
                        f"Guests: {guest_count or 'N/A'}\n"
                        f"Selection: {selected_service or 'N/A'}\n\n"
                        f"Details:\n{details or 'None'}"
                    ),
                )

                def send_job():
                    mail.send(msg)

                run_in_background(
                    app_obj, send_job, "service request notification email"
                )
        except Exception:
            current_app.logger.exception("Service request email dispatch setup failed")

        if persisted:
            flash("Your request has been submitted. Our team will follow up shortly.", "success")
        else:
            flash(
                "Your request was received, but we hit a temporary save issue. Our team was notified.",
                "info",
            )
        return redirect(url_for("booking.service_request", request_type=request_type))

    return render_template(
        "booking_service.html",
        request_type=request_type,
        config=config,
        selected_service=selected,
        form_data=None,
    )
