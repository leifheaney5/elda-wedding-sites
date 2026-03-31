from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time

from app.models.booking import BookingRequest
from app.models.contact import ContactSubmission
from app.models.payment import Payment
from app.models.service_request import ServiceRequest


@dataclass(frozen=True)
class DatasetConfig:
    model: type
    date_field: str
    default_fields: list[str]
    available_fields: dict[str, str]
    statuses: list[str]


DATASET_CONFIG: dict[str, DatasetConfig] = {
    "contacts": DatasetConfig(
        model=ContactSubmission,
        date_field="submitted_at",
        default_fields=["submitted_at", "name", "email", "services_interested", "is_read"],
        available_fields={
            "id": "ID",
            "submitted_at": "Submitted At",
            "name": "Name",
            "email": "Email",
            "phone": "Phone",
            "subject": "Subject",
            "services_interested": "Services Interested",
            "is_read": "Read",
        },
        statuses=[],
    ),
    "bookings": DatasetConfig(
        model=BookingRequest,
        date_field="submitted_at",
        default_fields=["submitted_at", "couple_name", "email", "package_id", "status"],
        available_fields={
            "id": "ID",
            "submitted_at": "Submitted At",
            "couple_name": "Couple",
            "email": "Email",
            "wedding_date": "Wedding Date",
            "package_id": "Package",
            "guest_count": "Guest Count",
            "status": "Status",
        },
        statuses=[
            "all",
            BookingRequest.STATUS_NEW,
            BookingRequest.STATUS_REVIEWING,
            BookingRequest.STATUS_CONFIRMED,
            BookingRequest.STATUS_CANCELLED,
        ],
    ),
    "service_requests": DatasetConfig(
        model=ServiceRequest,
        date_field="submitted_at",
        default_fields=["submitted_at", "request_type", "name", "email", "status"],
        available_fields={
            "id": "ID",
            "submitted_at": "Submitted At",
            "request_type": "Type",
            "name": "Name",
            "email": "Email",
            "selected_service": "Selected Service",
            "event_date": "Event Date",
            "guest_count": "Guest Count",
            "status": "Status",
        },
        statuses=[
            "all",
            ServiceRequest.STATUS_NEW,
            ServiceRequest.STATUS_REVIEWING,
            ServiceRequest.STATUS_CONTACTED,
            ServiceRequest.STATUS_CLOSED,
        ],
    ),
    "payments": DatasetConfig(
        model=Payment,
        date_field="created_at",
        default_fields=["created_at", "booking_id", "amount_cents", "currency", "status"],
        available_fields={
            "id": "ID",
            "created_at": "Created At",
            "booking_id": "Booking ID",
            "amount_cents": "Amount Cents",
            "currency": "Currency",
            "status": "Status",
            "description": "Description",
            "paid_at": "Paid At",
        },
        statuses=[
            "all",
            Payment.STATUS_PENDING,
            Payment.STATUS_PAID,
            Payment.STATUS_FAILED,
            Payment.STATUS_REFUNDED,
        ],
    ),
}


def dataset_options() -> list[dict[str, str]]:
    return [
        {"value": key, "label": key.replace("_", " ").title()}
        for key in DATASET_CONFIG.keys()
    ]


def parse_fields(dataset: str, raw_fields: list[str] | str | None) -> list[str]:
    config = DATASET_CONFIG.get(dataset) or DATASET_CONFIG["contacts"]
    if raw_fields is None:
        return config.default_fields

    if isinstance(raw_fields, str):
        candidates = [part.strip() for part in raw_fields.split(",") if part.strip()]
    else:
        candidates = [part.strip() for part in raw_fields if part and part.strip()]

    selected = [field for field in candidates if field in config.available_fields]
    return selected or config.default_fields


def _format_cell(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return value if value is not None else ""


def build_report(
    *,
    dataset: str,
    fields: list[str],
    status_filter: str,
    date_start: date | None,
    date_end: date | None,
    viz_type: str,
    limit: int = 500,
) -> dict:
    config = DATASET_CONFIG.get(dataset) or DATASET_CONFIG["contacts"]
    selected_fields = parse_fields(dataset, fields)

    query = config.model.query
    date_column = getattr(config.model, config.date_field)

    if date_start:
        query = query.filter(date_column >= datetime.combine(date_start, time.min))
    if date_end:
        query = query.filter(date_column <= datetime.combine(date_end, time.max))

    if config.statuses and status_filter and status_filter != "all":
        query = query.filter(config.model.status == status_filter)

    rows_raw = query.order_by(date_column.desc()).limit(max(1, min(limit, 1000))).all()

    rows = []
    for row in rows_raw:
        rows.append({
            field: _format_cell(getattr(row, field, ""))
            for field in selected_fields
        })

    status_counts: dict[str, int] = defaultdict(int)
    if config.statuses and hasattr(config.model, "status"):
        for row in rows_raw:
            status_counts[getattr(row, "status", "unknown")] += 1

    daily_counts: dict[str, int] = defaultdict(int)
    for row in rows_raw:
        dt_value = getattr(row, config.date_field, None)
        if isinstance(dt_value, datetime):
            daily_counts[dt_value.strftime("%Y-%m-%d")] += 1

    if viz_type == "status_breakdown" and status_counts:
        viz_points = [{"label": key, "value": value} for key, value in status_counts.items()]
    else:
        viz_points = [{"label": key, "value": value} for key, value in sorted(daily_counts.items())]

    return {
        "dataset": dataset,
        "field_labels": {field: config.available_fields[field] for field in selected_fields},
        "selected_fields": selected_fields,
        "rows": rows,
        "row_count": len(rows),
        "status_counts": dict(status_counts),
        "viz_type": viz_type,
        "viz_points": viz_points,
        "status_options": config.statuses or ["all"],
        "selected_status_filter": status_filter if status_filter in (config.statuses or ["all"]) else "all",
        "date_start": date_start,
        "date_end": date_end,
    }
