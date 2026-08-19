from __future__ import annotations

import os
import sys


def _database_url_present() -> bool:
    return bool(
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("POSTGRESQL_URL")
    )


def _sqlite_staging_allowed() -> bool:
    # Explicit opt-in for disposable, non-production parity environments only.
    # Production/client deployments should never enable this flag.
    return os.getenv("ALLOW_SQLITE_STAGING", "False").strip().lower() == "true"


def main() -> int:
    if not _database_url_present() and not _sqlite_staging_allowed():
        print(
            "ERROR: DATABASE_URL is missing. Attach Railway Postgres or set DATABASE_URL before deploy.",
            file=sys.stderr,
        )
        return 1

    if not _database_url_present():
        print(
            "WARNING: ALLOW_SQLITE_STAGING is enabled; using the app's disposable SQLite fallback.",
            file=sys.stderr,
        )

    port = os.getenv("PORT", "8080")
    gunicorn_argv = [
        sys.executable,
        "-m",
        "gunicorn",
        "--bind",
        f"0.0.0.0:{port}",
        "--workers",
        "1",
        "--threads",
        "4",
        "run:app",
    ]
    os.execvp(sys.executable, gunicorn_argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
