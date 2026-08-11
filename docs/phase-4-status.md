# Phase 4 status — Regional Opportunity Engine core

- Status: Complete; merged
- Date: 2026-08-11
- Branch: `codex/phase-4-opportunity-engine`
- Release target: `0.3`

## Outcome

Phase 4 adds a transparent regional comparison and scoring workflow on the published Gold
data. Users can compare two to five provinces, inspect raw and normalized observations,
control weights and favorable direction, exclude regions below a visible coverage threshold,
inspect per-indicator contributions, test rank sensitivity, share a scenario URL, and export
a version-bound evidence package.

## Delivered scope

- Catalog API with definition, unit, favorable direction, source, coverage, quality, and
  immutable Gold version metadata.
- Comparison API with indicator-specific reference periods, trends, distributions, and
  explicit unit compatibility checks.
- Min-max and percentile normalization with deterministic tie and constant-series handling.
- Coverage gate with no silent zero imputation and transparent effective-weight
  renormalization when partial coverage is allowed.
- Score, rank, contribution, sensitivity, source, methodology, share, and JSON export flows.
- Responsive UI with loading, empty, error, ineligible, chart, and table-alternative states.

## Exit-gate evidence

| Gate | Result | Evidence |
|---|---|---|
| Reviewer can reproduce a score | Pass | Hand-calculated fixture yields 100, 50, and 0 with matching contributions |
| Ranking exposes contribution and methodology | Pass | Score response and drawer expose raw/normalized values, weights, source, period, and version |
| UI refuses insufficient coverage | Pass | Ineligible region has null score/rank and is rendered as `Tidak diranking` |
| Export contains version and configuration | Pass | Server JSON includes methodology/configuration, version/checksum, sources, ranking, and sensitivity |

## Benchmarks

| Metric | Target | Local result |
|---|---:|---:|
| Scoring reproducibility | 100% | 100% |
| All 38-region scoring p95 | < 500 ms | 1.267 ms in the deterministic engine fixture |
| Hidden imputation | 0 | 0 |
| MVP indicator source metadata | 100% | 6/6 |
| Normalization/scoring branch coverage | ≥ 90% | 95% via Python trace |

## Verification

- Backend Ruff, format, strict Mypy pass; 48 unit/API tests pass locally.
- PostgreSQL integration passes in the hosted CI database job; local Docker/browser rerun
  remains optional and requires a fresh explicit execution approval.
- Frontend ESLint, TypeScript, six component tests, and production build pass locally.
- Hosted CI run [31457229496](https://github.com/LaboNapitupulu/NusaIntel/actions/runs/31457229496)
  passes backend/PostgreSQL, frontend, Compose build, and security jobs.

## Pull request

- [PR #12](https://github.com/LaboNapitupulu/NusaIntel/pull/12)
- Hosted implementation commit: `dbd2fd353f8dfe62f5eb4af0094bd8b97268766d`
- Merge commit: `248bc93b7f342a480c933f5f1dc35a4a047720c2`

## Limitations

- Rankings cover the selected provinces and assumptions; they are not investment advice.
- Sensitivity varies weights only and does not model source uncertainty or causal effects.
- Share links encode configuration in the URL and are not durable server-side workspaces.
- Phase 5 will add richer geographic exploration and reporting.
