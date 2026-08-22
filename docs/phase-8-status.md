# Phase 8 status — Retrieval baseline and evaluation harness

- Status: Complete — local exit gate passed
- Date completed: 2026-08-23
- Branch: `codex/phase-8-retrieval-baseline`
- Baseline: Phase 7 merge commit `00a88f0`

## Delivered

- Added a strict versioned evaluation schema and 100 manually reviewed Indonesian questions.
- Covered direct lookup, paraphrase, multi-section, multi-document, unanswerable, and
  version/status-sensitive cases with expected document and section IDs.
- Implemented deterministic BM25, TF-IDF feature-hashing dense retrieval, RRF hybrid fusion,
  legal query normalization, explanatory-section handling, and a measured reranker.
- Compared legal-structure chunks with a fixed 1,600-character baseline and selected the
  better-performing fixed configuration.
- Added `POST /api/v1/regulations/search` and `GET /api/v1/regulations/retrieval/manifest`.
- Returned immutable document/section provenance, official source URL/anchor, and all active
  model/index/chunker versions with every search.

## Gate evidence

- Selected Recall@5: 0.8083.
- Selected Recall@10: 0.8917 against target ≥0.85.
- Selected p95: 0.0448 seconds against target <1.5 seconds.
- Source URL and anchor coverage: 100%.
- Reranker gain over fixed hybrid baseline: +0.0625 Recall@10; adoption is justified.
- All evaluation questions remain tracked; full failure categories are retained in the
  generated benchmark artifact and summarized in `docs/regulasilens-retrieval-benchmark.md`.

Phase 9 answer generation may proceed, but multi-document retrieval remains the first
quality-improvement target and generated answers must never conceal missing support.
