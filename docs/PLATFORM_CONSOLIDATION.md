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
    ├── Postgres
    └── optional client-owned image asset service
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

## Client-owned image assets

The canonical repository intentionally does not need to absorb every client's
private or production photo library. A deployment can set:

```env
ASSET_BASE_URL=https://assets.example.com/static
```

When configured, requests under `/static/images/*` are redirected to that client
asset origin while shared CSS and JavaScript continue to come from the canonical
application. This keeps the application code consolidated without forcing client
photography into the core repository.

For Barefoot Beach Brides, this is the preferred cutover path because the current
BBB repository owns the real production logo and photography while the ELDA/template
repository contains placeholders in several equivalent image paths.

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
- client-owned image/photo libraries when `ASSET_BASE_URL` is used

A new client deployment receives a new Postgres service. Never point two client
web services at the same production `DATABASE_URL`.

## Barefoot Beach Brides migration sequence

1. Keep the existing BBB Railway project and database intact as the rollback source.
2. Finish the reusable profile seam on `platform-consolidation`.
3. Validate the shared application against a disposable/staging database or an
   explicitly disposable SQLite staging instance.
4. Compare the canonical schema/Alembic head with BBB before changing source code.
5. Point a staging BBB web service at the canonical repository/branch and set
   `SITE_PROFILE=bbb` without pointing it at the production BBB database.
6. Preserve BBB production photography through a client-owned asset origin before
   any production source cutover.
7. Run migrations only against the staging/target BBB database.
8. Smoke-test public pages, booking/contact intake, client login, admin login,
   payment paths, email generation, and file/attachment handling.
9. Switch the existing BBB web service source only after the staging checks pass.
10. Do not move or merge the BBB Postgres data during the source-code cutover unless
    a schema migration explicitly requires it.
11. Keep the old BBB repository branch and last successful Railway deployment as
    rollback references until the new deployment has been stable through a full
    operational cycle.

## Staging safety

The production Railway config runs Alembic as a pre-deploy command. Disposable
SQLite staging must override that pre-deploy command because the repository also
contains local fallback SQLite fixtures whose pre-existing tables are not a clean
migration target. The `ALLOW_SQLITE_STAGING=True` startup flag is therefore only
an explicit boot escape hatch for a disposable parity instance; it must never be
enabled on an actual client production deployment.

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

## Validation status

GitHub Actions is currently available and the platform CI is green. The suite
validates both built-in profiles, the shared application contract, and full-app
ELDA/BBB render smoke checks. A Railway BBB-profile staging service is also used as
an additional deployment-parity gate before the existing BBB production web source
is changed.
