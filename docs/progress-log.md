# Progress Log

## Phase 0 — 2026-08-08

### Outcome delivered

- Confirmed the province-level 2023–2025 MVP and six indicators.
- Recorded architecture, source, indicator, and logical data-model decisions.
- Configured BPS WebAPI access without committing the credential.
- Captured and decoded a live TPT fixture for August 2023–2025.

### Benchmarks

- Authenticated BPS request: pass.
- TPT response: 113/117 expected cells (96.58%).
- 2024 and 2025: all 38 provinces available.
- 2023: four new Papua provinces have no separate observation.
- Offline decoder: passes documentation and live fixtures.
- Secret leak scan: zero matches outside `.env`.

### Quality evidence

- `tests/fixtures/bps/README.md`
- `spikes/parse_bps_fixture.py`
- `docs/phase-0-status.md`

### Decisions

- Use August (`turth=190`) for the comparable TPT series.
- Preserve unavailable historical province cells as missing; never convert them to zero.
- Defer a formal historical-geography policy to the Silver/Gold contract design.

### Risks/blockers

- Five remaining indicator API contracts still require live discovery.
- Official API rate-limit guidance remains unconfirmed.
- Province GeoJSON source and license remain to be selected.

### Next phase

- Start Phase 1 repository and local-platform foundation.

## Phase 1 — 2026-08-09

### Outcome delivered

- Initialized `nusa-intel` as a standalone Git repository.
- Added FastAPI API and worker with structured JSON logging and request IDs.
- Added strict Next.js/TypeScript frontend with explicit backend health states.
- Added PostgreSQL schemas, ten foundation tables, and Alembic migration.
- Added Docker Compose, GitHub Actions, Dependabot, audits, and setup documentation.

### Benchmarks

- Backend: Ruff pass, Mypy pass, 4/4 tests pass.
- Frontend: ESLint pass, TypeScript pass, 2/2 tests pass, production build pass.
- Docker: database, API, web, and worker start together.
- Migration: empty PostgreSQL database upgraded to `20260809_0001`.
- Health failure injection: HTTP 503 degraded while database is stopped; HTTP 200 healthy after recovery.
- Dependency audits: zero known Python vulnerabilities and zero npm vulnerabilities.
- Docker frontend context reduced from more than 500 MB to less than 1 KB after service-level `.dockerignore` was added.
- Clean clone: isolated Docker stack passed API, migration, and web probes, then temporary resources were removed.
- Hosted CI: GitHub Actions run `31286045883` passed for commit `a839d97`.

### Quality evidence

- `backend/tests/`
- `frontend/components/system-status.test.tsx`
- `.github/workflows/ci.yml`
- `docs/phase-1-status.md`

### Decisions

- Use MIT for the repository license.
- Use host port `3100` for NusaIntel web because port `3000` is owned by an unrelated local service.
- Keep the worker separate from the API process from the first platform phase.

### Risks/blockers

- Phase 2 still needs production connector behavior, contracts, and ingestion idempotency.

### Next phase

- Start the production-shaped BPS connector and Bronze ingestion vertical slice.

## Phase 2 — 2026-08-09

### Outcome delivered

- Added a credential-safe BPS client with timeout, bounded retry, jitter, and conservative throttling.
- Added immutable Bronze payloads, contract-normalized Silver observations, publish-gated Gold observations, coverage summaries, quarantine records, and latest-valid view.
- Added deterministic observation/version checksums and Bronze → Silver → Gold lineage.
- Added and fixture-backed all six MVP contracts with one-command live batch ingestion.

### Benchmarks

- Live source rows: 768; normalized/published contract rows: 702.
- Explicit missing values: 51; silent zero imputations: 0.
- PDRB indicators: `38/38` provinces for 2023–2025.
- TPT, TPAK, poverty: `34/38` in 2023 and `38/38` in 2024–2025.
- IPM method-new: `38/38` in 2023–2024; 2025 unavailable in WebAPI and explicit missing.
- Three-run connector-plus-normalization median: `5.555 s`.
- Full-batch re-run: all six `unchanged`; additional versions, rows, and runs: 0.
- Lineage edges: 12; failed critical checks: 0; quarantine rows: 0.

### Quality evidence

- Backend: Ruff pass, Mypy pass, 20/20 tests pass including isolated PostgreSQL failure injection.
- Six credential-safe live fixtures pass deterministic regression tests.
- Live Docker batch published once and returned unchanged on the second run.
- PostgreSQL audit confirmed six versions per layer, 702 Gold rows, and complete lineage.
- Empty-database migration reached `20260809_0002` with 15 application tables.
- `docs/phase-2-status.md`

### Risks/blockers

- Official BPS rate-limit guidance remains unavailable; the client uses a conservative default.
- IPM method-new 2025 is not currently exposed by WebAPI and remains explicit missing.

### Next step

- Start Phase 3 Data Reliability Control Tower after hosted CI passes.
