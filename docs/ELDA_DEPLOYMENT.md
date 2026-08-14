# ELDA Production Runbook

Railway project: `elda-weddings-website`

## Services

- `web` — canonical application from `leifheaney5/elda-wedding-sites` `main`
- `Postgres` — ELDA production database

## Required invariants

- `SITE_PROFILE=elda`.
- `DATABASE_URL` belongs to ELDA `Postgres` only.
- ELDA never references BBB production data or secrets.
- Production uses the deterministic Railway Docker build path.

## Release check

1. Verify `web` and `Postgres` report successful deployment status.
2. Inspect migration and Gunicorn startup logs.
3. Test the public site plus client/admin entry points.
4. Verify canonical URLs and ELDA-specific metadata.
5. Check for sustained 5xx responses.
6. Perform controlled persistence validation when a release changes database behavior.

## Rollback

Restore the prior successful ELDA application deployment/source while leaving ELDA `Postgres` in place. Restore a database backup only when required by an incompatible forward migration.
