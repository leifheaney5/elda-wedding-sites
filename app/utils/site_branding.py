from __future__ import annotations

from typing import Any
from urllib.parse import quote

from flask import redirect
from jinja2 import BaseLoader, TemplateNotFound


def _brand_replacements(config: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    package_labels = [label for _, label in config.get("BRAND_PACKAGE_NAV", ())]
    venue_labels = [label for _, label in config.get("BRAND_VENUE_NAV", ())]

    replacements: list[tuple[str, str]] = [
        ("ELDA Wedding Sites logo", str(config.get("BRAND_LOGO_ALT", "ELDA Wedding Sites logo"))),
        ("images/logo/elda-logo-primary.svg", str(config.get("BRAND_LOGO_PATH", "images/logo/elda-logo-primary.svg"))),
        ("images/logo/elda-logo-light.svg", str(config.get("BRAND_LOGO_LIGHT_PATH", "images/logo/elda-logo-light.svg"))),
        ("ELDA Wedding Sites", str(config.get("BRAND_NAME", "ELDA Wedding Sites"))),
        ("Wedding Template", str(config.get("BRAND_TAGLINE", "Wedding Template"))),
        ("Your City, State", str(config.get("BRAND_LOCATION", "Your City, State"))),
        ("ELDA Florals", str(config.get("BRAND_FLORALS_LABEL", "ELDA Florals"))),
        ("info@eldaweddingsites.com", str(config.get("BRAND_CONTACT_EMAIL", "info@eldaweddingsites.com"))),
        ("Template wedding website with reusable package, venue, planning, and inquiry flows for customization.", str(config.get("BRAND_DESCRIPTION", ""))),
    ]

    address_lines = list(config.get("BRAND_ADDRESS_LINES", ()))
    if address_lines:
        replacements.append(("123 Example Avenue Suite 100", str(address_lines[0])))
    if len(address_lines) > 1:
        replacements.append(("Example City, ST 00000", str(address_lines[1])))

    for index, label in enumerate(package_labels[:8]):
        replacements.append((f"Ceremony Package {chr(ord('A') + index)}", str(label)))

    for index, label in enumerate(venue_labels[:3]):
        replacements.append((f"Venue Option {chr(ord('A') + index)}", str(label)))

    # Longer tokens first avoids partial replacement of more-specific values.
    return tuple(sorted(replacements, key=lambda item: len(item[0]), reverse=True))


def apply_brand_profile(source: str, config: dict[str, Any]) -> str:
    if config.get("SITE_PROFILE", "elda") == "elda":
        return source

    transformed = source
    for old, new in _brand_replacements(config):
        transformed = transformed.replace(old, new)
    return transformed


class BrandProfileLoader(BaseLoader):
    def __init__(self, delegate: BaseLoader, config: dict[str, Any]):
        self.delegate = delegate
        self.config = config

    def get_source(self, environment, template):  # type: ignore[override]
        if self.delegate is None:
            raise TemplateNotFound(template)
        source, filename, uptodate = self.delegate.get_source(environment, template)
        return apply_brand_profile(source, self.config), filename, uptodate

    def list_templates(self) -> list[str]:
        if self.delegate is None:
            return []
        return self.delegate.list_templates()


def install_brand_profile_loader(app) -> None:
    if app.extensions.get("brand_profile_loader"):
        return
    if app.jinja_loader is not None:
        app.jinja_loader = BrandProfileLoader(app.jinja_loader, app.config)
    app.extensions["brand_profile_loader"] = True


def install_deployment_asset_origin(app) -> None:
    """Redirect deployment-owned image requests to an optional external origin.

    Shared CSS and JavaScript continue to come from the canonical application.
    Only paths under ``/static/images/`` are redirected. This lets a client keep a
    private/production photo library in its own tiny asset service while the web app
    runs the shared canonical codebase.
    """

    if app.extensions.get("deployment_asset_origin"):
        return

    asset_base_url = str(app.config.get("ASSET_BASE_URL", "")).strip().rstrip("/")
    if not asset_base_url:
        app.extensions["deployment_asset_origin"] = False
        return

    original_static = app.view_functions.get("static")
    if original_static is None:
        app.extensions["deployment_asset_origin"] = False
        return

    def deployment_static(filename: str):
        if filename.startswith("images/"):
            safe_filename = quote(filename, safe="/-_.~")
            return redirect(f"{asset_base_url}/{safe_filename}", code=302)
        return original_static(filename=filename)

    app.view_functions["static"] = deployment_static
    app.extensions["deployment_asset_origin"] = True


def install_site_profile_runtime(app) -> None:
    install_brand_profile_loader(app)
    install_deployment_asset_origin(app)
