import importlib

import pytest

import site_profiles


def test_elda_profile_is_default(monkeypatch):
    monkeypatch.delenv("SITE_PROFILE", raising=False)
    profile = site_profiles.load_site_profile()
    assert profile["key"] == "elda"
    assert profile["brand_name"] == "ELDA Wedding Sites"
    assert profile["package_nav"]
    assert profile["venue_nav"]


def test_bbb_profile_preserves_client_identity(monkeypatch):
    monkeypatch.setenv("SITE_PROFILE", "bbb")
    profile = site_profiles.load_site_profile()
    assert profile["key"] == "bbb"
    assert profile["brand_name"] == "Barefoot Beach Brides"
    assert profile["brand_location"] == "Ocean City, Maryland"
    assert profile["logo_path"].endswith("bbb-logo.png")


def test_scalar_environment_overrides_are_applied(monkeypatch):
    monkeypatch.setenv("SITE_PROFILE", "elda")
    monkeypatch.setenv("BRAND_NAME", "Example Weddings")
    monkeypatch.setenv("SITE_URL", "https://example.test")
    profile = site_profiles.load_site_profile()
    assert profile["brand_name"] == "Example Weddings"
    assert profile["site_url"] == "https://example.test"


def test_nested_profile_values_are_copied(monkeypatch):
    monkeypatch.setenv("SITE_PROFILE", "bbb")
    first = site_profiles.load_site_profile()
    first["address"]["city"] = "Changed"
    second = site_profiles.load_site_profile()
    assert second["address"]["city"] == "Ocean City"


def test_unknown_profile_fails_fast(monkeypatch):
    monkeypatch.setenv("SITE_PROFILE", "does-not-exist")
    with pytest.raises(RuntimeError, match="Unknown SITE_PROFILE"):
        site_profiles.load_site_profile()
