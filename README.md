# NusaIntel

NusaIntel is an evidence-first public-data platform composed of three product
surfaces:

- Data Reliability Control Tower
- Regional Opportunity Engine
- RegulasiLens ID

The current implementation includes the platform foundation, the completed six-indicator
BPS path, the Data Reliability Control Tower Lite, the Regional Opportunity Engine, and
regional analytics/reporting. Phase 6 MVP hardening is in progress. TPT, TPAK, poverty, PDRB per
capita, PDRB growth, and HDI flow through immutable Bronze, contract-validated Silver, and
publish-gated Gold with lineage. Dataset health, freshness, quality history, schema drift,
incidents, and last-known-good state are exposed through the API and web dashboard.

## Prerequisites

- Git
- Python 3.11 or newer
- Node.js 20.9 or newer (Node.js 24 is used in CI)
- Docker Desktop with Docker Compose
- A BPS WebAPI key for live ingestion

## Quick start with Docker

1. Copy `.env.example` to `.env` if it does not already exist.
2. Keep the local development defaults and set your real `BPS_API_KEY`.
3. Start the stack:

   ```powershell
   docker compose up --build
   ```

4. Open:

   - Web: <http://localhost:3100>
   - API docs: <http://localhost:8000/api/docs>
   - Health: <http://localhost:8000/api/v1/health>
   - Dataset catalog: <http://localhost:8000/api/v1/datasets>

The `migrate` service upgrades an empty database before the API and worker
start. The API health endpoint returns HTTP 503 with a `degraded` payload when
PostgreSQL is unavailable.

Stop services without deleting the database volume:

```powershell
docker compose down
```

Delete the local database volume only when an intentional clean reset is
needed:

```powershell
docker compose down --volumes
```

## Backend development

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Checks:

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests migrations
.\.venv\Scripts\python.exe -m ruff format --check app tests migrations
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\alembic.exe upgrade head
```

## Frontend development

```powershell
cd frontend
npm ci
npm run dev
```

Checks:

```powershell
npm run lint
npm run typecheck
npm test
npm run build
```

## Full local verification

After installing backend and frontend dependencies:

```powershell
.\scripts\verify_phase1.ps1
```

Use `-SkipDocker` to run only static checks and tests.

For the Phase 6 release gate, including critical-engine branch coverage, production build,
desktop/360px Playwright journeys, axe accessibility scan, security audits, and Compose
configuration validation:

```powershell
.\scripts\verify_release.ps1
```

Use `-SkipSecurityAudit` when package registries are unavailable and `-FullStack` to also
build/start/wait for every Compose service. With a healthy stack, verify database recovery
without touching the primary database:

```powershell
.\scripts\backup_restore_smoke.ps1 -RestoreSmoke
.\scripts\clean_stack_smoke.ps1
```

The clean-stack smoke uses isolated ports and a disposable Compose project to prove that
migrations, API, worker, and web start from an empty database. It removes only its own
scratch containers, network, and volume after verification.

## Run the TPT pipeline

After the stack is healthy, ingest the live BPS August TPT series:

```powershell
.\scripts\run_tpt_pipeline.ps1
```

For an offline run using the checked-in source fixture:

```powershell
.\scripts\run_tpt_pipeline.ps1 -Fixture
```

The command exits with `0` for a new publication or unchanged input, `2` when a
critical quality gate rejects the input, and `1` for retrieval/configuration
errors. Re-running identical source content returns `unchanged` and creates no
duplicate observations.

Recovery rules and validation queries are documented in
`docs/phase-2-status.md`.

Run all six contracted indicators:

```powershell
.\scripts\run_bps_pipeline.ps1
```

## Control Tower

Run the six-indicator pipeline at least once, then open <http://localhost:3100/#control-tower>.
The Control Tower distinguishes source reference period from retrieval/processing time and
keeps the last-known-good version visible when a critical check blocks a new publication.

Primary endpoints:

- `POST /api/v1/contracts/validate`
- `GET /api/v1/datasets` and `GET /api/v1/datasets/{id}`
- `GET /api/v1/datasets/{id}/quality`
- `GET /api/v1/pipeline-runs`
- `GET /api/v1/lineage/{dataset_id}`
- `GET /api/v1/incidents` and `PATCH /api/v1/incidents/{id}`

The portable contract schema and versioning rules are in `contracts/`. Phase 3 acceptance
and benchmark evidence is recorded in `docs/phase-3-status.md`.

## Regional Opportunity Engine

Run the six-indicator pipeline, then open <http://localhost:3100/#opportunity>.
Select two to five provinces and a common analysis year, configure weights and direction,
then calculate the scenario. Indicator-specific reference periods remain visible even when
their official months differ.

Primary endpoints:

- `GET /api/v1/opportunity/indicators` and `GET /api/v1/opportunity/regions`
- `POST /api/v1/opportunity/compare`
- `POST /api/v1/opportunity/score`
- `POST /api/v1/opportunity/sensitivity`
- `POST /api/v1/opportunity/export`

The scoring method, missing-data behavior, and reproduction steps are documented in
`docs/methodology.md`. Phase 4 acceptance and benchmark evidence is recorded in
`docs/phase-4-status.md`.

## Regional Analytics

Run the six-indicator pipeline, then open <http://localhost:3100/#regional-analytics>.
Choose two to six comparable indicators, a province, and a common year. The report provides
similar regions with driver explanations, evidence-gated clusters, a schematic tile map,
an equivalent table, source/version citations, a regional detail page, JSON download, and
print layout.

Primary endpoints:

- `POST /api/v1/opportunity/analytics/similarity`
- `POST /api/v1/opportunity/analytics/clusters`
- `POST /api/v1/opportunity/analytics/report`
- `GET /api/v1/opportunity/regions/{region_code}?year=2024`

The tile map is explicitly schematic and contains no third-party administrative boundary
geometry. The deterministic preprocessing, similarity formula, validation thresholds, and
limitations are documented in `docs/regional-analytics-methodology.md`; the source/licensing
decision is in ADR 0004 and Phase 5 evidence is in `docs/phase-5-status.md`.

Release architecture, physical data definitions, operations, security, and benchmark
evidence are maintained in `docs/architecture.md`, `docs/data-dictionary.md`,
`docs/runbook.md`, `docs/privacy-and-security.md`, and `docs/benchmark-report.md`.

## Configuration

| Variable | Required | Purpose |
|---|---|---|
| `APP_ENV` | No | `development`, `test`, or `production` |
| `DATABASE_URL` | Production | Async SQLAlchemy PostgreSQL URL |
| `LOG_LEVEL` | No | Structured application log level |
| `CORS_ORIGINS` | No | JSON array of allowed frontend origins |
| `NEXT_PUBLIC_API_BASE_URL` | No | Browser-visible API origin |
| `WEB_PORT` | No | Host port for the web container; defaults to `3100` |
| `API_PORT` | No | Host port for the API container; defaults to `8000` |
| `DB_PORT` | No | Host port for local PostgreSQL; defaults to `5432` |
| `BPS_API_KEY` | Live pipeline | Secret BPS WebAPI token; backend/worker only |

Real secrets belong only in `.env` or a deployment secret manager. `.env` and
runtime datasets are ignored by Git.

## Repository layout

```text
backend/       FastAPI API, worker, SQLAlchemy models, Alembic, tests
contracts/     Portable JSON contract schema and versioning guidance
frontend/      Next.js application and component tests
docs/          Product, architecture, source, and progress evidence
scripts/       Local configuration and verification helpers
tests/         Cross-project source fixtures
compose.yaml   Local PostgreSQL and application stack
```

## License

MIT. BPS data remains subject to its official attribution and terms; see
`docs/source-inventory.md`.
