"""Deployment-specific branding and navigation profiles.

The application code is shared by every deployment. A deployment selects a profile
with SITE_PROFILE and may override any scalar branding/contact value with
environment variables. Databases, secrets, domains, and customer data are never
stored in these profiles.
"""

from __future__ import annotations

from copy import deepcopy
import os
from typing import Any


ELDA_PROFILE: dict[str, Any] = {
    "key": "elda",
    "brand_name": "ELDA Wedding Sites",
    "brand_tagline": "Wedding Template",
    "brand_location": "Your City, State",
    "brand_description": (
        "Template wedding website with reusable package, venue, planning, and "
        "inquiry flows for customization."
    ),
    "logo_path": "images/logo/elda-logo-primary.svg",
    "logo_light_path": "images/logo/elda-logo-light.svg",
    "logo_alt": "ELDA Wedding Sites logo",
    "florals_label": "ELDA Florals",
    "phone_display": "(443) 614-4783",
    "phone_uri": "+14436144783",
    "contact_email": "info@eldaweddingsites.com",
    "mail_default_sender": "info@eldaweddingsites.example",
    "site_url": "https://eldaweddingsites.example",
    "address_lines": [
        "123 Example Avenue Suite 100",
        "Example City, ST 00000",
    ],
    "address": {
        "street": "123 Example Avenue Suite 100",
        "city": "Example City",
        "region": "ST",
        "postal_code": "00000",
        "country": "US",
    },
    "area_served": "Regional service area",
    "package_nav": [
        ("packages.elopement", "Ceremony Package A"),
        ("packages.circle_of_love", "Ceremony Package B"),
        ("packages.ocean_city", "Ceremony Package C"),
        ("packages.sail_away", "Ceremony Package D"),
        ("packages.seaside_serenity_basic", "Ceremony Package E"),
        ("packages.seaside_serenity_upgrade", "Ceremony Package F"),
        ("packages.all_inclusive", "Ceremony Package G"),
        ("packages.beach_wedding_reception", "Ceremony Package H"),
    ],
    "venue_nav": [
        ("venue.coastal_59", "Venue Option A"),
        ("venue.intimate_dinner", "Venue Option B"),
        ("venue.gazebo_weddings", "Venue Option C"),
        ("venue.gallery", "Venue Gallery"),
    ],
    "social": {
        "facebook": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "pinterest": "https://www.pinterest.com",
        "youtube": "https://www.youtube.com",
    },
}


BBB_PROFILE: dict[str, Any] = {
    "key": "bbb",
    "brand_name": "Barefoot Beach Brides",
    "brand_tagline": "Ocean City, Maryland",
    "brand_location": "Ocean City, Maryland",
    "brand_description": (
        "Beach weddings, ceremony packages, venue coordination, florals, catering, "
        "and planning support in Ocean City, Maryland."
    ),
    "logo_path": "images/logo/bbb-logo.png",
    "logo_light_path": "images/logo/bbb-logo-light.png",
    "logo_alt": "Barefoot Beach Brides logo",
    "florals_label": "Barefoot Florals",
    "phone_display": "(443) 614-4783",
    "phone_uri": "+14436144783",
    "contact_email": "admin@barefootbeachbridesoc.com",
    "mail_default_sender": "info@barefootbeachbrides.wedding",
    "site_url": "https://barefootbeachbrides.wedding",
    "address_lines": ["Ocean City, Maryland"],
    "address": {
        "street": "",
        "city": "Ocean City",
        "region": "MD",
        "postal_code": "",
        "country": "US",
    },
    "area_served": "Ocean City, Maryland and surrounding coastal communities",
    "package_nav": [
        ("packages.elopement", "Elopement Ceremony Package"),
        ("packages.circle_of_love", "Circle of Love Package"),
        ("packages.ocean_city", "Ocean City Beach Package"),
        ("packages.sail_away", "Sail Away & Say I Do"),
        ("packages.seaside_serenity_basic", "Seaside Serenity (Basic)"),
        ("packages.seaside_serenity_upgrade", "Seaside Serenity (Upgrade)"),
        ("packages.all_inclusive", "All-Inclusive Wedding Package"),
        ("packages.beach_wedding_reception", "Beach Wedding and Reception"),
    ],
    "venue_nav": [
        ("venue.coastal_59", "Coastal 59 Venue"),
        ("venue.intimate_dinner", "2-Hour Intimate Dinner Package"),
        ("venue.gazebo_weddings", "Gazebo Wedding Package"),
        ("venue.gallery", "Coastal 59 Venue Gallery"),
    ],
    "social": {
        "facebook": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "pinterest": "https://www.pinterest.com",
        "youtube": "https://www.youtube.com",
    },
}


PROFILES: dict[str, dict[str, Any]] = {
    "elda": ELDA_PROFILE,
    "bbb": BBB_PROFILE,
}


_SCALAR_ENV_OVERRIDES = {
    "BRAND_NAME": "brand_name",
    "BRAND_TAGLINE": "brand_tagline",
    "BRAND_LOCATION": "brand_location",
    "BRAND_DESCRIPTION": "brand_description",
    "BRAND_LOGO_PATH": "logo_path",
    "BRAND_LOGO_LIGHT_PATH": "logo_light_path",
    "BRAND_LOGO_ALT": "logo_alt",
    "BRAND_FLORALS_LABEL": "florals_label",
    "BRAND_PHONE_DISPLAY": "phone_display",
    "BRAND_PHONE_URI": "phone_uri",
    "BRAND_CONTACT_EMAIL": "contact_email",
    "MAIL_DEFAULT_SENDER": "mail_default_sender",
    "SITE_URL": "site_url",
    "BRAND_AREA_SERVED": "area_served",
}


def available_profiles() -> tuple[str, ...]:
    return tuple(sorted(PROFILES))


def load_site_profile(profile_key: str | None = None) -> dict[str, Any]:
    """Return one deployment profile with safe environment overrides applied."""

    key = (profile_key or os.environ.get("SITE_PROFILE", "elda")).strip().lower()
    if key not in PROFILES:
        allowed = ", ".join(available_profiles())
        raise RuntimeError(f"Unknown SITE_PROFILE={key!r}. Expected one of: {allowed}")

    profile = deepcopy(PROFILES[key])
    for env_name, profile_name in _SCALAR_ENV_OVERRIDES.items():
        value = os.environ.get(env_name)
        if value is not None and value.strip():
            profile[profile_name] = value.strip()

    return profile
