# Production Validation

## Release gate

A release is complete only when infrastructure, application behavior, isolation, and rollback references are all verified.

## Infrastructure

- Confirm all intended Railway services report `SUCCESS`.
- Inspect startup/runtime logs for crashes, migration failures, or repeated restarts.
- Confirm the app listens on the Railway-provided port.
- Check HTTP logs for sustained 5xx responses.

## Public application

- Open the production homepage on desktop and mobile.
- Test primary navigation and representative content pages.
- Verify nested/deep links survive direct load and refresh.
- Verify images, logos, CSS, and JavaScript load successfully.
- Check browser console and network panels for errors.

## Authentication

- Verify `/client` and `/admin/login` load.
- Confirm protected routes redirect unauthenticated users appropriately.
- Confirm login rate limiting and CSRF protections remain active.

## Canonical host

- Record the full redirect chain from legacy/non-canonical hosts.
- Confirm HTTPS is preserved.
- Confirm the canonical host is the configured `SITE_URL`.
- Confirm path and query strings are preserved.
- Confirm no redirect loop occurs.

## Persistence and isolation

When the release changes persistence behavior, perform a controlled test record through the normal UI:

1. Create one identifiable test record.
2. Verify it is visible in the correct client/admin workflow.
3. Refresh and confirm persistence.
4. Confirm the other client deployment does not contain the record.
5. Remove the test record through normal application/admin behavior.
6. Inspect logs for database errors.

Never change production `DATABASE_URL` values merely to perform this test.

## BBB-specific checks

- `web-canonical` source is `leifheaney5/elda-wedding-sites` `main`.
- `SITE_PROFILE=bbb` is present.
- `ASSET_BASE_URL` is present and resolves to the BBB asset origin.
- `Postgres` remains the BBB project database.
- `bbb-assets` remains healthy while referenced.
- Legacy `web` behavior is intentionally documented.

## ELDA-specific checks

- `web` source is `leifheaney5/elda-wedding-sites` `main`.
- `SITE_PROFILE=elda` is present.
- ELDA references only its own `Postgres` service.

## Quality checks

Run or verify the project regression suite, including smoke and browser E2E coverage. Review accessibility, performance, SEO/social metadata, responsive behavior, and production security headers for meaningful releases.

## Sign-off record

Capture:

- validation date/time
- deployed commit(s)
- successful Railway deployment IDs
- service statuses
- redirect result
- database isolation result
- acceptance-test result
- automated QA result
- known non-blocking issues
- rollback commit/deployment references
