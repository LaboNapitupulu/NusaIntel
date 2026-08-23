# NusaIntel

NusaIntel is an evidence-first public-data platform composed of three product
surfaces:

- Data Reliability Control Tower
- Regional Opportunity Engine
- RegulasiLens ID

The current implementation includes the platform foundation, the completed six-indicator
BPS path, the Data Reliability Control Tower Lite, the Regional Opportunity Engine, and
regional analytics/reporting. The bounded RegulasiLens corpus and its versioned Phase 8
retrieval baseline are implemented. TPT, TPAK, poverty, PDRB per
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

The worker also supports one lightweight scheduled connector. It is disabled by default;
to run TPT immediately at worker start and then once per day, set:

```dotenv
BPS_SCHEDULE_ENABLED=true
BPS_SCHEDULE_INDICATOR=tpt
BPS_SCHEDULE_INTERVAL_SECONDS=86400
```

The interval is bounded to 5 minutes–7 days. A PostgreSQL advisory lock prevents concurrent
workers from fetching/publishing the same scheduled cycle. Keep scheduling disabled until a
valid BPS key is installed and the deployment owner has selected the intended cadence.

## Control Tower

Run the six-indicator pipeline at least once, then open <http://localhost:3100/#control-tower>.
The Control Tower distinguishes source reference period from retrieval/processing time and
keeps the last-known-good version visible when a critical check blocks a new publication.

![Control Tower showing populated quality checks and lineage](docs/assets/control-tower-desktop.jpg)

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

![Opportunity Engine showing scenario configuration, ranking, and score contributions](docs/assets/opportunity-engine-desktop.png)

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

![Regional Analytics configuration on a mobile viewport](docs/assets/regional-analytics-mobile.jpg)

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
`docs/runbook.md`, `docs/privacy-and-security.md`, and `docs/benchmark-report.md`. The
two-minute walkthrough, evidence cases, and release gate are in `docs/demo-guide.md`,
`docs/case-studies.md`, and `docs/release-scorecard.md`.

## RegulasiLens corpus foundation

Phase 7 provides a three-document personal-data-protection corpus from official JDIH BPK
sources. The checked-in manifest pins metadata, status-review date, byte count, and SHA-256.
The governed pipeline stores the immutable PDF in Bronze, publishes source-anchored legal
sections and evidenced relations, exposes every run/check/incident in Control Tower, and
preserves the last-known-good version when a changed or invalid candidate is quarantined.

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\validate_regulation_manifest.py
.\backend\.venv\Scripts\python.exe .\scripts\benchmark_regulation_parser.py
.\backend\.venv\Scripts\python.exe .\scripts\run_regulation_pipeline.py
```

Read the corpus through `GET /api/v1/regulations`,
`GET /api/v1/regulations/{document_id}`, and
`GET /api/v1/regulations/{document_id}/relations`. The parser benchmark is versioned under
`regulations/evaluation/` and currently reviews 30 positive/negative legal boundaries.

Scope, source-use policy, update rules, and limitations are documented in
`docs/regulasilens-scope.md`; ADR 0005 records the domain choice.

## RegulasiLens retrieval baseline

The retrieval API provides BM25, deterministic feature-hashing dense search, RRF hybrid
fusion, and a benchmark-justified legal reranker. The default uses versioned 1,600-character
chunks and always returns member section IDs, immutable document-version ID, official source
URL/anchor, and complete corpus/index/retriever provenance.

```powershell
$env:DATABASE_URL='postgresql+asyncpg://nusa_intel:nusa_intel_dev@localhost:5432/nusa_intel'
.\backend\.venv\Scripts\python.exe .\scripts\benchmark_regulation_retrieval.py `
  --output .\artifacts\regulasilens-retrieval-benchmark.v1.json
```

Search with `POST /api/v1/regulations/search`; inspect the selected index with
`GET /api/v1/regulations/retrieval/manifest`. The reviewed 100-question evaluation suite is
under `regulations/evaluation/`. Methodology, metrics, and known misses are recorded in
`docs/regulasilens-retrieval-benchmark.md` and ADR 0006.

## RegulasiLens grounded answers

`POST /api/v1/regulations/answer` produces an extractive answer only from retrieved,
source-anchored evidence. Every material line has a validated `[C#]` marker; insufficient or
out-of-domain evidence returns a refusal without citations. The UI shows confidence,
evidence coverage, document status/check date, disclaimer, immutable provenance, official
source links, and surrounding context.

Use `GET /api/v1/regulations/{document_id}/versions` and
`GET /api/v1/regulations/compare` for source-preserving structured version differences.
Run the 100-question beta gate with:

```powershell
$env:DATABASE_URL='postgresql+asyncpg://nusa_intel:nusa_intel_dev@localhost:5432/nusa_intel'
.\backend\.venv\Scripts\python.exe .\scripts\benchmark_regulation_answers.py `
  --output .\artifacts\regulasilens-answer-benchmark.json
```

The recorded result, rubric, and known misses are in
`docs/regulasilens-answer-benchmark.md` and ADR 0007. This beta is a retrieval and evidence
exploration tool, not legal advice.

## Configuration

| Variable | Required | Purpose |
|---|---|---|
| `APP_ENV` | No | `development`, `test`, or `production` |
| `DATABASE_URL` | Production | Async SQLAlchemy PostgreSQL URL |
| `LOG_LEVEL` | No | Structured application log level |
| `CORS_ORIGINS` | No | JSON array of allowed frontend origins |
| `ALLOWED_HOSTS` | No | JSON array of accepted HTTP hostnames; explicit public host required in production |
| `NEXT_PUBLIC_API_BASE_URL` | No | Browser-visible API origin |
| `WEB_PORT` | No | Host port for the web container; defaults to `3100` |
| `API_PORT` | No | Host port for the API container; defaults to `8000` |
| `DB_PORT` | No | Host port for local PostgreSQL; defaults to `5432` |
| `BPS_API_KEY` | Live pipeline | Secret BPS WebAPI token; backend/worker only |
| `BPS_SCHEDULE_ENABLED` | No | Enable the worker's immediate + interval BPS run; default `false` |
| `BPS_SCHEDULE_INDICATOR` | Scheduled pipeline | One of the six contracted codes; default `tpt` |
| `REGULATION_ANSWER_TIMEOUT_SECONDS` | No | Grounded-answer timeout, maximum 10 seconds; default `9` |
| `REGULATION_MAXIMUM_CONCURRENT_ANSWERS` | No | In-process answer concurrency guard; default `8` |
| `REGULATION_ANSWER_RATE_LIMIT_REQUESTS` | No | Per-process, per-direct-client answer quota; default `10` |
| `REGULATION_ANSWER_RATE_LIMIT_WINDOW_SECONDS` | No | Answer quota window; default `60` seconds |
| `BPS_SCHEDULE_INTERVAL_SECONDS` | Scheduled pipeline | Cadence from 300–604800 seconds; default `86400` |

Real secrets belong only in `.env` or a deployment secret manager. `.env` and
runtime datasets are ignored by Git.

## Public beta preflight

Use `.env.production.example` as a field list, not as deployable credentials. Production
startup fails closed unless the database URL, explicit HTTPS browser origins, public API host,
and public HTTPS frontend API URL are configured. Verify the environment without printing
secret values:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\verify_public_beta_config.py
```

Use `/api/v1/live` for process liveness and `/api/v1/ready` for traffic readiness. The API
adds security headers and a bounded per-process answer rate limiter; a public deployment still
requires TLS termination and distributed edge rate limiting. See
`docs/public-beta-deployment.md` before exposing any port publicly.

The repository also contains a standalone production candidate in `compose.production.yaml`.
It places pinned Caddy in front of the web/API, publishes only 80/443, keeps PostgreSQL private,
and requires commit-tagged application images. Validate its rendered isolation contract without
printing values:

```powershell
docker compose --env-file .env.production -f compose.production.yaml config --format json |
  .\backend\.venv\Scripts\python.exe .\scripts\verify_production_compose.py
```

Copy `.env.production.example` to the ignored `.env.production` only on the deployment host.
The provider, domains, operator, budget, recovery objectives, backup evidence, and rotated BPS
key remain mandatory go-live decisions.

## Repository layout

```text
backend/       FastAPI API, worker, SQLAlchemy models, Alembic, tests
contracts/     Portable JSON contract schema and versioning guidance
frontend/      Next.js application and component tests
docs/          Product, architecture, source, and progress evidence
scripts/       Local configuration and verification helpers
tests/         Cross-project source fixtures
compose.yaml   Local PostgreSQL and application stack
compose.production.yaml  Isolated single-host public-beta candidate
```

## License

MIT. BPS data remains subject to its official attribution and terms; see
`docs/source-inventory.md`.
