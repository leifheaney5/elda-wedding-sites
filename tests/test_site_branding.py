from app.utils.site_branding import apply_brand_profile
from site_profiles import load_site_profile


def _config_for(profile_key: str) -> dict:
    profile = load_site_profile(profile_key)
    return {
        "SITE_PROFILE": profile["key"],
        "BRAND_NAME": profile["brand_name"],
        "BRAND_TAGLINE": profile["brand_tagline"],
        "BRAND_LOCATION": profile["brand_location"],
        "BRAND_DESCRIPTION": profile["brand_description"],
        "BRAND_LOGO_PATH": profile["logo_path"],
        "BRAND_LOGO_LIGHT_PATH": profile["logo_light_path"],
        "BRAND_LOGO_ALT": profile["logo_alt"],
        "BRAND_FLORALS_LABEL": profile["florals_label"],
        "BRAND_CONTACT_EMAIL": profile["contact_email"],
        "BRAND_ADDRESS_LINES": profile["address_lines"],
        "BRAND_PACKAGE_NAV": profile["package_nav"],
        "BRAND_VENUE_NAV": profile["venue_nav"],
    }


def test_elda_profile_leaves_template_source_unchanged():
    source = "ELDA Wedding Sites | Wedding Template | Ceremony Package A"
    assert apply_brand_profile(source, _config_for("elda")) == source


def test_bbb_profile_rebrands_shared_template_source():
    source = (
        "ELDA Wedding Sites logo\n"
        "images/logo/elda-logo-primary.svg\n"
        "ELDA Wedding Sites\n"
        "Wedding Template\n"
        "ELDA Florals\n"
        "Ceremony Package A\n"
        "Venue Option A\n"
        "info@eldaweddingsites.com"
    )
    rendered = apply_brand_profile(source, _config_for("bbb"))

    assert "Barefoot Beach Brides logo" in rendered
    assert "images/logo/bbb-logo.png" in rendered
    assert "Barefoot Beach Brides" in rendered
    assert "Ocean City, Maryland" in rendered
    assert "Barefoot Florals" in rendered
    assert "Elopement Ceremony Package" in rendered
    assert "Coastal 59 Venue" in rendered
    assert "admin@barefootbeachbridesoc.com" in rendered
    assert "ELDA Wedding Sites" not in rendered


def test_bbb_profile_replaces_all_generic_package_labels():
    source = " | ".join(f"Ceremony Package {letter}" for letter in "ABCDEFGH")
    rendered = apply_brand_profile(source, _config_for("bbb"))
    for _, label in load_site_profile("bbb")["package_nav"]:
        assert label in rendered
