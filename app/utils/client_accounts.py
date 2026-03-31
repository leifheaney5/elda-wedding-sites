from app import db
from app.models.client_user import ClientUser


def get_or_create_client_by_email(email: str, full_name: str | None = None) -> ClientUser | None:
    if not email:
        return None

    normalized = email.strip().lower()
    if not normalized:
        return None

    client = ClientUser.query.filter_by(email=normalized).first()
    if client:
        if full_name and not client.full_name:
            client.full_name = full_name.strip()
            db.session.flush()
        return client

    client = ClientUser(
        email=normalized,
        full_name=(full_name or "").strip() or None,
        auth_provider="email",
    )
    db.session.add(client)
    db.session.flush()
    return client
