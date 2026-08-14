# BBB Production Runbook

Railway project: `bbb-wedding-website`

## Services

- `web` — legacy compatibility/rollback service
- `web-canonical` — canonical application from `leifheaney5/elda-wedding-sites` `main`
- `bbb-assets` — BBB photo/logo origin
- `Postgres` — BBB production database

## Required invariants

- `web-canonical` uses `SITE_PROFILE=bbb`.
- `DATABASE_URL` belongs to BBB `Postgres` only.
- `ASSET_BASE_URL` points to the BBB asset origin.
- BBB and ELDA never share a production database or secrets.
- Do not remove `bbb-assets` while the canonical deployment depends on it.

## Release check

1. Verify `web-canonical`, `bbb-assets`, and `Postgres` are healthy.
2. Verify the legacy `web` service behaves as intentionally configured.
3. Inspect runtime and HTTP logs for crashes, migration failures, 5xx responses, or redirect loops.
4. Test public, client, and admin entry points.
5. Validate BBB-specific metadata, imagery, and canonical URLs.
6. Perform a controlled database write/read test when persistence behavior changes.

## Rollback

Keep the BBB database in place. Restore the prior successful application deployment/source and verify public/admin/client health. Restore a database backup only if a migration prevents the previous application version from operating safely.
