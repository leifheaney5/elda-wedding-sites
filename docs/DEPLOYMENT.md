# Deployment Guide

## Shared code, isolated deployments

Deploy the shared application independently for each site. Every production web service must have its own client-specific Railway project/database relationship and an explicit `SITE_PROFILE`.

## Required production variables

At minimum, configure:

- `SITE_PROFILE=elda` or `SITE_PROFILE=bbb`
- `DATABASE_URL` referencing the deployment's own Postgres service
- `SECRET_KEY`
- `SITE_URL`
- `PREFERRED_URL_SCHEME=https`
- `ENFORCE_CANONICAL_HOST=True`
- `FLASK_ENV=production`

Client-specific mail, OAuth, Stripe, rate-limit, and contact variables remain deployment-local.

BBB additionally requires `ASSET_BASE_URL` while its production imagery is hosted by `bbb-assets`.

## ELDA production

Project: `elda-weddings-website`

1. Deploy `web` from `leifheaney5/elda-wedding-sites` `main`.
2. Use the deterministic Railway Docker build configured for the service.
3. Keep `SITE_PROFILE=elda`.
4. Reference only the ELDA project `Postgres` service.
5. Run Alembic migrations as part of the established Railway deployment path.
6. Verify the deployment reaches `SUCCESS` and Gunicorn listens on the Railway-assigned port.

## BBB production

Project: `bbb-wedding-website`

1. Keep `Postgres` isolated in the BBB project.
2. Keep `bbb-assets` available while BBB photography remains in the legacy repo.
3. Deploy `web-canonical` from `leifheaney5/elda-wedding-sites` `main`.
4. Set `SITE_PROFILE=bbb`.
5. Set `ASSET_BASE_URL` to the BBB asset origin.
6. Keep the legacy `web` service available as the compatibility/rollback layer until its public-domain role is intentionally retired.
7. Do not repoint BBB to another database during an application source change.

## Deployment validation

After every production deployment:

1. Check Railway deployment status.
2. Inspect build/runtime logs for migration failures, crashes, or repeated restarts.
3. Confirm Gunicorn startup.
4. Check HTTP logs for sustained 5xx responses or redirect loops.
5. Test public, client, and admin entry points externally.
6. Verify client-specific assets.
7. Perform a controlled write/read test when the release changes persistence behavior.

See `PRODUCTION_VALIDATION.md` for the full release checklist.

## Staging

`platform-staging` was created for the 2026 consolidation effort. It uses `ALLOW_SQLITE_STAGING=True` and is disposable. It is not a production database validation environment and must never be treated as a customer-data service.

## Rollback

1. Record the currently successful deployment/commit before a release.
2. Restore the previous application deployment/source if the new release fails.
3. Keep the deployment's existing Postgres service attached.
4. Restore a database backup only if the forward migration made the previous app version incompatible.
5. Re-run public/admin/client smoke checks.
