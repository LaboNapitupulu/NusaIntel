# Phase 7 status — RegulasiLens corpus foundation

- Status: Complete — ready for final CI and merge
- Date completed: 2026-08-16
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
- Added revision `20260816_0004`, immutable Bronze PDF storage, versioned regulation
  documents/sections, evidenced relations, and catalog/detail/relation APIs.
- Integrated ingestion runs, contract checks, quarantine, incidents, and last-known-good
  behavior with Control Tower.
- Added a deterministic structure parser for BAB, bagian, paragraf, pasal, and ayat with
  stable section IDs, original order, page/line anchors, hierarchy, OCR normalization,
  parser version, and explicit `needs_review` state.
- Live publication yields 274 sections for UU 27/2022, 427 for PP 71/2019, and 136 for
  Permenkominfo 20/2016 with 100% source-anchor coverage. A second run returns `unchanged`
  for all three and reuses their immutable dataset-version IDs.
- Draft PR [#15](https://github.com/LaboNapitupulu/NusaIntel/pull/15) passes backend/PostgreSQL,
  frontend/Playwright, Compose, and security in hosted run
  [31901770812](https://github.com/LaboNapitupulu/NusaIntel/actions/runs/31901770812).

## Gate evidence

- The versioned manual benchmark passes 30/30 reviewed boundaries (100%; target ≥95%),
  including OCR normalization and a negative repeated-ayat page-boundary case.
- Database integration proves publication, raw/section persistence, idempotency,
  rejected-candidate quarantine/incident evidence, relation exposure, and preservation of
  the published version.
- Clean-stack migration creates 22 domain tables at `20260816_0004`; backup/restore recreates
  the same schema and Gold view in an isolated scratch database.
- Final hosted CI and merge evidence are recorded in `docs/progress-log.md`.
