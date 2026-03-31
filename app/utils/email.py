from datetime import date

from flask import current_app, url_for
from flask_mail import Message
from app import mail
from app.models.admin_user import AdminUser
from app.services.weekly_digest import build_weekly_digest_data


def send_contact_notification(submission):
    """Send admin notification email for a new contact submission."""
    try:
        recipient = current_app.config.get("CONTACT_RECIPIENT")
        if not recipient:
            return
        msg = Message(
            subject=f"[ELDA] New Contact: {submission.subject or 'General Inquiry'}",
            recipients=[recipient],
            body=(
                f"New contact form submission received.\n\n"
                f"Name: {submission.name}\n"
                f"Email: {submission.email}\n"
                f"Phone: {submission.phone or 'N/A'}\n"
                f"Subject: {submission.subject or 'N/A'}\n\n"
                f"Message:\n{submission.message}\n\n"
                f"View in admin: /admin/contacts/{submission.id}"
            ),
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f"Failed to send contact notification email: {e}")


def send_booking_notification(booking):
    """Send admin notification email for a new booking request."""
    try:
        recipient = current_app.config.get("CONTACT_RECIPIENT")
        if not recipient:
            return
        msg = Message(
            subject=f"[ELDA] New Booking Request — {booking.couple_name}",
            recipients=[recipient],
            body=(
                f"New booking request received!\n\n"
                f"Couple: {booking.couple_name}\n"
                f"Email: {booking.email}\n"
                f"Phone: {booking.phone or 'N/A'}\n"
                f"Wedding Date: {booking.wedding_date or 'TBD'}\n"
                f"Package: {booking.package_id or 'Not specified'}\n"
                f"Guest Count: {booking.guest_count or 'N/A'}\n\n"
                f"Special Requests:\n{booking.special_requests or 'None'}\n\n"
                f"View in admin: /admin/bookings/{booking.id}"
            ),
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f"Failed to send booking notification email: {e}")


def send_booking_confirmation(booking):
    """Send confirmation email to the couple after booking request submission."""
    try:
        msg = Message(
            subject="We received your wedding inquiry — ELDA Wedding Sites",
            recipients=[booking.email],
            body=(
                f"Hello {booking.couple_name},\n\n"
                f"Thank you for reaching out to ELDA Wedding Sites!\n\n"
                f"We have received your wedding inquiry and will be in touch within 24 hours "
                f"to confirm availability and discuss next steps.\n\n"
                f"Here's a summary of your request:\n"
                f"  Package: {booking.package_id or 'Not yet specified'}\n"
                f"  Wedding Date: {booking.wedding_date or 'TBD'}\n"
                f"  Guest Count: {booking.guest_count or 'TBD'}\n\n"
                f"If you have any immediate questions, feel free to reply to this email.\n\n"
                f"We look forward to making your special day perfect!\n\n"
                f"Warmly,\n"
                f"ELDA Wedding Sites\n"
                f"123 Example Avenue Suite 100, Example City, ST\n"
            ),
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f"Failed to send booking confirmation email: {e}")


def send_client_password_reset_email(recipient_email: str, recipient_name: str | None, token: str):
    """Send password reset instructions to a client user."""
    try:
        reset_link = url_for("client.reset_password", token=token, _external=True)
        msg = Message(
            subject="Reset your ELDA Wedding Sites portal password",
            recipients=[recipient_email],
            body=(
                f"Hello {recipient_name or 'Client'},\n\n"
                "We received a request to reset your password.\n\n"
                f"Use this secure link to set a new password:\n{reset_link}\n\n"
                f"This link expires in {int(current_app.config.get('PASSWORD_RESET_TOKEN_MAX_AGE', 3600) / 60)} minutes.\n"
                "If you did not request this, you can safely ignore this email.\n\n"
                "ELDA Wedding Sites"
            ),
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f"Failed to send password reset email: {e}")


def _weekly_digest_body_text(report: dict) -> str:
        kpi = report["kpi"]
        daily = report["daily"]
        status = report["booking_status"]
        lines = [
                "ELDA Wedding Sites — Weekly Business Update",
                f"Window: {report['week_start'].isoformat()} to {report['week_ending'].isoformat()}",
                "",
                f"Total Leads: {kpi['total_leads']}",
                f"Contacts: {kpi['contacts']} | Bookings: {kpi['bookings']} | Service Requests: {kpi['services']}",
                f"Conversion: {kpi['conversion_pct']}%",
                f"Paid Revenue: ${kpi['paid_revenue_dollars']:.2f}",
                f"Pending Revenue: ${kpi['pending_revenue_dollars']:.2f}",
                f"Effective Revenue View: ${kpi['effective_revenue_dollars']:.2f}",
                f"Unread Contacts: {kpi['unread_contacts']}",
                "",
                "Booking Status Mix:",
                f"  New: {status.get('new', 0)}",
                f"  Reviewing: {status.get('reviewing', 0)}",
                f"  Confirmed: {status.get('confirmed', 0)}",
                f"  Cancelled: {status.get('cancelled', 0)}",
                "",
                "Daily Activity:",
        ]
        for i, label in enumerate(daily["labels"]):
                lines.append(
                        f"  {label}: C={daily['contacts'][i]} B={daily['bookings'][i]} S={daily['services'][i]} Rev=${daily['revenue_dollars'][i]:.2f}"
                )
        return "\n".join(lines)


def _weekly_digest_body_html(report: dict) -> str:
        kpi = report["kpi"]
        daily = report["daily"]
        status = report["booking_status"]
        max_daily = report["max_daily"]

        rows = []
        for i, label in enumerate(daily["labels"]):
                c_pct = int(round((daily["contacts"][i] / max_daily["contacts"]) * 100)) if max_daily["contacts"] else 0
                b_pct = int(round((daily["bookings"][i] / max_daily["bookings"]) * 100)) if max_daily["bookings"] else 0
                s_pct = int(round((daily["services"][i] / max_daily["services"]) * 100)) if max_daily["services"] else 0
                rows.append(
                        f"""
                        <tr>
                            <td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{label}</td>
                            <td style='padding:8px;border-bottom:1px solid #e5e7eb;'><div style='background:#f3f4f6;height:8px;border-radius:999px;'><div style='width:{c_pct}%;background:#4A9B8E;height:8px;border-radius:999px;'></div></div></td>
                            <td style='padding:8px;border-bottom:1px solid #e5e7eb;'><div style='background:#f3f4f6;height:8px;border-radius:999px;'><div style='width:{b_pct}%;background:#1A2E44;height:8px;border-radius:999px;'></div></div></td>
                            <td style='padding:8px;border-bottom:1px solid #e5e7eb;'><div style='background:#f3f4f6;height:8px;border-radius:999px;'><div style='width:{s_pct}%;background:#E07B6A;height:8px;border-radius:999px;'></div></div></td>
                            <td style='padding:8px;border-bottom:1px solid #e5e7eb;'>${daily['revenue_dollars'][i]:.2f}</td>
                        </tr>
                        """
                )

        return f"""
        <html>
            <body style='font-family:Arial,sans-serif;color:#1f2937;'>
                <h2 style='margin-bottom:6px;'>ELDA Wedding Sites — Weekly Business Update</h2>
                <p style='color:#6b7280;margin-top:0;'>Window: {report['week_start'].isoformat()} to {report['week_ending'].isoformat()}</p>

                <table style='width:100%;max-width:900px;border-collapse:collapse;margin-bottom:18px;'>
                    <tr>
                        <td style='padding:10px;border:1px solid #e5e7eb;'>Total Leads<br><strong style='font-size:22px;'>{kpi['total_leads']}</strong></td>
                        <td style='padding:10px;border:1px solid #e5e7eb;'>Bookings<br><strong style='font-size:22px;'>{kpi['bookings']}</strong></td>
                        <td style='padding:10px;border:1px solid #e5e7eb;'>Conversion<br><strong style='font-size:22px;'>{kpi['conversion_pct']}%</strong></td>
                        <td style='padding:10px;border:1px solid #e5e7eb;'>Revenue View<br><strong style='font-size:22px;'>${kpi['effective_revenue_dollars']:.2f}</strong></td>
                    </tr>
                </table>

                <h3 style='margin-bottom:8px;'>Daily Activity Visuals</h3>
                <table style='width:100%;max-width:900px;border-collapse:collapse;'>
                    <thead>
                        <tr>
                            <th style='text-align:left;padding:8px;border-bottom:1px solid #d1d5db;'>Day</th>
                            <th style='text-align:left;padding:8px;border-bottom:1px solid #d1d5db;'>Contacts</th>
                            <th style='text-align:left;padding:8px;border-bottom:1px solid #d1d5db;'>Bookings</th>
                            <th style='text-align:left;padding:8px;border-bottom:1px solid #d1d5db;'>Services</th>
                            <th style='text-align:left;padding:8px;border-bottom:1px solid #d1d5db;'>Revenue</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>

                <h3 style='margin-top:16px;margin-bottom:8px;'>Booking Status Mix</h3>
                <p>New: <strong>{status.get('new', 0)}</strong> · Reviewing: <strong>{status.get('reviewing', 0)}</strong> · Confirmed: <strong>{status.get('confirmed', 0)}</strong> · Cancelled: <strong>{status.get('cancelled', 0)}</strong></p>
            </body>
        </html>
        """


def send_weekly_admin_staff_update(
        week_ending: date | None = None,
        include_unpaid: bool = True,
        recipients_override: list[str] | None = None,
) -> dict:
        week_ending = week_ending or date.today()
        report = build_weekly_digest_data(week_ending=week_ending, include_unpaid=include_unpaid)

        recipients = recipients_override or [
                user.email
                for user in AdminUser.query.filter_by(is_active=True).all()
                if user.email
        ]
        recipients = sorted({r.strip().lower() for r in recipients if r and r.strip()})
        if not recipients:
                return {"sent": False, "reason": "no_recipients"}

        subject = f"[ELDA] Weekly Business Update ({report['week_start'].isoformat()} to {report['week_ending'].isoformat()})"
        sender = (
            current_app.config.get("MAIL_DEFAULT_SENDER")
            or current_app.config.get("CONTACT_RECIPIENT")
            or "no-reply@eldaweddingsites.example"
        )
        msg = Message(
                subject=subject,
                recipients=recipients,
            sender=sender,
                body=_weekly_digest_body_text(report),
                html=_weekly_digest_body_html(report),
        )
        mail.send(msg)
        return {"sent": True, "recipient_count": len(recipients), "recipients": recipients}


def send_bulk_message(
    recipients: list[str],
    subject: str,
    body: str,
    html: str | None = None,
    sender: str | None = None,
) -> dict:
    normalized_recipients = sorted(
        {item.strip().lower() for item in recipients if item and item.strip()}
    )
    if not normalized_recipients:
        return {"sent": False, "reason": "no_recipients", "recipient_count": 0}

    sender_email = (
        sender
        or current_app.config.get("MAIL_DEFAULT_SENDER")
        or "info@eldaweddingsites.example"
    )

    sent_count = 0
    errors: list[str] = []
    for recipient in normalized_recipients:
        try:
            msg = Message(
                subject=subject,
                recipients=[recipient],
                sender=sender_email,
                body=body,
                html=html,
            )
            mail.send(msg)
            sent_count += 1
        except Exception as exc:
            errors.append(f"{recipient}: {exc}")

    return {
        "sent": sent_count > 0,
        "recipient_count": sent_count,
        "requested_count": len(normalized_recipients),
        "errors": errors,
    }


def automated_subscriber_update_content() -> tuple[str, str, str]:
    today_str = date.today().strftime("%B %d, %Y")
    subject = "ELDA Wedding Sites | Wedding planning updates"
    body = (
        "Hello from ELDA Wedding Sites,\n\n"
        "Thank you for subscribing to our planning list. Here is your latest update:\n"
        "- New ceremony package availability windows are open\n"
        "- Venue and styling consultations are available this month\n"
        "- Planning Ops now supports live seating collaboration with your planner\n\n"
        "Need help right away? Reply to this email and our team will assist you.\n\n"
        f"Sent on {today_str}\n"
        "ELDA Wedding Sites\n"
        "info@eldaweddingsites.example"
    )
    html = (
        "<html><body style='font-family:Arial,sans-serif;color:#1f2937;'>"
        "<h2 style='color:#1A2E44;'>ELDA Wedding Sites Updates</h2>"
        "<p>Thank you for subscribing to our planning list. Here is your latest update:</p>"
        "<ul>"
        "<li>New ceremony package availability windows are open</li>"
        "<li>Venue and styling consultations are available this month</li>"
        "<li>Planning Ops now supports live seating collaboration with your planner</li>"
        "</ul>"
        "<p>Need help right away? Reply to this email and our team will assist you.</p>"
        f"<p style='color:#6b7280;font-size:12px;'>Sent on {today_str}</p>"
        "<p>ELDA Wedding Sites<br/>info@eldaweddingsites.example</p>"
        "</body></html>"
    )
    return subject, body, html
