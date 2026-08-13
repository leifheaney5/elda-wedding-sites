import os
from dotenv import load_dotenv

from site_profiles import load_site_profile

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SITE_PROFILE_VALUES = load_site_profile()


def _get_database_url() -> str | None:
    # Railway-linked services should provide DATABASE_URL, but allow common fallbacks.
    return (
        os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
        or os.environ.get("POSTGRESQL_URL")
    )


def _normalize_database_url(value: str | None) -> str | None:
    if not value:
        return value
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql://", 1)
    return value


def _sqlalchemy_engine_options(database_url: str | None) -> dict:
    if not database_url:
        return {"pool_pre_ping": True}

    options: dict = {"pool_pre_ping": True}
    # Railway Postgres connections should use TLS.
    if database_url.startswith("postgresql://"):
        options["connect_args"] = {"sslmode": "require"}
    return options


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    WTF_CSRF_TIME_LIMIT = int(os.environ.get("WTF_CSRF_TIME_LIMIT", 3600))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "True") == "True"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = os.environ.get("REMEMBER_COOKIE_SAMESITE", "Lax")
    REMEMBER_COOKIE_SECURE = os.environ.get("REMEMBER_COOKIE_SECURE", "True") == "True"

    SECURITY_HSTS_SECONDS = int(os.environ.get("SECURITY_HSTS_SECONDS", 31536000))
    SECURITY_X_XSS_PROTECTION = os.environ.get(
        "SECURITY_X_XSS_PROTECTION", "1; mode=block"
    )
    SECURITY_CSP = os.environ.get(
        "SECURITY_CSP",
        (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://cdn.jsdelivr.net; "
            "connect-src 'self' https://accounts.google.com https://openidconnect.googleapis.com; "
            "frame-src 'self' https://www.google.com;"
        ),
    )
    PASSWORD_RESET_TOKEN_MAX_AGE = int(
        os.environ.get("PASSWORD_RESET_TOKEN_MAX_AGE", 3600)
    )

    # Deployment profile. These values contain public site identity only. Customer
    # data, database credentials, OAuth secrets, Stripe secrets, and SMTP passwords
    # remain per-deployment Railway variables.
    SITE_PROFILE = SITE_PROFILE_VALUES["key"]
    BRAND_NAME = SITE_PROFILE_VALUES["brand_name"]
    BRAND_TAGLINE = SITE_PROFILE_VALUES["brand_tagline"]
    BRAND_LOCATION = SITE_PROFILE_VALUES["brand_location"]
    BRAND_DESCRIPTION = SITE_PROFILE_VALUES["brand_description"]
    BRAND_LOGO_PATH = SITE_PROFILE_VALUES["logo_path"]
    BRAND_LOGO_LIGHT_PATH = SITE_PROFILE_VALUES["logo_light_path"]
    BRAND_LOGO_ALT = SITE_PROFILE_VALUES["logo_alt"]
    BRAND_FLORALS_LABEL = SITE_PROFILE_VALUES["florals_label"]
    BRAND_PHONE_DISPLAY = SITE_PROFILE_VALUES["phone_display"]
    BRAND_PHONE_URI = SITE_PROFILE_VALUES["phone_uri"]
    BRAND_CONTACT_EMAIL = SITE_PROFILE_VALUES["contact_email"]
    BRAND_ADDRESS_LINES = SITE_PROFILE_VALUES["address_lines"]
    BRAND_ADDRESS = SITE_PROFILE_VALUES["address"]
    BRAND_AREA_SERVED = SITE_PROFILE_VALUES["area_served"]
    BRAND_PACKAGE_NAV = SITE_PROFILE_VALUES["package_nav"]
    BRAND_VENUE_NAV = SITE_PROFILE_VALUES["venue_nav"]
    BRAND_SOCIAL = SITE_PROFILE_VALUES["social"]

    # Optional origin for deployment-owned images. When set, requests under
    # /static/images/* are redirected there while shared CSS/JS remain local.
    # This allows a client deployment to keep its production photo library outside
    # the canonical code repository without duplicating application logic.
    ASSET_BASE_URL = os.environ.get("ASSET_BASE_URL", "").strip().rstrip("/")

    # Mail
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_TIMEOUT = int(os.environ.get("MAIL_TIMEOUT", 8))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", SITE_PROFILE_VALUES["mail_default_sender"]
    )
    CONTACT_RECIPIENT = os.environ.get(
        "CONTACT_RECIPIENT", SITE_PROFILE_VALUES["contact_email"]
    )
    SITE_URL = os.environ.get("SITE_URL", SITE_PROFILE_VALUES["site_url"])
    PREFERRED_URL_SCHEME = os.environ.get("PREFERRED_URL_SCHEME", "https")
    ENFORCE_CANONICAL_HOST = os.environ.get("ENFORCE_CANONICAL_HOST", "True") == "True"
    CLIENT_SELF_REGISTRATION_ENABLED = (
        os.environ.get("CLIENT_SELF_REGISTRATION_ENABLED", "False") == "True"
    )
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    CLIENT_LOGIN_GET_LIMIT = os.environ.get("CLIENT_LOGIN_GET_LIMIT", "120 per hour")
    CLIENT_LOGIN_POST_LIMIT = os.environ.get("CLIENT_LOGIN_POST_LIMIT", "5 per 15 minutes")
    CLIENT_REGISTER_GET_LIMIT = os.environ.get("CLIENT_REGISTER_GET_LIMIT", "120 per hour")
    CLIENT_REGISTER_POST_LIMIT = os.environ.get("CLIENT_REGISTER_POST_LIMIT", "3 per hour")
    ADMIN_LOGIN_GET_LIMIT = os.environ.get("ADMIN_LOGIN_GET_LIMIT", "240 per hour")
    ADMIN_LOGIN_POST_LIMIT = os.environ.get("ADMIN_LOGIN_POST_LIMIT", "12 per 15 minutes")
    EMAIL_CAMPAIGN_BATCH_SIZE = int(os.environ.get("EMAIL_CAMPAIGN_BATCH_SIZE", 500))
    EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "smtp")
    EMAIL_PROVIDER_TIMEOUT_SECONDS = int(os.environ.get("EMAIL_PROVIDER_TIMEOUT_SECONDS", 15))
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
    POSTMARK_API_TOKEN = os.environ.get("POSTMARK_API_TOKEN", "")
    POSTMARK_MESSAGE_STREAM = os.environ.get("POSTMARK_MESSAGE_STREAM", "outbound")
    EMAIL_COMMUNICATION_UNDO_MINUTES = int(os.environ.get("EMAIL_COMMUNICATION_UNDO_MINUTES", 5))
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Stripe
    STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PLATFORM_FEE_BPS = int(os.environ.get("STRIPE_PLATFORM_FEE_BPS", 1000))
    STRIPE_CONNECT_REFRESH_URL = os.environ.get(
        "STRIPE_CONNECT_REFRESH_URL", "/admin/reports/weekly"
    )
    STRIPE_CONNECT_RETURN_URL = os.environ.get(
        "STRIPE_CONNECT_RETURN_URL", "/admin/reports/weekly"
    )


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    ENFORCE_CANONICAL_HOST = False
    CLIENT_SELF_REGISTRATION_ENABLED = True
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(
        _get_database_url() or f"sqlite:///{os.path.join(BASE_DIR, 'bbb_dev.db')}"
    )
    SQLALCHEMY_ENGINE_OPTIONS = _sqlalchemy_engine_options(SQLALCHEMY_DATABASE_URI)


class ProductionConfig(Config):
    DEBUG = False
    # Railway startup validates that a deployment has an explicit database URL.
    # The fallback remains useful for local production-mode smoke tests only.
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(
        _get_database_url() or f"sqlite:///{os.path.join(BASE_DIR, 'bbb_prod_fallback.db')}"
    )
    SQLALCHEMY_ENGINE_OPTIONS = _sqlalchemy_engine_options(SQLALCHEMY_DATABASE_URI)


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
