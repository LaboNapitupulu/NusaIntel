# Data dictionary

- Status: Physical schema at Alembic revision `20260816_0004`
- Updated: 2026-08-16

All timestamps are UTC. UUIDs identify immutable operational records. Region and indicator
codes are strings because they are domain identifiers, not quantities.

## Operational governance

| Table/model | Purpose | Important fields and invariants |
|---|---|---|
| `sources` / `Source` | Approved external publisher | Unique `code`; base URL, owner, attribution |
| `datasets` / `Dataset` | Logical Bronze/Silver/Gold asset | Unique `code`; `layer`, owner, freshness SLA, active flag |
| `dataset_versions` / `DatasetVersion` | Immutable dataset publication candidate/result | Source identity, SHA-256 checksum, code commit, three separate timestamps, row count, status |
| `pipeline_runs` / `PipelineRun` | One ingestion/validation execution | Run type/status, correlation ID, start/finish, safe error category |
| `data_contracts` / `DataContract` | Immutable validation policy | Dataset + version unique; JSON specification and checksum |
| `quality_check_results` / `QualityCheckResult` | Auditable check outcome | Version/run/contract links; code, severity, status, expected/observed, bounded safe sample |
| `quality_exceptions` / `QualityException` | Time-bounded waiver | Dataset/check, reason, owner, expiry, active flag |
| `schema_drift_events` / `SchemaDriftEvent` | Observed contract schema difference | Version/contract, change type, column, expected/observed |
| `incidents` / `Incident` | Actionable critical/warning failure | Dataset/run/check, severity/status, title, resolution note/time |
| `lineage_edges` / `LineageEdge` | Version-to-version provenance | Upstream/downstream version, transformation version, run ID |

## Public-data layers

| Table/model | Layer | Grain | Important fields and invariants |
|---|---|---|---|
| `raw_payloads` / `RawPayload` | Bronze | One retrieved source response | Version, endpoint, safe parameters, headers, raw body, checksum, byte/row count |
| `regions` / `Region` | Silver | One region validity interval | BPS code, name, level, parent, valid-from/to |
| `indicators` / `Indicator` | Silver | One governed indicator definition | Code, name, unit, favorable direction, definition, official source URL, period rule |
| `observations` / `Observation` | Silver | Version × region × indicator × period | Decimal value, value status, source note, national-aggregate flag |
| `quarantine_records` / `QuarantineRecord` | Silver | One rejected record | Version, safe row key/sample, reason code/detail |
| `gold_regional_observations` / `GoldRegionalObservation` | Gold | Published version × province × indicator × period | Decimal value/unit, status, national flag; only publish-gated data |
| `coverage_summaries` / `CoverageSummary` | Gold | Published version × period | Expected/observed/missing counts and coverage percent |

## Semantic rules

- `source_reference_at`: when the source data says the observation applies.
- `retrieved_at`: when NusaIntel received the response.
- `processed_at`: when NusaIntel created the version.
- `missing`: no source observation; represented as null, never numeric zero.
- `zero`: an observed numeric zero and semantically different from missing.
- `national aggregate`: retained for evidence but excluded from province comparisons.
- `dataset checksum`: content identity used for idempotency, not a display version.
- `dataset version ID`: immutable reproducibility key returned by analytical endpoints.

Analytical scores, similarity, and cluster assignments are computed on request and exported
with their configuration/version manifest; they are intentionally not persisted as facts.
See `docs/erd.md` for relationships and migration files for authoritative SQL definitions.

## RegulasiLens corpus

| Table/model | Layer | Grain | Important fields and invariants |
|---|---|---|---|
| `regulation_documents` / `RawRegulationDocument` | Bronze | One accepted source PDF per dataset version | Source URL, MIME type, SHA-256, byte count, immutable bytes; dataset version unique |
| `documents` / `RegulationDocument` | Regulations | One governed legal identity | Manifest metadata, status review, official URLs, attribution, one Control Tower dataset |
| `document_versions` / `RegulationDocumentVersion` | Regulations | Document × checksum × parser version | Parser status/confidence, section count, anchor coverage, one current published flag |
| `sections` / `RegulationSection` | Regulations | One ordered legal boundary | Stable key/order, BAB/bagian/paragraf/pasal/ayat kind, hierarchy, page/line anchor |
| `relations` / `RegulationRelation` | Regulations | One evidenced source relation | Relation type, citation, evidence URL, nullable resolved target, explicit resolved flag |

Rejected source or parser candidates remain in `ops.dataset_versions`, checks, incidents, and
quarantine records, but never become a published regulation version.
