# ADR 0006 — Use a versioned local hybrid retrieval baseline

- Status: Accepted
- Date: 2026-08-23

## Context

RegulasiLens needs measurable retrieval before answer generation. The first corpus is small
enough to run locally, but it contains OCR variation, repeated explanatory sections, long
pasal, multi-ayat provisions, and questions that span multiple documents. Depending on a
remote embedding API would add credentials, cost, and nondeterminism before its quality gain
was demonstrated.

## Decision

Phase 8 ships four reproducible components:

1. BM25 keyword retrieval.
2. A deterministic 2,048-dimension TF-IDF feature-hashing baseline using Indonesian synonym
   normalization and character n-grams.
3. Reciprocal-rank fusion for hybrid retrieval.
4. A lightweight legal coverage/diversity reranker that separates document selectors from
   substantive query terms and down-ranks explanatory duplicates.

The selected production configuration is hybrid plus reranker over 1,600-character chunks.
The structure-aware alternative remains benchmarked and available. Every response retains
all member section IDs, document-version ID, official source URL and anchor, plus corpus,
index, retriever, dense, fusion, reranker, and chunker versions.

## Evidence

The manually reviewed evaluation set contains 100 tracked Indonesian questions across direct,
paraphrased, multi-section, multi-document, unanswerable, and version-sensitive categories.
On the recorded local environment, the selected configuration reaches Recall@5 0.8083,
Recall@10 0.8917, p95 0.0448 seconds, and 100% source-anchor coverage. The raw hybrid fixed
baseline reaches Recall@10 0.8292, so the measured reranker improvement justifies its use.

## Consequences

- Phase 9 may build grounded answers on the selected retrieval configuration.
- The feature-hashing baseline is not claimed to be equivalent to a trained semantic model.
- Multi-document misses remain the largest known failure class and must stay visible in the
  versioned benchmark.
- A future embedding model or chunker replaces this configuration only after a new versioned
  benchmark demonstrates a material improvement without losing provenance.
