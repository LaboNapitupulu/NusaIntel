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

- Start from `.env.production.example`; put real values only in a secret manager.
- Rotate any credential ever printed or copied outside its intended secret boundary.
- Run `python scripts/verify_public_beta_config.py` and the full release verifier.
- Run the RegulasiLens answer benchmark against the candidate database and retain the JSON
  artifact privately with its image/commit identifier.
- Ensure PostgreSQL is not publicly exposed and migration is an explicit one-shot job.
- Build immutable API/web images and retain the previous known-good image identifiers.

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

## Rollback

Stop traffic, restore the prior immutable application images, and do not reverse an additive
migration unless its reviewed down migration is proven safe. If data integrity is uncertain,
preserve the database, switch the product to an unavailable state, and restore into an isolated
database before promotion. Document the incident, affected versions, and recovery evidence.

## Go-live blockers

- Any failed CI, benchmark, backup/restore, readiness, TLS, or secret-scanning gate.
- Missing provider/domain/owner/budget/RPO/RTO decision.
- A known exposed credential that has not been rotated.
- Public PostgreSQL access or absence of distributed edge rate limiting.
