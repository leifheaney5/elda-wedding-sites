import pytest

from app import create_app
from config import config_map


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    test_app = create_app("development")
    test_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return test_app


@pytest.fixture
def production_app(monkeypatch):
    monkeypatch.setattr(config_map["production"], "SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    test_app = create_app("production")
    test_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return test_app


def test_home_route_ok(app):
    response = app.test_client().get("/")
    assert response.status_code == 200


def test_security_headers_present(app):
    response = app.test_client().get("/")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Content-Security-Policy")


def test_production_falls_back_when_database_url_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    monkeypatch.delenv("POSTGRESQL_URL", raising=False)
    application = create_app("production")
    assert application.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///")


@pytest.mark.parametrize(
    "path, expected_login_path",
    [
        ("/client/dashboard", "/client/login"),
        ("/admin/how-do-i", "/admin/login"),
        ("/admin/reports/weekly", "/admin/login"),
        ("/admin/reports/weekly/export", "/admin/login"),
        ("/admin/reports/weekly/export.csv", "/admin/login"),
        ("/admin/reports/studio", "/admin/login"),
        ("/admin/reports/studio/export", "/admin/login"),
        ("/admin/reports/studio/export.csv", "/admin/login"),
        ("/admin/vendors", "/admin/login"),
        ("/admin/vendors/1", "/admin/login"),
        ("/api/vendors/1/stripe/connect-status", "/admin/login"),
        ("/api/vendors/1/availability/rules", "/admin/login"),
        ("/api/vendors/1/calendar/connections", "/admin/login"),
        ("/api/vendors/1/availability/slots", "/admin/login"),
        ("/api/vendors/1/finance/summary", "/admin/login"),
        ("/api/vendors/1/finance/reconciliation", "/admin/login"),
        ("/api/vendors/1/finance/reconciliation.csv", "/admin/login"),
        ("/api/vendors/1/ops/scorecard", "/admin/login"),
        ("/api/vendors/1/ops/tasks", "/admin/login"),
    ],
)
def test_protected_get_routes_redirect_unauthenticated(app, path, expected_login_path):
    response = app.test_client().get(path, follow_redirects=False)
    assert response.status_code == 302
    assert expected_login_path in response.headers["Location"]


def test_vendor_api_post_requires_auth(app):
    response = app.test_client().post(
        "/api/vendors",
        json={"business_name": "Demo", "slug": "demo"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_vendor_ops_mutation_requires_auth(app):
    response = app.test_client().post(
        "/api/vendors/1/ops/expire-overdue-quotes",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_vendor_webhook_requires_valid_signature_when_configured(app, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    response = app.test_client().post("/api/webhooks/stripe/connect", data=b"{}")
    assert response.status_code in (400, 503)


def test_registration_disabled_in_production(production_app):
    response = production_app.test_client().get("/client/register", follow_redirects=False)
    assert response.status_code == 403


def test_robots_does_not_advertise_admin_path(app):
    response = app.test_client().get("/robots.txt")
    body = response.get_data(as_text=True)
    assert "Disallow: /admin/" not in body
    assert "Disallow: /client/" in body


def test_sitemap_uses_configured_site_url(production_app):
    response = production_app.test_client().get("/sitemap.xml")
    body = response.get_data(as_text=True)
    assert production_app.config["SITE_URL"].rstrip("/") + "/" in body
