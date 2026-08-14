# Wedding Platform Architecture

## Canonical application

`leifheaney5/elda-wedding-sites` is the maintained application lineage. Production deployments select a site identity with `SITE_PROFILE` while keeping databases, secrets, domains, and client data isolated per Railway project.

## Production topology

### ELDA

Railway project: `elda-weddings-website`

- `web` — canonical application from `leifheaney5/elda-wedding-sites` `main`
- `Postgres` — ELDA-only production database
- profile: `SITE_PROFILE=elda`

### Barefoot Beach Brides (BBB)

Railway project: `bbb-wedding-website`

- `web` — legacy BBB compatibility/rollback service sourced from `leifheaney5/bbb-wedding-website` `master`
- `web-canonical` — canonical shared application sourced from `leifheaney5/elda-wedding-sites` `main`
- `bbb-assets` — BBB-owned production photo/logo origin sourced from the legacy BBB repository
- `Postgres` — BBB-only production database
- profile: `SITE_PROFILE=bbb`

`platform-staging` was used during consolidation validation. It is disposable, uses explicit SQLite staging mode, and is not part of the target production topology.

## Isolation contract

The following must never be shared between ELDA and BBB production deployments:

- `DATABASE_URL`
- `SECRET_KEY`
- SMTP/API credentials
- OAuth credentials
- Stripe credentials
- admin/client accounts
- contacts, bookings, payments, RSVP records, communications, vendors, and uploaded client data

A client deployment may share application code, migrations, templates, and non-secret profile defaults. It must not share customer data or production credentials.

## Asset strategy

BBB production photography remains outside the canonical repository. `web-canonical` uses `ASSET_BASE_URL` so requests for deployment-owned images can resolve through `bbb-assets` while shared CSS, JavaScript, templates, and application logic remain in the canonical codebase.

## Canonical host behavior

Production deployments use `SITE_URL` plus `ENFORCE_CANONICAL_HOST=True`. Requests received on a non-canonical host are redirected with HTTP 301 to the configured canonical host while preserving the path and query string.

## Security baseline

The shared application enables:

- CSRF protection
- secure and HTTP-only session cookies in production
- authentication rate limiting
- HSTS on HTTPS responses
- CSP, frame, referrer, permissions, MIME-sniffing, and XSS response headers
- production debug mode disabled

## Rollback principle

Application rollback must not require moving databases. Restore the previous application source/deployment while leaving the client-specific Postgres service in place. Database restore is required only when a forward schema migration is not backward compatible.
