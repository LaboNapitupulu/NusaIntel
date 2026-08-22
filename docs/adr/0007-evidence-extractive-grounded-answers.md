# ADR 0007 — Use evidence-extractive grounded answers

- Status: Accepted
- Date: 2026-08-23

## Context

RegulasiLens must answer Indonesian legal-corpus questions without inventing claims, article
numbers, document status, or citations. Phase 8 retrieval is measurable but still has known
expected-section misses, especially on broad and multi-document questions. A generative model
would add cost and nondeterminism before claim-level faithfulness has been proven.

## Decision

The beta uses a deterministic extractive pipeline. It selects only retrieved evidence,
copies supported passages into answer bullets, binds each bullet to an inline `[C#]` marker,
and validates every marker and citation against the supplied evidence before returning it.
Low-coverage and out-of-domain questions fail closed with an explicit refusal and zero
citations. Each citation retains the immutable document version, member section IDs, verbatim
quote, official URL/anchor, status, and status-check date.

The public API bounds question length and citation count, applies a nine-second timeout and a
concurrency semaphore, and records zero external model calls in provenance. Version comparison
is structured by source sections and never summarizes a side whose source text is absent.

## Evidence

The reviewed 100-question Phase 9 evaluation passes every PRD beta target: Recall@10 0.8917,
citation correctness 1.0, claim coverage 1.0, refusal accuracy 0.95, fabricated citation rate
0, version-sensitive accuracy 0.90, openable citations 1.0, and p95 0.0242 seconds on the
recorded local environment.

## Consequences

- Answers favor traceability over fluent synthesis and can contain longer source excerpts.
- The answer is evidence navigation, not legal advice; the disclaimer remains mandatory.
- The diagnostic expected-section support score is 0.8625, so known retrieval/selection misses
  remain published for future tuning even though all beta release thresholds pass.
- A future generative model may replace this baseline only after a new versioned evaluation
  preserves zero fabricated citations, meets all gates, and justifies its operational cost.
