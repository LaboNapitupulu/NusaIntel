# Phase 6 status — MVP hardening and release

- Status: In progress
- Date started: 2026-08-11
- Branch: `codex/phase-6-mvp-hardening`
- Baseline: Phase 5 merge commit `a0b2e07`

## First hardening tranche

- Added an 85% branch-coverage gate for five critical calculation modules; current local
  result is 88.83%.
- Added deterministic Playwright journeys on 1440 px and 360 px Chromium for regional
  report, map/table equivalence, source-aware detail navigation, and horizontal overflow.
- Added axe scanning and fixed the discovered WCAG AA contrast and scroll-region keyboard
  failures; serious/critical findings are now zero in the fixture journey.
- Added accessible global error/not-found routes and unique regional detail metadata.
- Extended CI to run the coverage gate, production build, browser installation, E2E, and
  accessibility checks.
- Added repeatable release verification and isolated backup/restore smoke scripts.
- Added architecture, physical data dictionary, runbook, privacy/security, benchmark report,
  and ADR index release documents.

## Verification completed locally

- The full release script passes backend lint/format/type checks, 63 tests plus two skipped
  database tests, 88.83% critical branch coverage, frontend lint/type/component tests,
  production build, four Playwright cases, axe scan, and Compose configuration validation.
- `pip-audit` and `npm audit` report no known dependency vulnerabilities.
- The populated Compose stack builds and all persistent services become healthy.
- Backup/restore recreates 17 domain tables, the Gold latest-observation view, and Alembic
  revision `20260811_0003` in an isolated scratch database.
- A disposable clean-stack run proves migrations, API, worker, and web startup from an empty
  PostgreSQL volume, then removes only its own resources.
- Draft PR [#14](https://github.com/LaboNapitupulu/NusaIntel/pull/14) passes all four hosted
  CI jobs (backend/PostgreSQL, frontend/Playwright, Compose, and security) in run
  [31470460318](https://github.com/LaboNapitupulu/NusaIntel/actions/runs/31470460318).
- First-load JavaScript stays below the 200 KiB gzip internal budget; homepage warm HTTP p95
  is 62.37 ms and profiled release queries execute below 4 ms at MVP scale.
- A six-contract live run completes in 8.657 seconds with a 133.1 MiB peak worker footprint.
- The scheduled TPT connector completed idempotently under a PostgreSQL advisory lock.
- The isolated quality case rejects a nonnumeric candidate with two critical incidents and
  preserves 117 last-known-good Gold rows; the sensitivity case records a Bali/DKI rank flip.
- HTTP transport request logging is suppressed and regression-tested after a local scheduler
  smoke exposed a credential-bearing URL.

## Verification still required

- Regenerate the BPS API key that appeared in local scheduler-smoke output.
- Capture the remaining Opportunity Engine result screenshot. Control Tower desktop and
  Regional Analytics mobile assets are now checked into `docs/assets/`; controlled browser
  access to localhost was blocked when attempting the final capture.
- Re-run hosted CI for the final Phase 6 head before promoting the draft pull request.
