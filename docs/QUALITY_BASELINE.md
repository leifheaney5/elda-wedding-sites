# Production Quality Baseline

## Current verified evidence

- Legacy BBB release gate: 428/428 automated checks passing.
- BBB Railway core services were healthy at cutover.
- ELDA Railway `web` and `Postgres` were healthy at cutover.
- Shared application security configuration includes CSRF, secure cookies, auth rate limiting, CSP, HSTS, frame/referrer/permissions headers, and disabled production debug mode.

## Open verification items

- External browser acceptance against the deployed public hostname(s).
- Controlled production write/read/delete test for each deployment when persistence behavior changes.
- Lighthouse/Core Web Vitals baseline from a browser-capable external runner.
- Cross-browser/device acceptance where required.

These items should be recorded in `CUTOVER_SIGNOFF.md` when completed.
