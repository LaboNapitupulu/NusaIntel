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

- The full release script passes backend lint/format/type checks, 57 tests plus two skipped
  database tests, 88.83% critical branch coverage, frontend lint/type/component tests,
  production build, four Playwright cases, axe scan, and Compose configuration validation.
- `pip-audit` and `npm audit` report no known dependency vulnerabilities.
- The populated Compose stack builds and all persistent services become healthy.
- Backup/restore recreates 17 domain tables, the Gold latest-observation view, and Alembic
  revision `20260811_0003` in an isolated scratch database.
- A disposable clean-stack run proves migrations, API, worker, and web startup from an empty
  PostgreSQL volume, then removes only its own resources.

## Verification still required

- Run hosted CI from the Phase 6 pull request.
- Complete screenshots, demo path, case studies, resource/bundle evidence, and release
  scorecard before promoting the draft pull request.
