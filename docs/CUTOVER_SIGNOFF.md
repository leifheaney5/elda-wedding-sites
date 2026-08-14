# 2026-08-14 Cutover Sign-Off

## Production state

### BBB

Railway project: `bbb-wedding-website`

- `web`: successful deployment
- `web-canonical`: successful deployment before documentation-only rebuilds; canonical source is `leifheaney5/elda-wedding-sites` `main`
- `bbb-assets`: successful deployment
- `Postgres`: successful deployment
- `platform-staging`: disposable consolidation service, sleeping, not part of target production topology

### ELDA

Railway project: `elda-weddings-website`

- `web`: successful deployment before documentation-only rebuilds
- `Postgres`: successful deployment

## Repository state

- PR #2 (platform consolidation): merged
- PR #3 (deterministic Railway production build): merged
- canonical branch: `main`
- operational architecture, deployment, validation, BBB, ELDA, and troubleshooting runbooks are documented under `docs/`

## Automated validation evidence

The legacy BBB release-gate artifacts report 428/428 QA checks passing, including browser E2E coverage. The shared platform also contains profile/application contract coverage introduced during consolidation.

## Remaining external/manual evidence

The ChatGPT execution runtime could not resolve Railway-generated public hostnames through its external DNS path, so browser-level production acceptance and a controlled production write/read cycle were not performed from this runtime. These remain release-verification items, not infrastructure migration blockers.

## Rollback references

Preserve the pre-platform archive branch and prior successful Railway deployment references until the final external acceptance test and controlled persistence check are completed.

## Cleanup status

- `platform-staging` is sleeping and can be deleted after final external acceptance.
- obsolete merged-work branches may be deleted after their production references are no longer needed.
- canonical Railway services now use watch patterns that exclude docs-only changes from future automatic production deploys.
