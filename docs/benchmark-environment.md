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
