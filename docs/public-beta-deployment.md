# Public beta deployment gate

This document is a pre-deployment contract. It does not claim that NusaIntel is currently
hosted publicly.

## Required decisions

Record these before provisioning:

| Decision | Required evidence |
|---|---|
| Provider and region | Selected service, region, and data-residency rationale |
| Public domains | HTTPS frontend and API hostnames |
| Owner and budget | Named operator, monthly ceiling, and alert recipient |
| Database | Private network path, encryption, backup location, retention |
| Recovery | RPO, RTO, restore-test schedule, rollback owner |
| Edge | TLS, trusted proxy, distributed rate limit, request-size limit |

## Pre-deploy

- Start from `.env.production.example`; put real values only in `.env.production` on the
  deployment host or a secret manager. Never commit that file.
- Rotate any credential ever printed or copied outside its intended secret boundary.
- Set `IMAGE_TAG` to the candidate Git commit SHA. Do not use `latest`.
- Use a unique URL-safe `POSTGRES_PASSWORD` of at least 32 characters. The production Compose
  file derives the application database URL from the same value.
- Point `APP_DOMAIN` and `API_DOMAIN` to the server before starting Caddy; allow inbound
  80/TCP, 443/TCP, and 443/UDP only. Restrict SSH to the operator source where possible.
- Render and validate the topology without writing its secret-bearing output to the terminal:

  ```powershell
  docker compose --env-file .env.production -f compose.production.yaml config --format json |
    .\backend\.venv\Scripts\python.exe .\scripts\verify_production_compose.py
  ```

- Run `python scripts/verify_public_beta_config.py` when validating a non-Compose environment,
  and run the full release verifier.
- Run the RegulasiLens answer benchmark against the candidate database and retain the JSON
  artifact privately with its image/commit identifier.
- Ensure PostgreSQL is not publicly exposed and migration is an explicit one-shot job.
- Build immutable API/web images and retain the previous known-good image identifiers.

## Single-host Compose candidate

`compose.production.yaml` is standalone and must not be combined with the local `compose.yaml`.
Only Caddy publishes host ports. PostgreSQL, API, worker, web, and the migration job are private.

```powershell
docker compose --env-file .env.production -f compose.production.yaml build
docker compose --env-file .env.production -f compose.production.yaml run --rm --no-deps proxy `
  caddy validate --config /etc/caddy/Caddyfile
docker compose --env-file .env.production -f compose.production.yaml up -d
docker compose --env-file .env.production -f compose.production.yaml ps
```

Do not run `docker compose config` without `--quiet` or piping it directly into the topology
validator: rendered configuration contains secret values.

## Deploy and smoke

1. Apply migrations, then start worker/API/web.
2. Require `/api/v1/live` HTTP 200 for process health and `/api/v1/ready` HTTP 200 before
   routing traffic.
3. Verify the public frontend calls the configured HTTPS API origin and receives no CORS or
   trusted-host error.
4. Run answerable, unanswerable, citation-context, official-link, and version-unavailable
   journeys.
5. Exceed the edge test quota from an approved test source and verify HTTP 429/`Retry-After`.
6. Confirm logs contain request IDs and operational events but no credentials or full secret
   URLs.
7. Confirm public `POST /api/v1/datasets/{id}/exceptions`, public
   `PATCH /api/v1/incidents/{id}`, `/api/docs`, and `/api/openapi.json` return 404 at Caddy.

## Backup and restore gate

Before go-live, create an encrypted off-host `pg_dump --format=custom`, record its checksum,
restore it into an isolated PostgreSQL instance, run `alembic current`, and execute the critical
API/benchmark smoke against the restored database. Record the observed duration. The owner must
then approve RPO, RTO, backup cadence, retention, encryption key custody, and restore-test
schedule; a volume snapshot alone is not sufficient evidence.

## Rollback

Stop traffic, change `IMAGE_TAG` to the retained prior commit, restore those immutable
application images, and do not reverse an additive migration unless its reviewed down migration
is proven safe. If data integrity is uncertain,
preserve the database, switch the product to an unavailable state, and restore into an isolated
database before promotion. Document the incident, affected versions, and recovery evidence.

## Go-live blockers

- Any failed CI, benchmark, backup/restore, readiness, TLS, or secret-scanning gate.
- Missing provider/domain/owner/budget/RPO/RTO decision.
- A known exposed credential that has not been rotated.
- Public PostgreSQL access or absence of distributed edge rate limiting.
- More than one API replica without a reviewed trusted-client-IP design and shared limiter.
