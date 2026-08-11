# NusaIntel — Implementation Plan

| Field | Value |
|---|---|
| Document status | Draft v0.1 |
| Created | 2026-08-08 |
| Estimated roadmap | MVP 8–12 weeks part-time; RegulasiLens beta tambahan 6–8 weeks |
| MVP | Control Tower Lite + Regional Opportunity Engine |
| Beta extension | RegulasiLens ID |
| Source of product requirements | `PRD.md` |

## 1. Purpose

Dokumen ini menerjemahkan PRD menjadi urutan implementasi, deliverables, quality gates, benchmark, dan Definition of Done.

Aturan utama:

- Satu fase tidak dianggap selesai hanya karena UI terlihat bekerja.
- Setiap fase memiliki bukti berupa test, benchmark, artifact, atau dokumentasi.
- Fase berikutnya boleh dimulai untuk spike, tetapi release gate fase aktif tetap harus dipenuhi.
- Scope baru masuk backlog dan tidak menggantikan acceptance criteria tanpa pembaruan PRD.
- Data atau dokumen yang gagal quality gate tidak boleh dipublikasikan ke layer Gold.

## 2. Delivery strategy

Urutan produk:

```text
Foundation
    ↓
BPS Connector + Medallion Pipeline
    ↓
Control Tower Lite
    ↓
Regional Opportunity Engine
    ↓
Portfolio Hardening
    ↓
RegulasiLens Ingestion
    ↓
RegulasiLens Retrieval + Evaluation
```

MVP pertama harus memberikan vertical slice lengkap:

```text
BPS source
  → versioned Bronze
  → validated Silver
  → publish-gated Gold
  → API
  → regional comparison UI
  → visible lineage and quality status
```

## 3. Proposed repository structure

```text
nusa-intel/
├── .github/
│   └── workflows/
├── apps/
│   ├── web/
│   └── worker/
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   └── pyproject.toml
├── pipelines/
│   ├── connectors/
│   ├── contracts/
│   ├── transformations/
│   └── tests/
├── regulasilens/
│   ├── ingestion/
│   ├── retrieval/
│   ├── evaluation/
│   └── tests/
├── data/
│   ├── samples/
│   └── README.md
├── docs/
│   ├── adr/
│   ├── architecture.md
│   ├── data-dictionary.md
│   ├── methodology.md
│   └── runbook.md
├── infra/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── PRD.md
└── IMPLEMENTATION_PLAN.md
```

Runtime data, downloaded documents, database volumes, credentials, model weights, and browser profiles must be ignored from Git.

## 4. Engineering standards

### 4.1 Backend

- Python 3.11 or newer.
- Type hints on public functions and critical internal interfaces.
- Ruff for lint/format enforcement.
- Pyright or mypy for selected strict type checking.
- Pytest for unit and integration tests.
- Decimal for values requiring exact decimal behavior.
- UTC timestamps internally; source reference period stored separately.

### 4.2 Frontend

- TypeScript strict mode.
- ESLint and formatter enforcement.
- Runtime validation for external API payloads where appropriate.
- Vitest for unit/component tests.
- Playwright for critical user journeys.
- Accessible HTML before custom interaction patterns.

### 4.3 Data

- Raw response is immutable and checksum-addressable.
- Transformation is deterministic for the same input and code version.
- No silent coercion of invalid values to zero.
- Missing, invalid, suppressed, and unavailable values remain distinguishable.
- Every Gold table has a data contract and primary/composite key.

### 4.4 Git and review

- Work is split into focused commits.
- Secrets and personal data are prohibited.
- Pull request checklist includes tests, migration impact, data-contract impact, and screenshots when UI changes.
- Architecture-changing decisions require an ADR.

## 5. Benchmark environment

Performance numbers are meaningful only when the environment is recorded. Before benchmarking, create `docs/benchmark-environment.md` containing:

- Operating system.
- CPU and RAM.
- Python, Node.js, PostgreSQL, and Docker versions.
- Dataset row counts and version checksums.
- Warm-cache versus cold-cache condition.
- Number of benchmark repetitions.

Baseline methodology:

- Use at least 30 requests for API latency checks after five warm-up requests.
- Report p50, p95, maximum, and error rate.
- Run pipeline benchmark at least three times and report median.
- Never compare numbers from different dataset sizes without normalization.

## 6. Phase 0 — Discovery and architecture decisions

**Goal:** Remove high-risk uncertainty before scaffolding the full product.

**Estimated duration:** 2–3 days.

### Tasks

- [x] Confirm the repository name `nusa-intel` and public/private status.
- [x] Select MVP geographic level: province or regency/city.
- [x] Request/configure BPS WebAPI access according to official documentation.
- [x] Inspect candidate indicators for coverage, units, periods, and definitions.
- [x] Select six MVP indicators with compatible coverage.
- [x] Record source URLs and attribution requirements.
- [x] Spike one BPS API request and persist an unchanged fixture.
- [x] Compare Pandas and Polars only on representative transformations.
- [x] Compare a simple scheduler and Prefect against MVP requirements.
- [x] Decide PostgreSQL schema strategy for Bronze metadata, Silver, and Gold.
- [x] Select frontend map library after license and bundle-size review.
- [x] Create ADRs for decisions that materially affect architecture.

### Deliverables

- `docs/adr/0001-architecture.md`
- `docs/source-inventory.md`
- `docs/indicator-selection.md`
- Sanitized BPS response fixture.
- Initial entity relationship diagram.

### Exit gate

- [x] Six indicators have source, definition, unit, direction, and coverage evidence.
- [x] One API fixture can be parsed without live network access.
- [x] No unresolved decision blocks Phase 1 scaffolding.

## 7. Phase 1 — Repository and local platform foundation

**Goal:** Produce a clean, reproducible development environment.

**Estimated duration:** 3–4 days.

### Tasks

- [x] Initialize standalone Git repository only when repository boundaries are confirmed.
- [x] Add root `.gitignore`, `.editorconfig`, `.env.example`, and license decision.
- [x] Scaffold FastAPI backend.
- [x] Scaffold Next.js frontend with strict TypeScript.
- [x] Add PostgreSQL and application services to Docker Compose.
- [x] Configure Alembic migrations.
- [x] Add `/api/v1/health` with database readiness.
- [x] Add structured logging with request/run correlation IDs.
- [x] Add backend lint, typecheck, unit-test commands.
- [x] Add frontend lint, typecheck, unit-test, and build commands.
- [x] Add baseline GitHub Actions workflow.
- [x] Add secret scanning and dependency audit.
- [x] Document local setup and common commands.

### Initial schema

- [x] `sources`
- [x] `datasets`
- [x] `dataset_versions`
- [x] `pipeline_runs`
- [x] `data_contracts`
- [x] `quality_check_results`
- [x] `lineage_edges`
- [x] `regions`
- [x] `indicators`
- [x] `observations`

### Tests

- [x] Health endpoint reports healthy with database available.
- [x] Health endpoint reports degraded when database is unavailable.
- [x] Empty database upgrades to Alembic head.
- [x] Configuration rejects missing required production settings.
- [x] Frontend handles backend unavailable state.

### Exit gate

- [x] `docker compose up --build` starts the local stack from a clean clone.
- [x] CI executes lint, typecheck, tests, migrations, and builds.
- [x] No high/critical secret or dependency finding remains unreviewed.
- [x] No runtime data is tracked by Git.

## 8. Phase 2 — BPS connector and medallion pipeline

**Goal:** Build one production-shaped, versioned ingestion path.

**Estimated duration:** 5–7 days.

### Tasks: connector

- [x] Implement a BPS client with explicit timeout.
- [x] Add bounded retries with exponential backoff and jitter.
- [x] Apply conservative client-side rate limiting and identify the client appropriately.
- [x] Separate authentication/configuration from connector logic.
- [x] Parse errors into typed failure categories.
- [x] Store retrieval timestamp, safe URL/parameters, HTTP metadata, checksum, and row count.
- [x] Store raw payload before transformation.
- [x] Prevent duplicate dataset versions by source identity and checksum.

### Tasks: Bronze

- [x] Define immutable checksum-addressed raw version strategy.
- [x] Persist source metadata and exact raw response in PostgreSQL.
- [x] Add fixture-based ingestion tests.
- [x] Add JSON, envelope, metadata-contract, and composite-key corruption detection.

### Tasks: Silver

- [x] Normalize region codes and names for all six MVP contracts.
- [x] Normalize period representation.
- [x] Normalize units and numeric formats.
- [x] Preserve original value and status for invalid/missing values.
- [x] Produce deterministic observation keys.

### Tasks: Gold

- [x] Build application-ready regional observation table/view.
- [x] Add coverage summary by indicator and period.
- [x] Add latest-valid-version selection logic.
- [x] Record lineage edges for every transformation.

### Tests

- [x] Timeout behavior.
- [x] Retry stops after configured attempts.
- [x] Duplicate ingestion is idempotent across all six indicators.
- [x] Same fixture and code produce the same Silver checksum.
- [x] Invalid numeric values are not silently converted to zero.
- [x] Unknown region mappings are quarantined.
- [x] Partial transformation does not publish Gold.

### Benchmarks

- [x] Connector handles the six-indicator MVP fixture set without parser edits.
- [x] Re-running all six unchanged inputs creates zero duplicate observations.
- [x] Transformation determinism passes 100% on all six live fixtures.
- [x] All six indicators achieve documented coverage; unavailable IPM 2025 remains explicit missing data.

### Exit gate

- [x] One command runs all six sources → Bronze → Silver → Gold paths.
- [x] Every output row is traceable to a source version and pipeline run.
- [x] A failed run cannot replace the last-known-good Gold version.
- [x] Recovery instructions are documented.

## 9. Phase 3 — Data Reliability Control Tower Lite

**Goal:** Make data health visible and enforce publish quality gates.

**Estimated duration:** 5–7 days.

### Tasks: contracts

- [x] Define versioned YAML or JSON contract schema.
- [x] Validate contract syntax before pipeline execution.
- [x] Support column/type/nullability rules.
- [x] Support primary/composite uniqueness.
- [x] Support min/max, accepted values, and custom checks.
- [x] Support freshness and row-count change thresholds.
- [x] Store contract version used by each quality run.

### Tasks: quality engine

- [x] Implement severity levels: info, warning, critical.
- [x] Store expected and observed values.
- [x] Limit and sanitize failing-row samples.
- [x] Detect schema additions, removals, and type changes.
- [x] Block Gold publication on critical failure.
- [x] Allow exception only with reason, owner, and expiry.

### Tasks: Control Tower API/UI

- [x] Dataset catalog page.
- [x] Dataset detail and current health.
- [x] Pipeline-run history.
- [x] Quality-check history and filters.
- [x] Freshness status.
- [x] Schema-diff viewer.
- [x] Basic lineage graph/list.
- [x] Incident status and resolution note.

### Tests

- [x] Critical contract failure blocks publish.
- [x] Warning does not block but remains visible.
- [x] Expired exception no longer bypasses the gate.
- [x] Freshness distinguishes reference period from retrieval time.
- [x] Schema change creates a drift event.
- [x] Lineage has no orphan Gold dataset.

### Benchmarks

| Benchmark | Target |
|---|---|
| Contract coverage | 100% Silver and Gold MVP datasets |
| Critical failures reaching Gold | 0 |
| Check execution | Under 60 seconds for MVP dataset on benchmark machine |
| Health API p95 | Under 500 ms |
| Scheduled/dry-run success | ≥ 95% over 30 runs before MVP release |

### Exit gate

- [x] A deliberately corrupted fixture is blocked from Gold.
- [x] The UI clearly explains why it failed.
- [x] Last-known-good data remains served.
- [x] Incident resolution is recorded and auditable.

## 10. Phase 4 — Regional Opportunity Engine core

**Goal:** Deliver transparent regional comparison and scoring.

**Estimated duration:** 7–10 days.

### Tasks: indicator catalog

- [x] Add definitions, units, favorable direction, source, and periods.
- [x] Expose coverage and quality status.
- [x] Prevent comparison across incompatible definitions or units.

### Tasks: comparison

- [x] Region and period selectors.
- [x] Compare 2–5 regions.
- [x] Raw values, normalized values, trends, and distribution views.
- [x] Data table alternative for every chart.
- [x] Source and methodology drawer.

### Tasks: scoring

- [x] Implement min-max normalization.
- [x] Implement percentile/rank normalization.
- [x] Implement favorable/unfavorable direction explicitly.
- [x] Validate weights sum to 100% within an accepted tolerance.
- [x] Enforce missing-data coverage threshold.
- [x] Return contribution per indicator.
- [x] Persist/share configuration without storing user identity.

### Tasks: sensitivity

- [x] Perturb selected weights within a configurable range.
- [x] Re-normalize total weights.
- [x] Report rank stability and largest movers.
- [x] Explain that sensitivity is not confidence or causal inference.

### Tests

- [x] Known fixture produces hand-calculated score.
- [x] Weight validation rejects negative or invalid totals.
- [x] Unfavorable indicator direction is correct.
- [x] Missing value never becomes zero silently.
- [x] Same version and configuration produce identical score.
- [x] Incompatible indicators cannot be combined.
- [x] Changing one weight changes only expected contributions.

### Benchmarks

| Benchmark | Target |
|---|---|
| Scoring reproducibility | 100% |
| Score calculation p95 | < 500 ms for all MVP regions |
| Hidden imputation | 0 occurrences |
| Indicator source metadata | 100% complete |
| Business-logic coverage | ≥ 90% for normalization/scoring modules |

### Exit gate

- [x] A reviewer can reproduce one score manually from displayed data.
- [x] Every ranking has contribution and methodology details.
- [x] UI refuses to rank regions below the configured coverage threshold.
- [x] Export contains dataset version and score configuration.

## 11. Phase 5 — Regional analytics, map, and reporting

**Goal:** Add useful exploration without compromising methodological clarity.

**Estimated duration:** 5–7 days.

### Similarity

- [ ] Select only comparable, sufficiently complete features.
- [ ] Fit preprocessing deterministically.
- [ ] Implement distance-based similar-region search.
- [ ] Explain indicators driving similarity/difference.
- [ ] Test invariance to row ordering.

### Clustering

- [ ] Compare candidate `k` values.
- [ ] Record silhouette score and stability across seeds/bootstrap samples.
- [ ] Version feature set and preprocessing.
- [ ] Generate neutral, evidence-based cluster descriptions.
- [ ] Do not expose clustering if validation is materially weak.

### Map and reporting

- [ ] Choropleth with legend, no-data state, and keyboard-accessible alternative.
- [ ] Regional detail page.
- [ ] Printable/exportable report.
- [ ] Methodology, limitations, and citations included in export.
- [ ] Formula-injection-safe CSV export if CSV is supported.

### Benchmarks

- [ ] Similar-region result is deterministic for fixed version/configuration.
- [ ] Cluster report includes at least silhouette and stability evidence.
- [ ] Export contains no value without unit/source context.
- [ ] Main regional flow passes at 360 px and desktop viewport.

### Exit gate

- [ ] Comparison, scoring, sensitivity, similarity, and export work end to end.
- [ ] Charts have non-visual equivalents.
- [ ] No normative cluster labels are generated automatically.

## 12. Phase 6 — MVP hardening and release

**Goal:** Turn a working application into a credible portfolio release.

**Estimated duration:** 5–7 days.

### Quality and testing

- [ ] Backend unit/integration suite.
- [ ] Frontend unit/component suite.
- [ ] Playwright critical journeys on desktop and 360 px.
- [ ] Migration test from empty database.
- [ ] End-to-end pipeline test using fixtures.
- [ ] Accessibility scan and manual keyboard smoke test.
- [ ] Dependency and secret audit.
- [ ] Backup/restore smoke test.

### Performance

- [ ] Create reproducible benchmark script/configuration.
- [ ] Record p50/p95 API metrics.
- [ ] Profile slow queries and add justified indexes.
- [ ] Validate frontend bundle and primary page loading.
- [ ] Confirm pipeline resource usage on benchmark environment.

### Documentation

- [ ] README with architecture, setup, screenshots, and limitations.
- [ ] `docs/architecture.md`.
- [ ] `docs/data-dictionary.md`.
- [ ] `docs/methodology.md`.
- [ ] `docs/runbook.md`.
- [ ] `docs/privacy-and-security.md`.
- [ ] `docs/benchmark-report.md`.
- [ ] ADR index.

### Portfolio presentation

- [ ] Synthetic or public-only demo.
- [ ] Architecture diagram.
- [ ] Two-minute demo path.
- [ ] Case study: one detected data-quality incident.
- [ ] Case study: one ranking changes after sensitivity analysis.
- [ ] Explicit limitations and next steps.

### MVP release gate

- [ ] All PRD Section 18.1 criteria pass.
- [ ] All CI jobs pass from the release commit.
- [ ] No open critical data-quality incident.
- [ ] No high/critical security finding remains unexplained.
- [ ] Docker stack health is verified together.
- [ ] Clean-clone setup is verified by following only README.

## 13. Phase 7 — RegulasiLens corpus foundation

**Goal:** Build a trustworthy, version-aware legal-document dataset for one domain.

**Estimated duration:** 7–10 days.

### Discovery

- [ ] Select one domain: employment, personal-data protection, or education.
- [ ] Define inclusion/exclusion criteria.
- [ ] Create initial regulation source manifest.
- [ ] Record source terms, attribution, and update mechanism.
- [ ] Define document status vocabulary.

### Ingestion

- [ ] Download only from approved official sources.
- [ ] Store URL, retrieval timestamp, checksum, and content type.
- [ ] Detect unchanged documents by checksum.
- [ ] Quarantine corrupt or unsupported documents.
- [ ] Add document-ingestion runs to Control Tower.

### Parsing

- [ ] Extract text with page/source anchors where possible.
- [ ] Detect document title and metadata.
- [ ] Parse BAB, bagian, pasal, and ayat structure.
- [ ] Preserve original ordering.
- [ ] Validate section uniqueness and continuity.
- [ ] Maintain parser confidence/status.
- [ ] Add manual review sample for every parser version.

### Regulation graph

- [ ] Store explicit relations only when supported by metadata/text evidence.
- [ ] Link changed/revoked documents.
- [ ] Expose unresolved references separately.

### Quality benchmarks

| Benchmark | Target |
|---|---|
| Metadata completeness | ≥ 98% required fields on included corpus |
| Document checksum coverage | 100% |
| Section/source anchor coverage | ≥ 95% parsed sections |
| Manual parser sample accuracy | ≥ 95% correct structural boundaries |
| Failed document visibility | 100% visible in Control Tower |

### Exit gate

- [ ] Corpus can be rebuilt from the source manifest.
- [ ] Every section is traceable to a regulation version and source URL.
- [ ] Failed documents cannot silently enter the retrieval index.

## 14. Phase 8 — Retrieval baseline and evaluation harness

**Goal:** Establish measurable retrieval quality before answer generation.

**Estimated duration:** 7–10 days.

### Evaluation set

- [ ] Define versioned evaluation-case schema.
- [ ] Create at least 100 manually reviewed questions.
- [ ] Include direct lookup questions.
- [ ] Include paraphrased questions.
- [ ] Include multi-section and multi-document questions.
- [ ] Include unanswerable questions.
- [ ] Include version-sensitive/status questions.
- [ ] Record expected relevant document/section IDs.

### Retrieval

- [ ] Implement BM25/keyword baseline.
- [ ] Implement dense retrieval baseline.
- [ ] Implement hybrid fusion.
- [ ] Evaluate chunking by structure versus fixed-size baseline.
- [ ] Add reranker only if benchmark improvement justifies complexity.
- [ ] Record index, embedding, chunker, and corpus versions.

### Benchmarks

- [ ] BM25 baseline report completed.
- [ ] Dense baseline report completed.
- [ ] Hybrid Recall@5 and Recall@10 measured.
- [ ] Target Retrieval Recall@10 ≥ 0.85.
- [ ] Search p95 < 1.5 seconds on benchmark environment.
- [ ] No evaluation case is included in prompt tuning without being tracked.

### Exit gate

- [ ] Hybrid retrieval meets or exceeds target.
- [ ] Failure analysis categorizes missed cases.
- [ ] Retrieval results always retain source anchors.
- [ ] Generation work does not begin if retrieval remains below the agreed gate, except for isolated prototyping.

## 15. Phase 9 — Grounded answers and RegulasiLens beta

**Goal:** Generate useful answers without unsupported legal claims.

**Estimated duration:** 7–10 days.

### Answer pipeline

- [ ] Use only retrieved evidence supplied to the answer model.
- [ ] Require inline citation markers tied to section IDs.
- [ ] Validate every citation exists in the supplied evidence.
- [ ] Add answerability/confidence policy.
- [ ] Refuse when evidence coverage is insufficient.
- [ ] Display disclaimer and source date/status.
- [ ] Allow user to open full surrounding context.
- [ ] Add request limits, timeouts, and cost/usage guardrails.

### Comparison

- [ ] Compare two regulation versions by structured sections.
- [ ] Show additions, removals, and modifications.
- [ ] Avoid summarizing a difference if corresponding source text cannot be shown.

### Evaluation

- [ ] Citation correctness.
- [ ] Citation coverage.
- [ ] Answer correctness with documented rubric.
- [ ] Unanswerable refusal accuracy.
- [ ] Version-sensitive accuracy.
- [ ] Fabricated citation rate.
- [ ] Latency and failure rate.

### Beta benchmarks

| Metric | Required result |
|---|---|
| Retrieval Recall@10 | ≥ 0.85 |
| Citation correctness | ≥ 0.95 |
| Citation coverage | ≥ 0.90 |
| Refusal accuracy | ≥ 0.90 |
| Fabricated citations | 0% |
| Version-sensitive accuracy | ≥ 0.85 |
| End-to-end p95 | < 10 seconds on recorded benchmark environment |

### Exit gate

- [ ] All PRD Section 18.2 release criteria pass.
- [ ] No known fabricated citation remains in the evaluation set.
- [ ] Each answer can open every cited source section.
- [ ] Limitations are visible in product and documentation.

## 16. Test strategy

### 16.1 Unit tests

Prioritize deterministic business logic:

- Normalization.
- Weight validation.
- Score contribution.
- Missing-data policy.
- Sensitivity perturbation.
- Contract evaluation.
- Schema diff.
- Region mapping.
- Regulation section parsing.
- Citation validation.

### 16.2 Contract tests

- BPS fixture against connector parser.
- Backend OpenAPI schema against frontend expectations.
- Data contracts against Silver/Gold outputs.
- Retrieval result schema against answer pipeline.

### 16.3 Integration tests

- PostgreSQL repository and migrations.
- Pipeline run and publish transaction.
- Critical quality-gate failure.
- API query against seeded Gold data.
- Document ingest → parse → index.

### 16.4 End-to-end tests

MVP critical paths:

1. Open dashboard and verify data health.
2. Compare two regions.
3. Configure weights and calculate score.
4. Inspect contribution and methodology.
5. Run sensitivity analysis.
6. Export report.
7. View a failed quality check.

RegulasiLens critical paths:

1. Search regulation.
2. Ask answerable question and open citations.
3. Ask unanswerable question and receive refusal.
4. Compare two versions.

### 16.5 Failure injection

- Source timeout.
- HTTP rate limiting.
- Malformed JSON.
- Missing column.
- Type drift.
- Sudden row-count decrease.
- Duplicate observation keys.
- Corrupt PDF.
- Missing citation target.
- Model/provider timeout.

## 17. CI quality gates

Every pull request should run:

- [ ] Backend lint.
- [ ] Backend typecheck.
- [ ] Backend unit/integration tests.
- [ ] Migration upgrade from empty database.
- [ ] Frontend lint.
- [ ] Frontend typecheck.
- [ ] Frontend unit tests.
- [ ] Frontend production build.
- [ ] Fixture-based pipeline tests.
- [ ] Contract validation.
- [ ] Secret scanning.
- [ ] Dependency audit.

Release candidate additionally runs:

- [ ] Docker Compose health test.
- [ ] Playwright E2E.
- [ ] Accessibility automation.
- [ ] Performance smoke benchmark.
- [ ] RegulasiLens evaluation suite when applicable.

## 18. Backlog prioritization

Use this order:

1. Data correctness and traceability.
2. Critical user journey.
3. Automated quality gate.
4. Explainability and accessibility.
5. Performance proven by benchmark.
6. Additional data sources.
7. Visual polish.
8. Experimental features.

Do not prioritize these before MVP quality gates:

- Authentication/multi-user accounts.
- Mobile native application.
- Custom dashboard builder.
- Dozens of indicators.
- Real-time streaming without a real source requirement.
- Multiple LLM providers.
- Autonomous policy recommendations.
- Fine-tuning large models.

## 19. Progress scorecard

Update this table at the end of every milestone.

| Area | Weight | Current | Evidence |
|---|---:|---:|---|
| Data ingestion and reproducibility | 15% | 100% | Six live, fixture-backed, idempotent Bronze → Silver → Gold paths |
| Data contracts and quality gates | 15% | 100% | Versioned contracts cover all 12 Silver/Gold datasets; critical gate, exceptions, drift, and incidents tested |
| Regional methodology correctness | 15% | 100% | Version-bound normalization, direction, coverage, contribution, tie, and sensitivity rules pass hand-calculated tests |
| Regional user journeys | 15% | 75% | Comparison, scoring, ineligible state, table alternative, share, and export work locally; hosted/browser gate pending |
| Testing and CI | 10% | 100% | 48 local backend/API and six frontend tests pass; hosted PostgreSQL, frontend, Compose, and security jobs pass |
| Performance and reliability | 10% | 100% | Six-contract run 0.7787 s, API p95 76.36 ms, 30/30 dry-runs, last-known-good verified |
| Accessibility and UX | 5% | 75% | Responsive semantic UI, keyboard-native controls, live status, loading/empty/error/ineligible states, and table alternatives |
| Security and privacy | 5% | 75% | Credential controls remain; scenario URLs store configuration without identity and untrusted state is shape-validated |
| Documentation and reproducibility | 10% | 100% | ADRs, methodology, phase status, immutable versions, export evidence, fixtures, and benchmarks are documented |
| **Total** | **100%** | **93.75%** | Phase 4 implementation and hosted CI are complete; PR #12 is ready to merge |

Scoring rule:

- `0%`: not started.
- `25%`: spike or partial implementation exists.
- `50%`: primary implementation works locally.
- `75%`: tests and documentation exist, but release gate not complete.
- `100%`: acceptance criteria and benchmark pass with evidence.

Overall progress is weighted. A visually complete dashboard cannot exceed the milestone gate if correctness or reliability remains incomplete.

## 20. Weekly review template

At the end of each working week, add a short entry to `docs/progress-log.md`:

```markdown
## Week N — YYYY-MM-DD

### Outcome delivered
- ...

### Benchmarks
- Metric: result versus target

### Quality evidence
- Tests/CI/report links

### Decisions
- ADR or scope decision

### Risks/blockers
- ...

### Next week
- ...
```

## 21. Definition of Done

A feature is done only when:

- [ ] Acceptance behavior is implemented.
- [ ] Error, empty, loading, and permission/configuration states are handled.
- [ ] Unit/integration tests cover critical logic.
- [ ] Relevant E2E flow is updated.
- [ ] Accessibility is considered.
- [ ] Observability/logging is sufficient to diagnose failure.
- [ ] Data contract and migration impact are addressed.
- [ ] Security/privacy implications are reviewed.
- [ ] Documentation is updated.
- [ ] CI passes.

A milestone is done only when its exit gate passes with reproducible evidence.

## 22. Immediate next actions

Phase 4 implementation and hosted CI are complete. The next release actions are:

1. Merge PR #12 when explicitly approved.
2. Sync verified `main` and record the merged-main CI run.
3. Optionally perform populated desktop/mobile browser QA when local Docker execution is explicitly approved.
4. Start Phase 5 regional analytics, map, and reporting.
