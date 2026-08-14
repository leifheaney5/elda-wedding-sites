# 2026-08-14 Cutover Sign-Off

## Production state

### BBB

Railway project: `bbb-wedding-website`

- `web`: healthy legacy compatibility/rollback service
- `web-canonical`: `SUCCESS`, deployment `d57da856-711b-4141-92ad-0b22477b1c06`
- `bbb-assets`: healthy BBB production photo/logo origin
- `Postgres`: healthy BBB production database
- `platform-staging`: disposable consolidation service, sleeping, not part of target production topology
- canonical application source: `leifheaney5/elda-wedding-sites` `main`

### ELDA

Railway project: `elda-weddings-website`

- `web`: `SUCCESS`, deployment `688c31f8-aa9c-4e2e-b89c-79bc6134c82c`
- `Postgres`: healthy ELDA production database
- canonical application source: `leifheaney5/elda-wedding-sites` `main`

Both successful application deployments ran Alembic against PostgreSQL and started Gunicorn on port 8080 without startup failure.

## Repository state

- PR #2 (platform consolidation): merged
- PR #3 (deterministic Railway production build): merged
- PR #4 (profile-aware production SEO metadata): merged
- canonical branch: `main`
- operational architecture, deployment, validation, BBB, ELDA, quality, and troubleshooting runbooks are documented under `docs/`

## Product/SEO hardening completed

The post-cutover audit found that the shared base template still hard-coded ELDA identity into title, author, Open Graph/Twitter metadata, social image selection, and LocalBusiness structured data. PR #4 changed those fields to derive from the active deployment profile and added BBB metadata regression coverage.

Platform CI for PR #4 passed:

- site-profile validation
- full automated test suite
- ELDA profile smoke boot/render
- BBB profile smoke boot/render

## Existing automated validation evidence

The legacy BBB release-gate artifacts report 428/428 QA checks passing, including browser E2E coverage. The shared platform additionally validates both built-in site profiles and the shared application contract.

## Production deployment hygiene

Canonical ELDA and BBB Railway services now use application/build watch patterns. Documentation-only commits are correctly recorded as `SKIPPED`, while application changes still trigger production builds.

## Remaining external evidence

The ChatGPT execution runtime cannot resolve the Railway-generated public hostnames through its external DNS path. Therefore these two release-verification items could not be executed from this runtime:

1. browser-level public production acceptance/redirect-chain validation;
2. a controlled production write/read/delete cycle through the live application UI.

These are explicitly tracked as external acceptance evidence and are not infrastructure migration failures.

## Rollback references

Preserve the pre-platform archive branch and prior successful Railway deployment references until the final external acceptance test and controlled persistence check are completed.

## Cleanup status

- `platform-staging` is sleeping and may be deleted after final external acceptance.
- obsolete merged-work branches may be deleted after rollback retention is no longer required.
- `web`, `web-canonical`, `bbb-assets`, and BBB `Postgres` remain intentionally preserved.
- ELDA `web` and ELDA `Postgres` remain intentionally preserved.
