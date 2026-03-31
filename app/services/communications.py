from __future__ import annotations

import html
import re
from datetime import datetime, timedelta
from decimal import Decimal

import requests
from flask import current_app
from flask_mail import Message

from app import db, mail
from app.models.communication_log import CommunicationLog
from app.models.email_template import EmailTemplate

_PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_\.]+)\s*}}")


def _resolve_context_value(context: dict, key: str) -> str:
    value = context
    for part in key.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return ""

    if value is None:
        return ""
    if isinstance(value, (datetime,)):
        return value.strftime("%B %d, %Y %I:%M %p")
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    return str(value)


def render_template_string(template_text: str, context: dict) -> str:
    if not template_text:
        return ""

    def _replacement(match: re.Match) -> str:
        return _resolve_context_value(context, match.group(1))

    return _PLACEHOLDER_PATTERN.sub(_replacement, template_text)


def elegant_email_shell(*, title: str, body_html: str) -> str:
    escaped_title = html.escape(title or "ELDA Wedding Sites")
    return (
        "<html><head>"
        "<meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700&family=Inter:wght@400;500&display=swap' rel='stylesheet'>"
        "</head>"
        "<body style='margin:0;padding:0;background:#FAF6F1;color:#1A2E44;font-family:Inter,Arial,sans-serif;'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='padding:36px 12px;'>"
        "<tr><td align='center'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='max-width:640px;background:#ffffff;border:1px solid #F5EFE6;border-radius:16px;'>"
        "<tr><td style='padding:34px 38px 18px 38px;'>"
        "<p style='margin:0 0 8px 0;font-family:Playfair Display,Georgia,serif;font-size:30px;line-height:1.2;color:#1A2E44;'>ELDA Wedding Sites</p>"
        f"<p style='margin:0 0 24px 0;font-family:Playfair Display,Georgia,serif;font-size:22px;line-height:1.3;color:#1A2E44;'>{escaped_title}</p>"
        f"<div style='font-size:15px;line-height:1.75;color:#364152;'>{body_html}</div>"
        "<p style='margin:30px 0 0 0;padding-top:16px;border-top:1px solid #F5EFE6;font-size:12px;line-height:1.6;color:#6B7280;'>"
        "ELDA Wedding Sites<br>"
        "123 Example Avenue Suite 100, Example City, ST 00000"
        "</p>"
        "</td></tr></table>"
        "</td></tr></table>"
        "</body></html>"
    )


def _send_via_api(*, recipient_email: str, subject: str, html_body: str, text_body: str, sender_email: str) -> dict:
    provider = (current_app.config.get("EMAIL_PROVIDER") or "smtp").strip().lower()
    timeout_seconds = int(current_app.config.get("EMAIL_PROVIDER_TIMEOUT_SECONDS", 15))

    if provider == "resend":
        api_key = current_app.config.get("RESEND_API_KEY")
        if not api_key:
            return {"sent": False, "error": "RESEND_API_KEY missing", "provider": provider}
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "from": sender_email,
                "to": [recipient_email],
                "subject": subject,
                "html": html_body,
                "text": text_body,
            },
            timeout=timeout_seconds,
        )
        payload = response.json() if response.content else {}
        return {
            "sent": response.ok,
            "provider": provider,
            "provider_message_id": payload.get("id"),
            "error": None if response.ok else str(payload),
        }

    if provider == "sendgrid":
        api_key = current_app.config.get("SENDGRID_API_KEY")
        if not api_key:
            return {"sent": False, "error": "SENDGRID_API_KEY missing", "provider": provider}
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "from": {"email": sender_email},
                "personalizations": [{"to": [{"email": recipient_email}]}],
                "subject": subject,
                "content": [
                    {"type": "text/plain", "value": text_body},
                    {"type": "text/html", "value": html_body},
                ],
            },
            timeout=timeout_seconds,
        )
        return {
            "sent": response.status_code in {200, 202},
            "provider": provider,
            "provider_message_id": response.headers.get("X-Message-Id"),
            "error": None if response.status_code in {200, 202} else response.text,
        }

    if provider == "postmark":
        api_key = current_app.config.get("POSTMARK_API_TOKEN")
        if not api_key:
            return {"sent": False, "error": "POSTMARK_API_TOKEN missing", "provider": provider}
        response = requests.post(
            "https://api.postmarkapp.com/email",
            headers={
                "X-Postmark-Server-Token": api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "From": sender_email,
                "To": recipient_email,
                "Subject": subject,
                "HtmlBody": html_body,
                "TextBody": text_body,
                "MessageStream": current_app.config.get("POSTMARK_MESSAGE_STREAM", "outbound"),
            },
            timeout=timeout_seconds,
        )
        payload = response.json() if response.content else {}
        return {
            "sent": response.ok,
            "provider": provider,
            "provider_message_id": payload.get("MessageID"),
            "error": None if response.ok else str(payload),
        }

    try:
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            sender=sender_email,
            body=text_body,
            html=html_body,
        )
        mail.send(msg)
        return {"sent": True, "provider": "smtp", "provider_message_id": None, "error": None}
    except Exception as exc:  # pragma: no cover
        return {"sent": False, "provider": "smtp", "provider_message_id": None, "error": str(exc)}


def enqueue_template_email(
    *,
    template: EmailTemplate,
    recipient_email: str,
    context: dict,
    idempotency_key: str,
    scheduled_for: datetime | None = None,
    trigger_source: str,
    lifecycle_key: str | None = None,
    client_user_id: int | None = None,
    vendor_id: int | None = None,
    vendor_booking_id: int | None = None,
    booking_id: int | None = None,
    payment_id: int | None = None,
    created_by_admin_id: int | None = None,
    automation_rule_id: int | None = None,
    subject_template_override: str | None = None,
    body_html_template_override: str | None = None,
    body_markdown_template_override: str | None = None,
) -> CommunicationLog:
    subject_template = subject_template_override or template.subject_template
    body_markdown_template = (
        body_markdown_template_override
        if body_markdown_template_override is not None
        else template.body_markdown_template
    )
    body_html_template = body_html_template_override or template.body_html_template

    subject_rendered = render_template_string(subject_template, context)
    markdown_rendered = render_template_string(body_markdown_template or "", context)
    html_inner = render_template_string(body_html_template, context)
    html_rendered = elegant_email_shell(title=subject_rendered, body_html=html_inner)

    existing = CommunicationLog.query.filter_by(idempotency_key=idempotency_key).first()
    if existing:
        setattr(existing, "_was_existing", True)
        return existing

    log = CommunicationLog(
        template_id=template.id,
        automation_rule_id=automation_rule_id,
        client_user_id=client_user_id,
        vendor_id=vendor_id,
        vendor_booking_id=vendor_booking_id,
        booking_id=booking_id,
        payment_id=payment_id,
        trigger_source=trigger_source,
        lifecycle_key=lifecycle_key,
        idempotency_key=idempotency_key,
        recipient_email=recipient_email,
        recipient_name=context.get("client_name") or context.get("vendor_name"),
        sender_email=current_app.config.get("MAIL_DEFAULT_SENDER"),
        subject_rendered=subject_rendered,
        body_html_rendered=html_rendered,
        body_markdown_rendered=markdown_rendered,
        payload_json=context,
        scheduled_for=scheduled_for or datetime.utcnow(),
        created_by_admin_id=created_by_admin_id,
        status=CommunicationLog.STATUS_QUEUED,
    )
    db.session.add(log)
    db.session.flush()
    setattr(log, "_was_existing", False)
    return log


def dispatch_due_communications(*, now: datetime | None = None, limit: int = 200) -> dict:
    current_time = now or datetime.utcnow()
    due_items = (
        CommunicationLog.query.filter(
            CommunicationLog.status == CommunicationLog.STATUS_QUEUED,
            CommunicationLog.scheduled_for <= current_time,
        )
        .order_by(CommunicationLog.scheduled_for.asc(), CommunicationLog.id.asc())
        .limit(max(1, limit))
        .all()
    )

    sent = 0
    failed = 0
    for item in due_items:
        text_body = item.body_markdown_rendered or re.sub(r"<[^>]+>", " ", item.body_html_rendered)
        result = _send_via_api(
            recipient_email=item.recipient_email,
            subject=item.subject_rendered,
            html_body=item.body_html_rendered,
            text_body=text_body,
            sender_email=(
                item.sender_email
                or current_app.config.get("MAIL_DEFAULT_SENDER")
                or "info@eldaweddingsites.example"
            ),
        )
        item.provider_name = result.get("provider")
        item.provider_message_id = result.get("provider_message_id")
        item.provider_error = result.get("error")

        if result.get("sent"):
            item.status = CommunicationLog.STATUS_SENT
            item.sent_at = current_time
            sent += 1
        else:
            item.status = CommunicationLog.STATUS_FAILED
            failed += 1

    if due_items:
        db.session.commit()

    return {
        "queued_checked": len(due_items),
        "sent": sent,
        "failed": failed,
    }


def cancel_queued_communication(log: CommunicationLog) -> bool:
    if log.status != CommunicationLog.STATUS_QUEUED:
        return False
    log.status = CommunicationLog.STATUS_CANCELLED
    log.cancelled_at = datetime.utcnow()
    db.session.commit()
    return True


def default_manual_send_time() -> datetime:
    return datetime.utcnow() + timedelta(minutes=5)
