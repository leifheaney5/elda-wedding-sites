# ELDA Wedding Sites Wedding Website

Custom Flask application for the external website and internal owner/admin intranet for ELDA Wedding Sites in Your City, State.

## What is implemented

- Public-facing site pages:
  - Home
  - Ceremony Packages + expanded package detail pages
  - Venue pages + gallery
  - Florals
  - Catering
  - Contact form
  - Nearby Attractions (Google Maps-linked highlights)
  - Booking request form
  - Client portal entry point (`Client Login` in nav + homepage)
  - Separate activity request forms:
    - `/request/package`
    - `/request/venue`
    - `/request/catering`
    - `/request/florals`
  - About pages
  - Planning Guide page
  - Vow Renewals page
- Owner/admin intranet at `/admin`:
  - Secure login/logout
  - Dashboard with leads, bookings, and transaction metrics
  - Luxury Operations Command Center on dashboard with priority queue and concierge quick-action cards
  - Contact response management (read state + notes + selected service interests)
  - Booking management (status + notes)
  - Payments/transactions view with summary cards and status filter
  - Service request intake management for package/venue/catering/florals
  - Report Studio at `/admin/reports/studio` for dataset/field/filter-driven custom reports with saved templates and CSV/HTML exports
  - Admin Autopilot controls at `/admin/autopilot` for rule thresholds and autonomous stale-booking triage
  - Admin help center page at `/admin/how-do-i` with step-by-step operational guides
  - CSV exports:
    - `/admin/exports/contacts.csv`
    - `/admin/exports/bookings.csv`
    - `/admin/exports/payments.csv`
    - `/admin/exports/service_requests.csv`
  - Admin user management (owner-only)
- Client portal at `/client`:
  - Invite-only email/password login by default (`CLIENT_SELF_REGISTRATION_ENABLED=False`)
  - Google OAuth login (when credentials are configured)
  - Dashboard with plan selections, finance snapshot, and communication history
  - Wedding Inspo board (`/client/inspiration`) for colors/themes/florals/notes
  - Wedding Plan workspace (`/client/plan`) with milestones, required tasks, and custom tasks
  - Auto-linking of booking/contact/service requests by client email

## Architecture

- New layered architecture diagram source: `docs/architecture.mmd`
- Rendered image: `docs/architecture.png`
- Current modular boundaries:
  - `app/routes/*`: HTTP routing and view orchestration
  - `app/services/*`: shared business logic (attachment policy/handling, etc.)
  - `app/models/*`: persistence entities and relationships
  - `app/utils/*`: framework utilities (email, background jobs, helpers)

## Tech stack

- Python 3.11+
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-Login
- Flask-Mail
- PostgreSQL (production, Railway)
- SQLite (default local dev fallback)

## Local setup

```bash
uv sync --group dev
copy .env.example .env
```

Set at minimum:

- `SECRET_KEY`
- `FLASK_ENV=development`
- Optional OAuth:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
- Security defaults:
  - `CLIENT_SELF_REGISTRATION_ENABLED=False`
  - `ENFORCE_CANONICAL_HOST=True`
  - `RATELIMIT_STORAGE_URI=memory://` (or Redis in production)
  - Auth rate-limit tuning (optional):
    - `CLIENT_LOGIN_POST_LIMIT=5 per 15 minutes`
    - `ADMIN_LOGIN_POST_LIMIT=12 per 15 minutes`

Build local Tailwind CSS bundle (required after template/style changes):

```bash
npm install
npm run build:css
```

Optional for local PostgreSQL:

- `DATABASE_URL=postgresql://...`

Run migrations:

```bash
flask --app run.py db upgrade
```

Create owner/admin user:

```bash
flask --app run.py create-admin
```

Run app:

```bash
uv run python run.py
```

Run admin autopilot manually from CLI:

```bash
flask --app run.py run-admin-autopilot
```

Run automated tests (unit + Playwright e2e + QA runner):

```bash
uv run playwright install chromium
uv run pytest
uv run python tests/qa/run_full_qa.py
```

Run the production release gate (full regression + QA report checks):

```bash
python -m playwright install chromium
python tests/qa/run_release_gate.py
```

Fast deterministic 3-view smoke check (public + client + admin):

```bash
uv run pytest tests/smoke/test_three_views_smoke.py -q
```

QA artifacts are written to:

- `tests/reports/QA_TEST_REPORT.json`
- `tests/reports/QA_TEST_REPORT.md`
- `tests/reports/RELEASE_GATE_REPORT.json`
- `tests/reports/RELEASE_GATE_REPORT.md`

Release/rollback runbook:

- `docs/RELEASE_ROLLBACK_RUNBOOK.md`

## Railway deployment (PostgreSQL)

This repo is prepared for Railway with:

- `Procfile` (`web: gunicorn run:app`)
- `railway.json` (Nixpacks + start command)
- Production config that:
  - normalizes `postgres://` to `postgresql://`
  - enables TLS (`sslmode=require`) for PostgreSQL connections

### Steps

1. Create a new Railway project from this repo.
1. Add a PostgreSQL database service in Railway.
1. Attach DB variables to the web service (Railway usually injects `DATABASE_URL` automatically).
1. Set these environment variables in Railway:
   - `SECRET_KEY=<long-random-secret>`
   - `SITE_URL=https://eldaweddingsites.example`
   - `PREFERRED_URL_SCHEME=https`
   - `CONTACT_RECIPIENT=<owner inbox>`
   - Optional for Google autosign-in:
     - `GOOGLE_CLIENT_ID=<google oauth web app client id>`
     - `GOOGLE_CLIENT_SECRET=<google oauth web app client secret>`
   - Optional mail/Stripe keys as needed
1. Migrations are now run automatically at startup (`flask --app run.py db upgrade && gunicorn run:app`).
   - Optional manual fallback in Railway shell/CLI: `flask --app run.py db upgrade`
   - Deployment now fails fast with a clear error if `DATABASE_URL` is missing, to avoid SQLite fallback migration errors.

1. Create initial admin owner:
   - `flask --app run.py create-admin`

## Domain

- Primary domain: `https://eldaweddingsites.example`

Point DNS to Railway target and set domain in Railway project settings.

## Notes on media assets

Image and logo references are wired in templates. Place final files under:

- `app/static/images/logo/`
- `app/static/images/gallery/`
- other existing section folders in `app/static/images/`

## Content parity notes

- Original-site parity review: `docs/ORIGINAL_SITE_PARITY_REVIEW.md`

## Admin access

- URL: `/admin/login`
- Owner role has access to admin user management.
- Staff role has access to dashboard, contacts, bookings, and payments.
- Admin walkthrough guide: `docs/ADMIN_PORTAL_GUIDE.md`
- Portal testing checklist: `docs/PORTAL_TESTING.md`
