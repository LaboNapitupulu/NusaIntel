# Phase 7 status — RegulasiLens corpus foundation

- Status: In progress — discovery and governed-ingestion primitives complete
- Date started: 2026-08-16
- Branch: `codex/phase-7-regulasilens-corpus`
- Baseline: Phase 6 merge commit `647b143`

## First corpus tranche

- Selected personal-data protection as the limited first domain in ADR 0005.
- Defined explicit inclusion/exclusion criteria, a five-value status vocabulary, source
  attribution, link-and-local-cache policy, and a 30-day manual update review.
- Added a strict three-document manifest using official JDIH BPK metadata and PDF URLs.
- Verified every initial PDF signature, byte count, and SHA-256 on 2026-08-16 without
  committing the downloaded documents.
- Added approved-host enforcement and fail-closed download checks for HTTP failure, size,
  content type, PDF signature, checksum, and byte-count drift.
- Added a deterministic structure parser for BAB, bagian, paragraf, pasal, and ayat with
  stable section IDs, original order, page/line anchors, hierarchy, parser version, and
  explicit `needs_review` state.
- Live non-persisting smoke accepts all three checksum-pinned PDFs. UU 27/2022 yields 279
  sections/133 Pasal boundaries, PP 71/2019 yields 438/197, and Permenkominfo 20/2016 yields
  136/39; all parsed sections retain source anchors. Counts include explanatory sections and
  are not treated as a manual accuracy benchmark.

## Remaining Phase 7 work

- Persist document versions, sections, relations, quarantines, and ingestion runs.
- Add the corpus pipeline to the Control Tower and protect last-known-good retrieval state.
- Run the parser against all three official PDFs and record manual boundary-review samples.
- Expose unresolved legal references separately from resolved graph edges.
- Prove corpus rebuild and Phase 7 quality benchmarks from a clean database.
