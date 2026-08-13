from __future__ import annotations

import argparse
from pathlib import Path

from site_profiles import available_profiles, load_site_profile


ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "app" / "static"


def validate(profile_key: str) -> list[str]:
    profile = load_site_profile(profile_key)
    errors: list[str] = []

    required_text = (
        "brand_name",
        "brand_tagline",
        "logo_path",
        "logo_light_path",
        "contact_email",
        "site_url",
    )
    for key in required_text:
        if not str(profile.get(key, "")).strip():
            errors.append(f"{profile_key}: missing required value {key}")

    for key in ("logo_path", "logo_light_path"):
        relative = str(profile.get(key, "")).strip()
        if relative and not (STATIC_ROOT / relative).is_file():
            errors.append(f"{profile_key}: {key} does not exist: app/static/{relative}")

    if not profile.get("package_nav"):
        errors.append(f"{profile_key}: package_nav is empty")
    if not profile.get("venue_nav"):
        errors.append(f"{profile_key}: venue_nav is empty")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate wedding-site deployment profiles")
    parser.add_argument(
        "profiles",
        nargs="*",
        default=list(available_profiles()),
        help="Profile keys to validate; defaults to every built-in profile",
    )
    args = parser.parse_args()

    all_errors: list[str] = []
    for profile_key in args.profiles:
        try:
            all_errors.extend(validate(profile_key))
        except Exception as exc:
            all_errors.append(f"{profile_key}: {exc}")

    if all_errors:
        for error in all_errors:
            print(f"ERROR: {error}")
        return 1

    print("Validated site profiles: " + ", ".join(args.profiles))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
