from flask import Blueprint, render_template, redirect, url_for, flash, request
from datetime import datetime
from app import db, mail
from app.models.contact import ContactSubmission
from app.models.email_subscriber import EmailSubscriber
from flask_mail import Message
from flask import current_app
from app.utils.background import run_in_background
from app.utils.client_accounts import get_or_create_client_by_email

contact_bp = Blueprint("contact", __name__)

CONTACT_SERVICE_OPTIONS = [
    ("ceremony_packages", "Ceremony Packages"),
    ("venue_packages", "Venue Packages"),
    ("catering_menus", "Catering Menus"),
    ("elda_florals", "ELDA Florals"),
    ("planning_guide", "Complete Planning Guide"),
    ("vow_renewals", "Vow Renewals"),
]


def _safe_rollback():
    try:
        db.session.rollback()
    except Exception:
        current_app.logger.exception("DB rollback failed after contact-route error")


@contact_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        subject = request.form.get("subject", "").strip()
        services = request.form.getlist("services_interested")
        message = request.form.get("message", "").strip()

        # Basic validation
        if not name or not email or not message:
            flash("Please fill in all required fields.", "error")
            return render_template(
                "contact.html",
                service_options=CONTACT_SERVICE_OPTIONS,
            )

        persisted = False
        try:
            client = get_or_create_client_by_email(email=email, full_name=name)
            submission = ContactSubmission(
                client_id=client.id if client else None,
                name=name,
                email=email,
                phone=phone or None,
                subject=subject or None,
                services_interested=", ".join(services) if services else None,
                message=message,
            )
            db.session.add(submission)
            db.session.commit()
            persisted = True
        except Exception:
            _safe_rollback()
            current_app.logger.exception("Contact submission persistence failed")

        # Dispatch email asynchronously so SMTP delays can't block form completion.
        try:
            recipient = current_app.config.get("CONTACT_RECIPIENT")
            if recipient:
                app_obj = current_app._get_current_object()
                msg = Message(
                    subject=f"New Contact Form Submission — {subject or 'General Inquiry'}",
                    recipients=[recipient],
                    body=(
                        f"Name: {name}\n"
                        f"Email: {email}\n"
                        f"Phone: {phone or 'N/A'}\n"
                        f"Subject: {subject or 'N/A'}\n\n"
                        f"Services Interested: {', '.join(services) if services else 'N/A'}\n\n"
                        f"Message:\n{message}"
                    ),
                )

                def send_job():
                    mail.send(msg)

                run_in_background(app_obj, send_job, "contact notification email")
        except Exception:
            current_app.logger.exception("Contact email dispatch setup failed")

        if persisted:
            flash(
                "Thank you! Your message has been received. We'll be in touch soon.",
                "success",
            )
        else:
            flash(
                "Your inquiry was received, but we hit a temporary save issue. Our team was still notified.",
                "info",
            )
        return redirect(url_for("contact.contact"))

    return render_template(
        "contact.html",
        service_options=CONTACT_SERVICE_OPTIONS,
    )


@contact_bp.route("/sales-lead", methods=["GET", "POST"])
def sales_lead():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        event_date = request.form.get("event_date", "").strip()
        event_type = request.form.get("event_type", "").strip()
        budget_range = request.form.get("budget_range", "").strip()
        guest_count = request.form.get("guest_count", "").strip()
        referral_source = request.form.get("referral_source", "").strip()
        notes = request.form.get("notes", "").strip()

        if not name or not email:
            flash("Name and email are required.", "error")
            return render_template("sales_lead.html")

        persisted = False
        try:
            client = get_or_create_client_by_email(email=email, full_name=name)
            submission = ContactSubmission(
                client_id=client.id if client else None,
                name=name,
                email=email,
                phone=phone or None,
                subject=f"Sales Lead — {event_type or 'Wedding'}",
                services_interested="sales_lead",
                message=(
                    f"Event Date: {event_date or 'TBD'}\n"
                    f"Event Type: {event_type or 'Not specified'}\n"
                    f"Budget: {budget_range or 'Not specified'}\n"
                    f"Guest Count: {guest_count or 'Not specified'}\n"
                    f"Referral Source: {referral_source or 'Not specified'}\n\n"
                    f"Notes:\n{notes or 'None'}"
                ),
            )
            db.session.add(submission)
            db.session.commit()
            persisted = True
        except Exception:
            _safe_rollback()
            current_app.logger.exception("Sales lead persistence failed")

        if persisted:
            flash("Sales lead submitted successfully.", "success")
        else:
            flash(
                "Sales lead was received, but we hit a temporary save issue. Please retry later.",
                "error",
            )
        return redirect(url_for("contact.sales_lead"))

    return render_template("sales_lead.html")


@contact_bp.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email", "").strip().lower()
    name = request.form.get("name", "").strip() or None
    source = (request.form.get("source") or EmailSubscriber.SOURCE_FOOTER).strip().lower()

    if not email:
        flash("Please enter a valid email to subscribe.", "error")
        return redirect(request.referrer or url_for("main.home"))

    if source not in {
        EmailSubscriber.SOURCE_FOOTER,
        EmailSubscriber.SOURCE_CLIENT_PLAN,
        EmailSubscriber.SOURCE_ADMIN,
    }:
        source = EmailSubscriber.SOURCE_FOOTER

    try:
        existing = EmailSubscriber.query.filter_by(email=email).first()
        if existing:
            existing.name = name or existing.name
            existing.is_active = True
            existing.source = source
            existing.unsubscribed_at = None
            if not existing.subscribed_at:
                existing.subscribed_at = datetime.utcnow()
            message = "You are already on the list. Subscription has been refreshed."
        else:
            db.session.add(
                EmailSubscriber(
                    email=email,
                    name=name,
                    is_active=True,
                    source=source,
                )
            )
            message = "Thanks for subscribing to ELDA Wedding Sites updates."

        db.session.commit()
        flash(message, "success")
    except Exception:
        _safe_rollback()
        current_app.logger.exception("Subscriber signup failed")
        flash("Subscription failed temporarily. Please try again.", "error")

    return redirect(request.referrer or url_for("main.home"))
