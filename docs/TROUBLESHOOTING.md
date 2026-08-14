# Production Troubleshooting

## Deployment fails before app startup

- Inspect Railway build logs.
- Confirm the service is using the intended deterministic build path.
- Verify dependency lock/build files are present.
- Do not change database or secret variables to work around a build failure.

## Migration failure

- Stop treating the deployment as healthy even if the container starts.
- Verify `DATABASE_URL` belongs to the intended deployment.
- Compare the database migration head with the application migration set.
- Prefer forward-fixing a safe migration; use rollback plus database restore only when compatibility requires it.

## Redirect loop

- Compare the incoming host with `SITE_URL`.
- Verify `ENFORCE_CANONICAL_HOST` and Railway/public-domain configuration agree.
- Check proxy `X-Forwarded-Proto` and host behavior.

## Missing BBB images

- Confirm `bbb-assets` is healthy.
- Confirm `ASSET_BASE_URL` is configured on `web-canonical`.
- Check that the requested image exists in the BBB asset service at the expected static path.
- Do not copy production photography into the shared repository merely to mask an origin/config problem.

## Unexpected ELDA/BBB branding

- Confirm `SITE_PROFILE` on the affected service.
- Confirm deployment-specific brand overrides are intentional.
- Inspect shared templates for hard-coded client identity; shared templates should derive identity from the active profile.

## Database isolation concern

- Do not alter URLs while investigating.
- Inspect Railway service relationships and variable references without exposing secret values.
- Verify each application points only to the Postgres service in its own Railway project.

## Staging

`platform-staging` is disposable and may use SQLite only when `ALLOW_SQLITE_STAGING=True`. Never use it as evidence that a production Postgres migration succeeded.
