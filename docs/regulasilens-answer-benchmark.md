# RegulasiLens grounded-answer benchmark

- Evaluation: `regulations/evaluation/answer-evaluation.v1.json`
- Evaluation version: `1.0.0`
- Corpus manifest version: `2026-08-16.1`
- Pipeline: `evidence-extractive-id-v1`
- Recorded: 2026-08-23
- Questions: 100
- Command: `python scripts/benchmark_regulation_answers.py --output artifacts/regulasilens-answer-benchmark.json`

## Results

| Metric | Result | Beta target | Status |
|---|---:|---:|---|
| Retrieval Recall@10 | 0.8917 | ≥0.85 | Pass |
| Citation correctness | 1.0000 | ≥0.95 | Pass |
| Citation coverage | 1.0000 | ≥0.90 | Pass |
| Unanswerable refusal accuracy | 0.9500 | ≥0.90 | Pass |
| Fabricated citation rate | 0.0000 | 0% | Pass |
| Version-sensitive accuracy | 0.9000 | ≥0.85 | Pass |
| Openable citation rate | 1.0000 | 100% product gate | Pass |
| End-to-end p95 | 0.0242 seconds | <10 seconds | Pass |

The pipeline passes the full beta gate. Latency was measured locally against the migrated
PostgreSQL corpus with deterministic retrieval and extraction; there are no remote model or
embedding calls in this baseline.

## Correctness rubric

A material answer claim counts as covered only when it has an inline citation marker. A
citation counts as correct only when its marker exists, its section belongs to the exact
retrieved evidence, its quote is present in that evidence, and its official source URL and
anchor are non-empty. A citation is fabricated if any of those checks fail. An unanswerable
case passes only when the pipeline refuses and returns no citations. A version-sensitive case
passes only when the expected version/status section is among the cited evidence.

`answer_supported_by_expected_section` is retained as an additional diagnostic and scores
0.8625. It is not substituted for the PRD thresholds: eleven cases were refused or did not
cite every expected section, mostly because retrieval did not surface the expected provision
or the bounded extractive selector preferred another valid source passage. Their IDs,
expected/retrieved ranks, and cited section IDs remain in the generated JSON artifact.

## Limitations

- Extractive bullets prioritize auditable evidence over natural legal synthesis.
- Retrieval misses propagate to refusal or incomplete evidence; the answer layer does not
  conceal them.
- The current migrated corpus has one published version per document, so the structured
  comparison API is unit/API tested but the live UI correctly reports that two versions are
  required.
- Results are corpus- and version-specific and are not legal advice.
