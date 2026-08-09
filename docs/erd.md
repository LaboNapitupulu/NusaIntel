# Initial Entity Relationship Diagram

- Status: Phase 0 logical model
- Date: 2026-08-08

```mermaid
erDiagram
    SOURCE ||--o{ DATASET : owns
    DATASET ||--o{ DATASET_VERSION : versions
    DATASET ||--o{ DATA_CONTRACT : governed_by
    DATASET_VERSION ||--o{ PIPELINE_RUN : processed_by
    DATASET_VERSION ||--o{ QUALITY_CHECK_RESULT : evaluated_by
    DATASET_VERSION ||--o{ LINEAGE_EDGE : upstream
    DATASET_VERSION ||--o{ LINEAGE_EDGE : downstream
    PIPELINE_RUN ||--o{ QUALITY_CHECK_RESULT : produces
    REGION ||--o{ OBSERVATION : has
    INDICATOR ||--o{ OBSERVATION : measures
    DATASET_VERSION ||--o{ OBSERVATION : supplies
    SCORE_CONFIGURATION ||--o{ SCORE_WEIGHT : contains
    INDICATOR ||--o{ SCORE_WEIGHT : weighted_by
    SCORE_CONFIGURATION ||--o{ SCORE_RUN : executes
    SCORE_RUN ||--o{ SCORE_RESULT : produces
    REGION ||--o{ SCORE_RESULT : receives

    SOURCE {
        uuid id PK
        string code UK
        string name
        string base_url
        string owner
        string attribution
        timestamp created_at
    }

    DATASET {
        uuid id PK
        uuid source_id FK
        string code UK
        string name
        string layer
        string owner
        interval freshness_sla
        boolean active
    }

    DATASET_VERSION {
        uuid id PK
        uuid dataset_id FK
        string source_identity
        string checksum
        string code_commit
        timestamp source_reference_at
        timestamp retrieved_at
        timestamp processed_at
        integer row_count
        string status
    }

    PIPELINE_RUN {
        uuid id PK
        uuid dataset_version_id FK
        string run_type
        string status
        timestamp started_at
        timestamp finished_at
        string correlation_id
        string error_category
    }

    DATA_CONTRACT {
        uuid id PK
        uuid dataset_id FK
        integer version
        jsonb specification
        string checksum
        timestamp effective_at
    }

    QUALITY_CHECK_RESULT {
        uuid id PK
        uuid dataset_version_id FK
        uuid pipeline_run_id FK
        string check_code
        string severity
        string status
        jsonb expected
        jsonb observed
        jsonb safe_sample
    }

    LINEAGE_EDGE {
        uuid id PK
        uuid upstream_version_id FK
        uuid downstream_version_id FK
        string transformation_version
        string run_id
    }

    REGION {
        string code PK
        string name
        string level
        string parent_code
        date valid_from
        date valid_to
    }

    INDICATOR {
        string code PK
        string name
        string unit
        string favorable_direction
        string definition
        string source_url
        string reference_period_rule
    }

    OBSERVATION {
        uuid id PK
        string region_code FK
        string indicator_code FK
        uuid dataset_version_id FK
        date period
        decimal value
        string value_status
        string source_note
        boolean is_national_aggregate
    }

    SCORE_CONFIGURATION {
        uuid id PK
        string name
        string normalization_method
        decimal minimum_coverage
        jsonb version_manifest
        timestamp created_at
    }

    SCORE_WEIGHT {
        uuid configuration_id FK
        string indicator_code FK
        decimal weight
        string direction_override
    }

    SCORE_RUN {
        uuid id PK
        uuid configuration_id FK
        string code_commit
        timestamp generated_at
        jsonb dataset_versions
    }

    SCORE_RESULT {
        uuid score_run_id FK
        string region_code FK
        decimal score
        integer rank
        decimal coverage
        jsonb contributions
    }
```

## Schema placement

| Entity group | PostgreSQL schema |
|---|---|
| Source, Dataset, DatasetVersion, PipelineRun, Contract, Checks, Lineage | `ops` |
| Unchanged BPS response payload | `bronze` |
| Region, Indicator, normalized Observation | `silver` |
| Scoring configuration, score run/results, coverage marts | `gold` |

## Modeling notes

- `source_reference_at`, `retrieved_at`, and `processed_at` are separate concepts.
- Province codes must be stored as strings to preserve leading zeroes and code semantics.
- National aggregate is retained but excluded from province ranking.
- Provisional, revised, unavailable, zero, and missing values must remain distinguishable through `value_status` and notes.
- `ScoreRun` freezes dataset versions and code commit so results can be reproduced.
- The model will be refined into physical SQLAlchemy models during Phase 1.
