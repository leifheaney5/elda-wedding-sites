from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from run import app


def main() -> int:
    profile = app.config["SITE_PROFILE"]
    brand_name = app.config["BRAND_NAME"]
    logo_path = app.config["BRAND_LOGO_PATH"]

    response = app.test_client().get("/")
    if response.status_code != 200:
        print(f"ERROR: homepage returned {response.status_code}")
        return 1

    page = response.get_data(as_text=True)
    if brand_name not in page:
        print(f"ERROR: homepage missing brand name {brand_name!r}")
        return 1
    if logo_path not in page:
        print(f"ERROR: homepage missing logo path {logo_path!r}")
        return 1
    if profile == "bbb" and "ELDA Wedding Sites" in page:
        print("ERROR: BBB homepage leaked ELDA brand identity")
        return 1

    print(f"Smoke check passed for SITE_PROFILE={profile}: {brand_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
