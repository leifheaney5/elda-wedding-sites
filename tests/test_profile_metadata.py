import pytest

from app import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    application = create_app("development")
    application.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        BRAND_NAME="Barefoot Beach Brides",
        BRAND_TAGLINE="Ocean City, Maryland",
        BRAND_DESCRIPTION="Beach weddings in Ocean City, Maryland.",
        BRAND_LOGO_PATH="images/logo/bbb-logo.png",
        BRAND_PHONE_URI="+14436144783",
        BRAND_CONTACT_EMAIL="admin@barefootbeachbridesoc.com",
        BRAND_ADDRESS={
            "street": "",
            "city": "Ocean City",
            "region": "MD",
            "postal_code": "",
            "country": "US",
        },
        BRAND_AREA_SERVED="Ocean City, Maryland and surrounding coastal communities",
        SITE_URL="https://barefootbeachbrides.wedding",
    )
    return application


def test_home_metadata_uses_active_profile(app):
    response = app.test_client().get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Barefoot Beach Brides" in body
    assert 'meta property="og:site_name" content="Barefoot Beach Brides"' in body
    assert 'meta name="author" content="Barefoot Beach Brides"' in body
    assert "Beach weddings in Ocean City, Maryland." in body
    assert "https://barefootbeachbrides.wedding/" in body
    assert "images/logo/bbb-logo.png" in body
    assert '"addressLocality": "Ocean City"' in body
    assert '"addressRegion": "MD"' in body


def test_private_portal_metadata_is_noindex(app):
    response = app.test_client().get("/client/login")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'meta name="robots" content="noindex, nofollow"' in body
