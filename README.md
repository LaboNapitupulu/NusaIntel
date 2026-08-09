# NusaIntel

NusaIntel is an evidence-first public-data platform composed of three product
surfaces:

- Data Reliability Control Tower
- Regional Opportunity Engine
- RegulasiLens ID

The current implementation is the Phase 1 platform foundation: FastAPI,
Next.js, PostgreSQL, a lightweight worker, Alembic migrations, structured
logging, and reproducible checks.

## Prerequisites

- Git
- Python 3.11 or newer
- Node.js 20.9 or newer (Node.js 24 is used in CI)
- Docker Desktop with Docker Compose
- A BPS WebAPI key for later connector work

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
| `BPS_API_KEY` | Phase 2 | Secret BPS WebAPI token; backend/worker only |

Real secrets belong only in `.env` or a deployment secret manager. `.env` and
runtime datasets are ignored by Git.

## Repository layout

```text
backend/       FastAPI API, worker, SQLAlchemy models, Alembic, tests
frontend/      Next.js application and component tests
docs/          Product, architecture, source, and progress evidence
scripts/       Local configuration and verification helpers
tests/         Cross-project source fixtures
compose.yaml   Local PostgreSQL and application stack
```

## License

MIT. BPS data remains subject to its official attribution and terms; see
`docs/source-inventory.md`.
