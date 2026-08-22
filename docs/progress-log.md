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
- Hosted PR CI run `31288960900` passed all four jobs for commit `d36c890`.
- Merged `main` CI run `31289068592` passed all four jobs for merge commit `49962b1`.
- `docs/phase-2-status.md`

### Risks/blockers

- Official BPS rate-limit guidance remains unavailable; the client uses a conservative default.
- IPM method-new 2025 is not currently exposed by WebAPI and remains explicit missing.

### Next step

- Start Phase 3 Data Reliability Control Tower from the verified `main` branch
  after the dependency and branch cleanup is complete.

## Phase 3 — 2026-08-11

### Outcome delivered

- Added portable, strict, versioned dataset contracts and a generic quality engine.
- Added contract-linked quality results, exceptions, schema drift, and auditable incidents.
- Added the Control Tower catalog/detail/quality/runs/lineage/incidents API surface.
- Added a responsive Control Tower dashboard with explicit last-known-good evidence.

### Benchmarks

- Silver/Gold contract coverage: 12/12 (100%).
- Six-contract execution: 0.7787 seconds versus < 60 seconds.
- Dataset-health API p95: 76.36 ms versus < 500 ms over 30 calls.
- Dry-run success: 30/30 (100%) versus ≥ 95%.
- Critical failures reaching Gold: zero.

### Quality evidence

- Backend: Ruff, formatting, and strict Mypy pass; 29 unit/API tests pass.
- Isolated PostgreSQL: two integration/benchmark tests pass.
- Frontend: ESLint, TypeScript, four tests, and production build pass.
- Empty database migration reaches `20260811_0003`.
- `docs/phase-3-status.md`

### Decisions

- ADR 0002 selects strict JSON contracts with allow-listed custom operators.
- Every quality result references the immutable contract version used.
- Exceptions require reason, owner, and expiry; historical failures are never rewritten.

### Risks/blockers

- The benchmark reflects the 18-dataset MVP catalog; pagination and query limits remain
  mandatory as the catalog grows.

### Merge evidence

- PR [#11](https://github.com/LaboNapitupulu/NusaIntel/pull/11) merged after all four hosted
  checks passed.
- Merge commit: `df07d0a2461876bf47f99d0136563297bd7928aa`.

### Next phase

- Start Phase 4 Regional Opportunity Engine from the verified merge commit.

## Phase 4 — 2026-08-11

### Outcome delivered

- Added a source/version-aware indicator and province catalog for the Opportunity Engine.
- Added deterministic min-max and percentile normalization, direction handling, coverage
  gates, contributions, tied ranking, and sensitivity scenarios.
- Added comparison, score, sensitivity, and export APIs over immutable Gold observations.
- Added a responsive configuration and evidence UI with a table alternative for charts,
  ineligible states, methodology drawer, URL sharing, and JSON export.
- Preserved each indicator's official reference month inside a common analysis year.

### Benchmarks

- Reproducibility: 100%.
- All 38-region scoring p95: 1.267 ms versus < 500 ms.
- Hidden zero imputation: 0.
- Indicator metadata: 6/6 complete.
- Opportunity scoring engine line coverage: 95%.

### Quality evidence

- Backend: Ruff, formatting, strict Mypy pass; 48 unit/API tests pass and two database tests
  are available for the hosted PostgreSQL job.
- Frontend: ESLint, TypeScript, six component tests, and production build pass.
- ADR 0003, `docs/methodology.md`, and `docs/phase-4-status.md` capture decisions and gates.

### Risks/blockers

- Local Docker/browser verification remains optional and requires a fresh explicit execution
  approval after the desktop approval mechanism rejected the earlier Docker run.

### Hosted evidence

- PR [#12](https://github.com/LaboNapitupulu/NusaIntel/pull/12) is ready to merge.
- Hosted run [31457229496](https://github.com/LaboNapitupulu/NusaIntel/actions/runs/31457229496)
  passes backend/PostgreSQL, frontend, Compose build, and security jobs for commit `dbd2fd3`.

### Next step

- Merge PR #12 when explicitly approved, then start Phase 5 from verified `main`.

## Phase 5 — 2026-08-11

### Outcome delivered

- Added deterministic, version-bound complete-case preprocessing and similar-region search.
- Added candidate-`k` clustering with silhouette/stability evidence and fail-closed withholding.
- Added a keyboard-operable schematic tile choropleth for all 38 BPS provinces plus an
  equivalent data table and explicit non-boundary disclaimer.
- Added regional detail pages and printable/JSON reports with units, sources, reference
  periods, dataset versions, methodology, exclusions, and limitations.

### Quality evidence

- Backend Ruff/format/strict Mypy pass; 57 local tests pass and 2 isolated PostgreSQL tests
  await hosted CI.
- Frontend ESLint, TypeScript, 8 tests, and production build pass.
- Engine tests prove row-order invariance, deterministic versioning, cluster evidence,
  neutral descriptions, and withholding of degenerate structure.
- ADR 0004 documents why Phase 5 uses a self-authored schematic map instead of
  redistributing mismatched or license-ambiguous boundary data.

### Next step

- PR [#13](https://github.com/LaboNapitupulu/NusaIntel/pull/13) is ready to merge. Hosted run
  [31465223016](https://github.com/LaboNapitupulu/NusaIntel/actions/runs/31465223016)
  passes backend/PostgreSQL, frontend, Compose, and security; the full-report benchmark
  remains below its enforced 500 ms p95 threshold.

### Merge evidence

- PR #13 merged into `main` as `a0b2e07` after all four checks passed.

## Phase 6 — 2026-08-11

### Hardening started

- Created `codex/phase-6-mvp-hardening` from the verified Phase 5 merge.
- Added an 85% branch-coverage gate; critical engines currently reach 88.83%.
- Added four production-build Playwright journeys across desktop and 360 px.
- Added axe scanning and fixed discovered contrast/keyboard-scroll violations to zero
  serious/critical findings in the regional journey.
- Added CI E2E coverage, error/404 routes, release verification, backup/restore smoke, and
  the missing architecture/operations/security/release documentation set.

### Next step

- Populated Compose passes with database, API, worker, and web healthy.
- Backup/restore smoke passes with 17 domain tables, the Gold latest-observation view, and
  Alembic revision `20260811_0003` restored to a scratch database.
- Clean-stack smoke passes from an empty isolated PostgreSQL volume and removes its own
  containers, network, and volume afterward.
- Full release verification, `pip-audit`, and `npm audit` pass locally.
- Draft PR [#14](https://github.com/LaboNapitupulu/NusaIntel/pull/14) opened; hosted run
  [31470460318](https://github.com/LaboNapitupulu/NusaIntel/actions/runs/31470460318)
  passes backend/PostgreSQL, frontend/Playwright, Compose, and security.

### Next step

- Finish portfolio/resource evidence, then promote PR #14 from draft when all release gates
  are closed.

### Second hardening tranche

- Added a disabled-by-default TPT scheduler with a bounded cadence and PostgreSQL advisory
  lock; an actual scheduled run completed as `unchanged`.
- Suppressed `httpx`/`httpcore` request logging after scheduler smoke revealed that the BPS
  query credential could appear in local logs; the second smoke emitted only safe fields.
- Added reproducible route-bundle, live-pipeline resource, and SQL query profiling.
- Added an isolated fail-closed quality incident case and a public-data rank-sensitivity case.
- Added the two-minute demo guide and PRD release scorecard.

### Release closure — 2026-08-16

- The deployment owner regenerated the BPS key and recreated the worker while keeping the
  scheduler disabled by default; the replacement secret was neither displayed nor committed.
- Added the populated Control Tower desktop, Opportunity Engine desktop, and Regional
  Analytics mobile screenshots to the README and closed the documentation gate.
- Hosted run [31900689643](https://github.com/LaboNapitupulu/NusaIntel/actions/runs/31900689643)
  passes all four jobs on evidence commit `b5ab9ce`; PR #14 is ready for promotion and merge.

### Merge evidence

- PR #14 merged into `main` as `647b143` after all four required checks passed.

## Phase 7 — 2026-08-16

### Corpus foundation started

- Created `codex/phase-7-regulasilens-corpus` from Phase 6 merge `647b143`.
- Selected personal-data protection as the bounded first corpus and recorded ADR 0005.
- Added strict scope, status vocabulary, source-use policy, update mechanism, and a
  checksum-pinned three-document JDIH BPK manifest.
- Added fail-closed retrieval primitives and a deterministic, source-anchored structural
  parser with unit tests. Database persistence and Control Tower integration are next.
- Opened draft PR [#15](https://github.com/LaboNapitupulu/NusaIntel/pull/15); hosted run
  [31901770812](https://github.com/LaboNapitupulu/NusaIntel/actions/runs/31901770812) passes
  all four CI jobs on the initial implementation commit.

### Corpus foundation completed

- Added revision `20260816_0004`, immutable Bronze PDF storage, versioned regulation
  documents/sections, evidenced relations, and read APIs.
- Integrated ingestion runs, contract checks, quarantine, incidents, and last-known-good
  behavior with Control Tower.
- Corrected OCR `Pasal I` and repeated ayat page-boundary handling; the versioned manual
  benchmark passes 30/30 reviewed cases (100%, target ≥95%).
- A live first run published 274 + 427 + 136 source-anchored sections; the second run returned
  `unchanged` for all three documents with identical dataset-version IDs.
- Database integration proves rejected candidates stay quarantined while the published legal
  version remains available. Final release verification and hosted CI follow.
- Clean-stack and backup/restore smokes pass with 22 domain tables, the Gold view, and
  Alembic revision `20260816_0004`; both scratch environments were removed after verification.

## Phase 8 — 2026-08-23

### Retrieval baseline and evaluation harness

- Created a strict versioned schema and 100 manually reviewed retrieval questions spanning
  all required direct, paraphrased, multi-section, multi-document, unanswerable, and
  version-sensitive categories.
- Implemented BM25, deterministic TF-IDF feature hashing, RRF hybrid fusion, structure and
  fixed chunkers, legal normalization, explanatory duplicate handling, and provenance.
- Benchmark evidence justified adopting the legal coverage/diversity reranker and the
  fixed-1,600 chunker: Recall@5 0.8083, Recall@10 0.8917, p95 0.0448 seconds, and 100% anchors.
- Added search/index-manifest APIs, validation/unit/API tests, and database integration
  assertions that published sections remain source-anchored and version reproducible.
