# Wedding Site Platform Consolidation

## Status

The 2026 ELDA/BBB platform consolidation is complete at the application/infrastructure level.

`leifheaney5/elda-wedding-sites` is the canonical shared application lineage. ELDA and Barefoot Beach Brides run isolated Railway deployments with separate production databases and secrets.

For current operations, use:

- `ARCHITECTURE.md`
- `DEPLOYMENT.md`
- `PRODUCTION_VALIDATION.md`
- `BBB_DEPLOYMENT.md`
- `ELDA_DEPLOYMENT.md`
- `TROUBLESHOOTING.md`
- `CUTOVER_SIGNOFF.md`

## Final topology

### ELDA

Railway project: `elda-weddings-website`

- `web` — shared application from `elda-wedding-sites` `main`
- `Postgres` — ELDA-only production database
- `SITE_PROFILE=elda`

### Barefoot Beach Brides

Railway project: `bbb-wedding-website`

- `web-canonical` — shared application from `elda-wedding-sites` `main`
- `bbb-assets` — BBB-owned production photo/logo origin
- `Postgres` — BBB-only production database
- legacy `web` — compatibility/rollback service from the legacy BBB repository
- `SITE_PROFILE=bbb`

`platform-staging` was a disposable consolidation-parity service. It uses explicit SQLite staging mode, is sleeping, and is not part of the target production topology.

## Isolation rule

Customer databases are never merged into a shared multi-tenant database. Each deployment owns its own `DATABASE_URL`, `SECRET_KEY`, credentials, customer records, and production integrations.

## Asset rule

BBB production photography can remain in the BBB-owned asset origin. `ASSET_BASE_URL` allows the canonical application to reference those images without re-forking application logic or copying private/client production assets into the shared repository.

## Migration history

- PR #2 introduced reusable `elda` and `bbb` deployment profiles, isolation rules, staging support, and application-contract coverage.
- PR #3 introduced the deterministic Railway Docker production build.
- BBB `web-canonical` was cut over to the shared `main` lineage while preserving BBB Postgres and the BBB asset origin.
- ELDA production remained on the shared canonical lineage with its own Postgres service.

## Rollback

Rollback remains client-local: restore the prior application deployment/source while keeping that client's Postgres service in place. Restore a database backup only if a forward migration is incompatible with the rollback application version.

## Branch policy

`main` is the canonical production line. Consolidation/hotfix branches are historical rollback references only and may be deleted once external acceptance and rollback-retention requirements are satisfied.

No migration history should be force-pushed over production history.
