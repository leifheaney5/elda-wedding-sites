import threading
from collections.abc import Callable
from flask import Flask


def run_in_background(app: Flask, job: Callable[[], None], label: str) -> None:
    """Run a small best-effort task without blocking request latency."""

    def wrapped():
        try:
            with app.app_context():
                job()
        except Exception:
            app.logger.exception("Background task failed: %s", label)

    threading.Thread(target=wrapped, daemon=True).start()
