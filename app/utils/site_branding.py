from __future__ import annotations

from typing import Any

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
