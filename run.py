import os
from app import create_app
from app.utils.site_branding import install_brand_profile_loader


def _resolve_env() -> str:
    configured = os.environ.get("FLASK_ENV")
    if configured:
        return configured
    # In hosted environments (Railway), a DATABASE_URL means we should run production config.
    if os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or os.environ.get("POSTGRESQL_URL"):
        return "production"
    return "development"


app = create_app(_resolve_env())
install_brand_profile_loader(app)

if __name__ == "__main__":
    app.run(
        debug=_resolve_env() == "development",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
    )
