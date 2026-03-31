from __future__ import annotations

from app import db
from app.models.email_template import EmailTemplate


def ensure_default_email_templates() -> int:
    defaults = [
        {
            "key": "payment_due_reminder",
            "name": "Payment Reminder",
            "category": EmailTemplate.CATEGORY_LIFECYCLE,
            "audience": EmailTemplate.AUDIENCE_CLIENT,
            "description": "Automated reminder for upcoming payment due dates.",
            "subject_template": "Payment Reminder: {{payment_amount}} due {{payment_due_date}}",
            "body_html_template": (
                "<p>Hello {{client_name}},</p>"
                "<p>This is a gentle reminder that your upcoming payment of <strong>{{payment_amount}}</strong> is due on <strong>{{payment_due_date}}</strong>.</p>"
                "<p>Your wedding date is {{wedding_date}}. If you need help, reply and our team will assist you right away.</p>"
                "<p>With care,<br>ELDA Wedding Sites</p>"
            ),
            "body_markdown_template": (
                "Hello {{client_name}},\n\n"
                "Your payment of {{payment_amount}} is due on {{payment_due_date}}.\n"
                "Wedding date: {{wedding_date}}.\n\n"
                "With care,\nELDA Wedding Sites"
            ),
            "is_system": True,
        },
        {
            "key": "rsvp_soft_deadline_followup",
            "name": "RSVP Soft Deadline Follow-up",
            "category": EmailTemplate.CATEGORY_LIFECYCLE,
            "audience": EmailTemplate.AUDIENCE_CLIENT,
            "description": "Automated follow-up when RSVP soft deadline is reached.",
            "subject_template": "RSVP Follow-up: {{pending_rsvp_count}} guest(s) still pending",
            "body_html_template": (
                "<p>Hello {{client_name}},</p>"
                "<p>Your RSVP soft deadline is today. We still have <strong>{{pending_rsvp_count}}</strong> guest response(s) pending.</p>"
                "<p>Please update your portal so we can keep your seating and vendor timelines accurate for {{wedding_date}}.</p>"
                "<p>With care,<br>ELDA Wedding Sites Planning Team</p>"
            ),
            "body_markdown_template": (
                "Hello {{client_name}},\n\n"
                "Your RSVP soft deadline is today. Pending RSVPs: {{pending_rsvp_count}}.\n"
                "Please update before {{wedding_date}} planning lock-in.\n\n"
                "ELDA Wedding Sites Planning Team"
            ),
            "is_system": True,
        },
        {
            "key": "wedding_countdown_milestone",
            "name": "Wedding Countdown Milestone",
            "category": EmailTemplate.CATEGORY_LIFECYCLE,
            "audience": EmailTemplate.AUDIENCE_CLIENT,
            "description": "Countdown milestone communication.",
            "subject_template": "{{countdown_label}} — ELDA Wedding Sites",
            "body_html_template": (
                "<p>Hello {{client_name}},</p>"
                "<p><strong>{{countdown_label}}</strong> is here — only {{days_remaining}} day(s) until {{wedding_date}}.</p>"
                "<p>Take a breath, review your checklist, and let us know if you want us to review final logistics this week.</p>"
                "<p>With excitement,<br>ELDA Wedding Sites</p>"
            ),
            "body_markdown_template": (
                "Hello {{client_name}},\n\n"
                "{{countdown_label}} is here. {{days_remaining}} day(s) until {{wedding_date}}.\n"
                "Reply if you want a final logistics review.\n\n"
                "ELDA Wedding Sites"
            ),
            "is_system": True,
        },
        {
            "key": "vendor_confirmation_ping",
            "name": "Vendor Arrival Confirmation",
            "category": EmailTemplate.CATEGORY_LIFECYCLE,
            "audience": EmailTemplate.AUDIENCE_VENDOR,
            "description": "Automated vendor check-in sent 30 days before event.",
            "subject_template": "Arrival Confirmation Needed for {{event_date}}",
            "body_html_template": (
                "<p>Hello {{vendor_name}},</p>"
                "<p>We are confirming arrival timing for the upcoming event on <strong>{{event_date}}</strong>.</p>"
                "<p>Current expected arrival time is <strong>{{arrival_time}}</strong>. Please reply to confirm or propose an adjustment.</p>"
                "<p>Thank you,<br>ELDA Wedding Sites Vendor Coordination</p>"
            ),
            "body_markdown_template": (
                "Hello {{vendor_name}},\n\n"
                "Please confirm arrival time for event date {{event_date}} (current arrival {{arrival_time}}).\n\n"
                "ELDA Wedding Sites Vendor Coordination"
            ),
            "is_system": True,
        },
        {
            "key": "change_of_venue",
            "name": "Change of Venue",
            "category": EmailTemplate.CATEGORY_ANNOUNCEMENT,
            "audience": EmailTemplate.AUDIENCE_CLIENT,
            "description": "Manual emergency venue update.",
            "subject_template": "Important Venue Update for {{wedding_date}}",
            "body_html_template": (
                "<p>Hello {{client_name}},</p>"
                "<p>We have an important venue update related to {{wedding_date}}.</p>"
                "<p>{{custom_message}}</p>"
                "<p>We will support every adjustment and keep your day seamless.</p>"
            ),
            "body_markdown_template": "Hello {{client_name}},\n\n{{custom_message}}",
            "is_system": False,
        },
        {
            "key": "weather_warning",
            "name": "Weather Warning",
            "category": EmailTemplate.CATEGORY_ANNOUNCEMENT,
            "audience": EmailTemplate.AUDIENCE_CLIENT,
            "description": "Manual weather communication template.",
            "subject_template": "Weather Advisory for {{wedding_date}}",
            "body_html_template": (
                "<p>Hello {{client_name}},</p>"
                "<p>We are monitoring weather and want to keep you informed.</p>"
                "<p>{{custom_message}}</p>"
                "<p>We have contingency plans ready and will guide you through every step.</p>"
            ),
            "body_markdown_template": "Hello {{client_name}},\n\n{{custom_message}}",
            "is_system": False,
        },
        {
            "key": "general_announcement",
            "name": "General Announcement",
            "category": EmailTemplate.CATEGORY_ANNOUNCEMENT,
            "audience": EmailTemplate.AUDIENCE_CLIENT,
            "description": "General update broadcast template.",
            "subject_template": "Update from ELDA Wedding Sites",
            "body_html_template": (
                "<p>Hello {{client_name}},</p>"
                "<p>{{custom_message}}</p>"
                "<p>Warmly,<br>ELDA Wedding Sites</p>"
            ),
            "body_markdown_template": "Hello {{client_name}},\n\n{{custom_message}}\n\nELDA Wedding Sites",
            "is_system": False,
        },
    ]

    created = 0
    for payload in defaults:
        existing = EmailTemplate.query.filter_by(key=payload["key"]).first()
        if existing:
            continue
        db.session.add(EmailTemplate(**payload, is_active=True))
        created += 1

    if created:
        db.session.commit()
    return created
