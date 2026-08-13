# Wedding Site Platform Consolidation

## Decision

`elda-wedding-sites` is the canonical reusable application/template lineage.
`bbb-wedding-website` remains an isolated Barefoot Beach Brides client deployment.

The goal is one maintained application codebase with one independently deployed
Railway web service and one independently owned Postgres database per client.
Customer databases are never merged into a shared multi-tenant database.

## Target topology

```text
GitHub
└── leifheaney5/elda-wedding-sites
    ├── shared Flask application
    ├── models + migrations
    ├── admin portal
    ├── client portal
    ├── reusable public-site templates
    ├── site_profiles.py
    └── deployment/runbooks

Railway
├── wedding-site-template (current project: elda-weddings-website)
│   ├── web
│   └── Postgres
│
└── client-bbb-wedding (current project: bbb-wedding-website)
    ├── web
    └── Postgres
```

The Railway project names above are descriptive targets only. Renaming them does
not change services, domains, data, or deployment history and currently must be
done in the Railway dashboard.

## Deployment profile contract

Every deployment selects a public site identity with:

```env
SITE_PROFILE=elda
```

or:

```env
SITE_PROFILE=bbb
```

Profiles contain only non-secret defaults such as public brand names, labels,
logos, contact display data, and navigation names. They never contain customer
records or credentials.

Scalar values can be overridden per deployment without forking code:

```env
BRAND_NAME=Example Weddings
BRAND_TAGLINE=Coastal weddings made simple
BRAND_LOCATION=Ocean City, Maryland
BRAND_LOGO_PATH=images/logo/example-logo.png
BRAND_LOGO_LIGHT_PATH=images/logo/example-logo-light.png
BRAND_CONTACT_EMAIL=hello@example.com
BRAND_PHONE_DISPLAY=(555) 555-0100
BRAND_PHONE_URI=+15555550100
SITE_URL=https://weddings.example.com
```

## Isolation requirements

The following are always deployment-specific Railway variables or resources:

- `DATABASE_URL`
- `SECRET_KEY`
- SMTP credentials
- Google OAuth credentials
- Stripe credentials and webhook secrets
- client domains
- admin/client user records
- contacts, bookings, payments, service requests, communications, vendors, and files

A new client deployment receives a new Postgres service. Never point two client
web services at the same production `DATABASE_URL`.

## Barefoot Beach Brides migration sequence

1. Keep the existing BBB Railway project and database intact as the rollback source.
2. Finish the reusable profile seam on `platform-consolidation`.
3. Validate the shared application against a disposable/staging database.
4. Compare the canonical schema/Alembic head with BBB before changing source code.
5. Point a staging BBB web service at the canonical repository/branch and set
   `SITE_PROFILE=bbb` plus BBB's existing deployment-specific secrets.
6. Run migrations only against the staging/target BBB database.
7. Smoke-test public pages, booking/contact intake, client login, admin login,
   payment paths, email generation, and file/attachment handling.
8. Switch the existing BBB web service source only after the staging checks pass.
9. Do not move or merge the BBB Postgres data during the source-code cutover unless
   a schema migration explicitly requires it.
10. Keep the old BBB repository branch and last successful Railway deployment as
    rollback references until the new deployment has been stable through a full
    operational cycle.

## Rollback

Rollback is intentionally simple because data remains isolated and in place:

1. Restore the prior BBB web source/ref or Railway deployment.
2. Keep the same BBB `DATABASE_URL`.
3. If a forward migration is not backward compatible, restore the pre-migration
   database backup before restoring the old application version.
4. Confirm public, admin, and client portal health before declaring rollback done.

## Branch policy

- `main` on `elda-wedding-sites`: current canonical production/template line.
- `platform-consolidation`: isolated consolidation work until validation passes.
- `master` on `bbb-wedding-website`: existing client production line until cutover.
- `platform-consolidation` on BBB: isolated client-migration preparation/rollback work.

No consolidation work should be force-pushed over production history.

## Current blocker

GitHub Actions validation is currently unavailable because the account Actions
billing/spending limit is blocking workflow jobs. Do not merge the consolidation
branch solely on the basis of an unexecuted workflow. Use local/staging validation
and re-run CI after Actions is restored.
