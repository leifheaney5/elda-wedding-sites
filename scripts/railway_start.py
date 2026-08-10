from __future__ import annotations

import os
import sys


def _database_url_present() -> bool:
    return bool(
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("POSTGRESQL_URL")
    )


def main() -> int:
    if not _database_url_present():
        print(
            "ERROR: DATABASE_URL is missing. Attach Railway Postgres or set DATABASE_URL before deploy.",
            file=sys.stderr,
        )
        return 1

    port = os.getenv("PORT", "8080")
    gunicorn_argv = [
        sys.executable,
        "-m",
        "gunicorn",
        "--bind",
        f"0.0.0.0:{port}",
        "run:app",
    ]
    os.execvp(sys.executable, gunicorn_argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
