# Phase 1 Status

- Started: 2026-08-09
- Last updated: 2026-08-09
- Status: Phase 1 exit gate passed locally and on hosted CI

## Delivered foundation

- Standalone Git repository on `main`.
- FastAPI API and separate lightweight worker.
- PostgreSQL with `ops`, `bronze`, `silver`, and `gold` schemas.
- Ten initial tables across `ops` and `silver`.
- Alembic revision `20260809_0001`.
- Database-aware `GET /api/v1/health`.
- Structured JSON logs and `X-Request-ID` correlation.
- Strict Next.js/TypeScript frontend with offline and degraded states.
- Docker Compose services: `db`, `migrate`, `api`, `worker`, and `web`.
- Backend/frontend CI, dependency audit, secret scan, and Dependabot configuration.
- Root setup documentation, environment template, editor conventions, and MIT license.

## Verification evidence

| Check | Result |
|---|---|
| Ruff lint and format | Pass |
| Mypy strict | Pass |
| Backend unit tests | 4/4 pass |
| ESLint | Pass |
| TypeScript | Pass |
| Frontend component tests | 2/2 pass |
| Next.js production build | Pass |
| Docker Compose configuration | Pass |
| Empty-database Alembic upgrade | Pass; `20260809_0001` |
| Initial physical tables | Pass; 10/10 |
| Live healthy response | Pass; HTTP 200 and database `ready` |
| Live degraded response | Pass; HTTP 503 and database `unavailable` |
| Recovery after database restart | Pass; HTTP 200 |
| Python dependency audit | Pass; zero known vulnerabilities |
| npm dependency audit | Pass; zero vulnerabilities |
| API key leak scan | Pass; zero matches outside ignored `.env` |
| Clean-clone Docker build/start | Pass on isolated ports `3200`, `8100`, and `55432` |
| Hosted GitHub Actions CI | Pass; run `31286045883` for commit `a839d97` |

## Port decision

An unrelated existing service named `spendsense_frontend` owns host port `3000`.
NusaIntel therefore publishes its web service at <http://localhost:3100> while
retaining container port `3000`. The API remains at <http://localhost:8000>.

## Hosted evidence

The initial secret-safe snapshot was created. A temporary clone built and
started an isolated empty-database stack successfully; its containers, volume,
and directory were removed afterward. GitHub Actions run
<https://github.com/LaboNapitupulu/NusaIntel/actions/runs/31286045883> completed
successfully for the Phase 1 snapshot.
