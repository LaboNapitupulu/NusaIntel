# Benchmark Environment

- Recorded: 2026-08-09
- Condition: live BPS requests, warm local Python environment, sequential requests
- Repetitions: 3

| Component | Value |
|---|---|
| OS | Windows 11 Home Single Language, 64-bit, build 10.0.26200 |
| CPU | AMD Ryzen 7 5800H, 8 cores / 16 logical processors |
| RAM | 15.34 GiB visible |
| Python | 3.12.13 locally; project supports 3.11+ and container/CI use 3.13 |
| Node.js | 24.18.0 |
| PostgreSQL | 17.10 |
| Docker Engine | 29.2.1 |
| Docker Compose | 5.0.2 |
| Normalized rows | 702 across six indicators |
| Raw rows | 768 across six source responses |

## Live pipeline benchmark

The measured operation is sequential BPS retrieval plus deterministic
normalization and quality evaluation for all six contracts. It excludes Docker
startup and database publication.

| Run | Duration |
|---:|---:|
| 1 | 5.555 s |
| 2 | 5.539 s |
| 3 | 5.576 s |
| **Median** | **5.555 s** |

All runs produced identical normalized checksums, zero invalid values, zero
quarantine rows, and publishable quality reports for all contracts. IPM 2025 is
an explicit source-unavailable period, not a benchmark failure.

## RegulasiLens retrieval benchmark

- Recorded: 2026-08-23
- Corpus: 837 published sections across three regulation versions
- Evaluation: 100 reviewed questions; one pass per method/chunker configuration
- Database: PostgreSQL 17 on local Docker, exposed at port 55432 for the benchmark
- Timing: Python `perf_counter`, including service call; p95 over 100 questions

The selected hybrid-reranked fixed-1,600 configuration measured Recall@5 0.8083,
Recall@10 0.8917, p95 0.0448 seconds, and 100% source-anchor coverage. Full methodology and
comparisons are in `docs/regulasilens-retrieval-benchmark.md`.
