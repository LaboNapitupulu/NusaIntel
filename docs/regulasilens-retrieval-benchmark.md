# RegulasiLens retrieval benchmark

- Evaluation: `regulations/evaluation/retrieval-cases.v1.json`
- Evaluation version: `1.0.0`
- Corpus manifest version: `2026-08-16.1`
- Recorded: 2026-08-23
- Questions: 100 total; 80 answerable and 20 unanswerable
- Command: `python scripts/benchmark_regulation_retrieval.py --output artifacts/regulasilens-retrieval-benchmark.v1.json`

## Results

Recall is macro-averaged over answerable questions. Unanswerable cases are tracked as
out-of-domain diagnostics and are not counted as retrieval recall. Latency includes the public
service call; the first index build is retained in timings, while p95 prevents one cold build
from defining steady-state search.

| Method | Chunker | Recall@5 | Recall@10 | p95 seconds | Anchor coverage |
|---|---|---:|---:|---:|---:|
| BM25 | legal structure | 0.6375 | 0.6937 | 0.0307 | 100% |
| Dense hashing | legal structure | 0.6333 | 0.7104 | 0.0359 | 100% |
| Hybrid RRF | legal structure | 0.6542 | 0.7646 | 0.0422 | 100% |
| Hybrid + reranker | legal structure | 0.6542 | 0.7667 | 0.1027 | 100% |
| Hybrid RRF | fixed 1,600 chars | 0.7583 | 0.8292 | 0.0145 | 100% |
| **Hybrid + reranker** | **fixed 1,600 chars** | **0.8083** | **0.8917** | **0.0448** | **100%** |

The selected row passes the Recall@10 target of 0.85 and p95 target of 1.5 seconds. The
reranker adds 0.0625 Recall@10 over raw hybrid on the same fixed chunks, so it is adopted.

## Selected provenance

| Component | Version |
|---|---|
| Corpus | `2026-08-16.1` |
| Retrieval | `regulation-retrieval-v1` |
| BM25 | `bm25-k1-1.5-b-0.75-v1` |
| Dense | `hashing-tfidf-2048-id-v1` |
| Fusion | `rrf-k60-v1` |
| Reranker | `legal-coverage-diversity-v1` |
| Chunker | `fixed-1600-char-v1` |
| Index | `0dc50549b2f60ef50d3d7af1` |

## Failure analysis

Eleven answerable questions are not fully recalled at 10: five direct lookup cases, one
paraphrase, and five multi-document cases. The multi-document category is the main weakness:
the selected system retrieves at least one relevant provision but sometimes misses one of
three required documents. Multi-section and version-sensitive categories both reach 1.0;
paraphrased reaches 0.95 and direct lookup reaches 0.875.

Failures remain in the JSON artifact with question ID, expected section IDs, retrieved IDs,
category, and observed recall. They are not removed or silently rewritten during tuning.
