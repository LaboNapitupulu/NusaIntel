# Phase 12 status — Release readiness and product safeguards

- Date: 2026-08-25
- Branch: `main`
- Candidate commit: `c1df75a`
- Hosted CI: [run `32802818466`](https://github.com/LaboNapitupulu/NusaIntel/actions/runs/32802818466)
- Status: implementation and hosted CI complete; real deployment pending

## Delivered

- Added persistent first-use guidance and editable presets for equity, growth, and workforce
  opportunity scenarios.
- Kept scenario state local to the device and shareable through an explicit URL.
- Added printable Opportunity results and a direct GitHub feedback entry point.
- Added deterministic Playwright visual baselines for the landing page on desktop/mobile and
  every product shell in light/dark themes.
- Added bounded process-local runtime metrics with release identity, request/error totals,
  status distribution, in-flight count, uptime, and rolling p50/p95 latency.
- Integrated the six patch-level dependency updates raised by Dependabot.

## Verification evidence

- Backend Ruff, Ruff format, strict mypy, and all 93 tests pass (3 intentional skips).
- Frontend lint, typecheck, 12 component tests, production build, and the full browser suite
  pass (18 executed, 4 intentional mobile shell skips).
- Visual baselines were manually inspected after generation.
- Runtime metrics exclude their own scrape request and retain at most 512 latency samples.
- Docker Compose rebuilt all four application images; migration completed; database, API,
  worker, and web services started successfully; liveness, readiness, metrics, and web smoke
  checks passed.
- Hosted frontend, backend, Compose, and security jobs all passed for `c1df75a`.

## Remaining external gate

- Obtain explicit provider, region, domains, owner, budget ceiling, RPO, and RTO decisions.
- Rotate the BPS key into the selected deployment secret store.
- Execute off-host backup/restore, deployment, and real HTTPS smoke verification.
