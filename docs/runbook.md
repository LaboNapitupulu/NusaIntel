# Operations runbook

## Start and verify

1. Create `.env` from `.env.example`; set a real `BPS_API_KEY` only for live ingestion.
2. Start the stack with `docker compose up --build --detach --wait`.
3. Confirm `docker compose ps` reports `db`, `api`, and `web` healthy and `migrate`
   completed successfully.
4. Check `http://localhost:8000/api/v1/health` and `http://localhost:3100`.
5. Run `scripts/verify_release.ps1 -SkipSecurityAudit` for deterministic local gates; omit
   the switch when registry access is available.

`scripts/verify_release.ps1 -FullStack` also builds and waits for the full Compose stack. It
does not delete the PostgreSQL volume.

## Ingestion

- One fixture-backed TPT run: `scripts/run_tpt_pipeline.ps1 -Fixture`.
- All six live contracts: `scripts/run_bps_pipeline.ps1`.
- Exit `0`: published or unchanged; `2`: critical quality rejection; `1`: retrieval/config
  failure.
- Re-running identical content must return `unchanged` and create no duplicate observation.

Before diagnosing a missing analytical result, confirm the requested indicator/year has a
published Gold version and inspect Control Tower quality, incidents, and reference period.

## RegulasiLens ingestion

1. Review and version `regulations/manifests/personal-data-protection.v1.json`; never update a
   checksum merely to silence drift.
2. Validate locally with `python scripts/validate_regulation_manifest.py`.
3. Run `python scripts/benchmark_regulation_parser.py`; accuracy must remain at least 95%.
4. Run `python scripts/run_regulation_pipeline.py`. Exit `0` means all documents published or
   unchanged; exit `2` means at least one candidate was rejected.
5. Repeat the pipeline and confirm all unchanged source documents reuse their dataset version.
6. Inspect `/api/v1/regulations`, the document detail/relations routes, and Control Tower.

Checksum, byte-count, MIME/PDF signature, or parser-quality failure creates auditable failure
evidence and preserves the previous published document version. Resolve the source change by
reviewing official metadata and issuing a new manifest version; do not edit stored history.

## Scheduled connector

Set `BPS_SCHEDULE_ENABLED=true`, one `BPS_SCHEDULE_INDICATOR`, and an interval between 300
and 604800 seconds. The worker runs once on startup and then maintains the configured
start-to-start cadence. Verify a safe structured `scheduled_pipeline` log containing status,
indicator, pipeline status, and run ID. Request URLs and credentials must never appear.

The PostgreSQL advisory lock makes concurrent workers return `skipped_locked` before any
fetch. Disable scheduling before key rotation, incident investigation, or a planned BPS
maintenance window; the last-known-good Gold version remains available.

## Incident response

1. Record request/correlation ID, dataset, candidate version, and failed check.
2. Confirm the last-known-good Gold version is still visible.
3. Classify retrieval, schema, contract, value, coverage, or infrastructure failure.
4. Never edit historical checks. Resolve the incident with a note after the source/contract
   issue is understood.
5. A temporary exception must include a reason, owner, and expiry and cannot waive an
   unrelated check.
6. Re-run the same immutable fixture or approved source response and confirm idempotency.
7. If a request URL containing `key=` ever appears in logs, disable scheduling, rotate the
   BPS key, preserve only redacted evidence, and treat the old credential as compromised.

## Backup and restore

With a healthy local stack:

```powershell
.\scripts\backup_restore_smoke.ps1
.\scripts\backup_restore_smoke.ps1 -RestoreSmoke
```

The first command writes a custom-format PostgreSQL dump under `artifacts/`. The smoke mode
restores into the isolated `nusa_intel_restore_smoke` database, verifies all 22 domain
tables, the Gold latest-observation view, and the Alembic revision, then drops only that
scratch database. It never overwrites the primary `nusa_intel` database.

To prove startup and migration against a completely empty database, run
`scripts/clean_stack_smoke.ps1`. It uses isolated host ports and a fixed scratch Compose
project, validates the API and web, and removes only its own containers, network, and volume.

For production, store encrypted backups outside the application host, test restores on a
schedule, and set retention/RPO/RTO with the deployment owner. The repository does not ship
cloud backup credentials.

## Rollback and recovery

- Application: redeploy the previous image/commit; do not rewrite dataset versions.
- Data candidate: reject it and retain last-known-good Gold; do not delete the evidence.
- Schema migration: prefer a forward corrective migration. Validate restore before any
  irreversible database operation.
- BPS outage/rate limit: stop retries after the bounded client policy and retain existing
  Gold data with visible freshness status.

## Shutdown

`docker compose down` stops services and preserves the named database volume. Use
`docker compose down --volumes` only for an intentional disposable-environment reset after
the exact project and backup state have been verified.
