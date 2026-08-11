# Phase 3 status — Data Reliability Control Tower Lite

- Status: Complete and merged
- Date: 2026-08-11
- Branch: `codex/phase-3-control-tower`
- Release target: `0.2`

## Outcome

Phase 3 turns the Phase 2 medallion pipeline into an auditable reliability product.
Versioned contracts are validated before use, every quality result records its contract,
critical failures open incidents and block Gold, and the last-known-good Gold version
remains available. The Control Tower API and responsive UI expose dataset health,
freshness, reference period, runs, checks, schema drift, lineage, incidents, and resolution
notes.

## Delivered scope

### Contracts and quality engine

- Strict contract format `1.0` in Pydantic and portable JSON Schema.
- Immutable dataset `contract_version`; Phase 3 rules use version `2` after the Phase 2
  indicator metadata contract.
- Column/type/nullability, composite uniqueness, min/max, accepted values, bounded custom
  operators, freshness, and row-count change rules.
- `info`, `warning`, and `critical` severities with expected/observed values.
- Safe samples limited to five rows, eight named fields, and 160 characters per value.
- Schema additions, removals, type changes, and constraint changes represented as drift
  events.
- Time-bounded exception records require check code, reason, owner, and expiry. Expired
  exceptions cannot bypass a gate.

### Persistence and quality gate

- Alembic revision `20260811_0003` adds exceptions, drift events, incidents, and contract/
  exception references on quality results.
- All six Silver and six Gold MVP datasets receive version-2 contracts.
- Critical non-waived failures reject a Silver version, create auditable incidents, and do
  not create or replace Gold.
- `source_reference_at`, `retrieved_at`, and `processed_at` remain separate.
- Valid Gold versions retain complete Bronze → Silver → Gold lineage.

### API and UI

- Contract validation: `POST /api/v1/contracts/validate`.
- Catalog/detail/quality: `GET /api/v1/datasets`, `/{id}`, and `/{id}/quality`.
- Runs and lineage: `GET /api/v1/pipeline-runs` and `/lineage/{dataset_id}`.
- Incidents: `GET /api/v1/incidents` and audited `PATCH /incidents/{id}`.
- Exceptions: `POST /api/v1/datasets/{id}/exceptions`.
- UI includes loading, empty, failure/retry, filtered quality history, schema drift, lineage,
  pipeline history, incident resolution, and explicit last-known-good evidence.

## Exit-gate evidence

| Gate | Result | Evidence |
|---|---|---|
| Corrupted fixture blocked from Gold | Pass | Invalid numeric fixture returns `rejected`; failed critical checks and incidents persist |
| UI explains failure | Pass | Dataset health, failed check code/severity, open incident, and version status are visible |
| Last-known-good remains served | Pass | Gold row count and version remain unchanged after rejected run |
| Incident resolution is auditable | Pass | Status, resolution note, and `resolved_at` are persisted; empty note is rejected |
| No orphan Gold lineage | Pass | Integration assertion checks every published Gold version has an upstream edge |

## Benchmarks

Benchmark environment: Docker Compose internal network, PostgreSQL 17, Python 3.13,
six checked-in BPS fixtures, Windows host described in `docs/benchmark-environment.md`.

| Metric | Target | Result |
|---|---:|---:|
| Silver/Gold contract coverage | 100% | 12/12 (100%) |
| Critical failures reaching Gold | 0 | 0 |
| Six-contract execution | < 60 s | 0.7787 s |
| Dataset-health API p95, 30 calls | < 500 ms | 76.36 ms |
| Scheduled/dry-run success | ≥ 95% over 30 | 30/30 (100%) |
| Safe failing-row sample | bounded | 5 rows maximum |

## Quality evidence

- Backend: Ruff pass, formatting pass, strict Mypy pass.
- Backend unit/API: 29 passed; two PostgreSQL tests skip unless `RUN_DB_TESTS=1`.
- Isolated PostgreSQL integration/benchmark: 2 passed.
- Frontend: ESLint pass, TypeScript pass, 4 tests pass, production build pass.
- Browser QA: populated Silver detail, quality filters, lineage, run history, zero console
  errors, and a 390 px mobile viewport without horizontal overflow.
- Migration from empty database reaches `20260811_0003`.
- `docker compose config --quiet` passes.

## Operational notes

- The dashboard reports retrieval freshness independently from source reference period.
- Closing an incident does not change historical quality results.
- An exception only changes gate evaluation while it is active and unexpired; the failed
  check is stored as `waived` with its exception ID.
- Rejected data is retained in Bronze/Silver for diagnosis, while consumers continue using
  last-known-good Gold.

## Remaining external verification

- Pull request: [#11](https://github.com/LaboNapitupulu/NusaIntel/pull/11).
- Hosted pull-request CI: [run 31454614843](https://github.com/LaboNapitupulu/NusaIntel/actions/runs/31454614843),
  with backend, frontend, Compose, and security jobs passing.
- PR #11 was merged as commit `df07d0a2461876bf47f99d0136563297bd7928aa`.
- Record the merged-main run ID when the post-merge workflow completes.
