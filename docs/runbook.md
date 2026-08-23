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

## RegulasiLens retrieval

1. Ensure the approved corpus has a published version; search fails closed when no published
   sections exist.
2. Run `python scripts/benchmark_regulation_retrieval.py` against the migrated corpus.
3. Confirm the selected `hybrid_rerank` + `fixed` row retains Recall@10 ≥0.85, p95 <1.5
   seconds, and source-anchor coverage of 100%.
4. Store disposable full JSON output under ignored `artifacts/`; commit the summarized result
   and failure categories to `docs/regulasilens-retrieval-benchmark.md`.
5. Inspect `/api/v1/regulations/retrieval/manifest` before comparing results. A corpus,
   chunker, index, dense, fusion, or reranker version change invalidates direct comparisons.

Do not remove failed evaluation cases after tuning. Update the versioned evaluation set only
after manual corpus review, and issue a new evaluation version when expected references or
wording materially change.

## RegulasiLens grounded answers

1. Run `python scripts/benchmark_regulation_answers.py`; release only when the JSON result has
   `passed: true` and fabricated citation rate remains exactly zero.
2. Confirm retrieval Recall@10 ≥0.85, citation correctness ≥0.95, citation coverage ≥0.90,
   refusal accuracy ≥0.90, version-sensitive accuracy ≥0.85, and end-to-end p95 <10 seconds.
3. Ask an answerable question in `#regulasilens`, open every citation's surrounding context,
   and verify its official source link, document status, and status-check date.
4. Ask an out-of-domain question and verify a refusal with no citation.
5. Compare two stored versions only when both source texts are present. A single-version
   corpus must show an explicit unavailable state instead of manufacturing a difference.

Do not rewrite or delete failing evaluation cases to make a release pass. The diagnostic
`answer_supported_by_expected_section` rubric remains visible even though it is not a beta
threshold. A timeout returns HTTP 504; repeated saturation should be investigated before
raising `REGULATION_MAXIMUM_CONCURRENT_ANSWERS`.

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
