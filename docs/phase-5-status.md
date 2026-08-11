# Phase 5 status — Regional analytics, map, and reporting

- Status: Implementation complete; hosted PostgreSQL/CI verification pending
- Date: 2026-08-11
- Branch: `codex/phase-5-regional-analytics`
- Release target: `0.4`

## Outcome

Phase 5 adds deterministic similar-region search, evidence-gated clustering, a schematic
38-province tile choropleth, regional detail pages, and printable/JSON evidence reports.
Every output remains bound to the preprocessing configuration, immutable Gold versions,
units, reference periods, official source URLs, and explicit limitations.

## Delivered scope

- Complete-case z-score preprocessing with coverage filtering and no hidden imputation.
- RMS Euclidean similarity with per-feature distance drivers and row-order invariance.
- Candidate-`k` evaluation using silhouette, adjusted-Rand stability across seeds, and
  minimum membership evidence.
- Fail-closed withholding and neutral cluster descriptions.
- Versioned feature set/preprocessing plus deterministic region and cluster ordering.
- 38-province schematic tile map with quantile legend, no-data styling, keyboard buttons,
  and an equivalent table.
- Regional evidence page, browser-print layout, and context-complete JSON export.

## Acceptance evidence

| Gate | Result | Evidence |
|---|---|---|
| Similarity deterministic | Pass | Reordered fixture produces byte-equivalent results |
| Cluster evidence visible | Pass | Every candidate reports silhouette, stability, and minimum size |
| Weak clustering withheld | Pass | Constant fixture returns no assignment or description |
| Export context complete | Pass locally/unit; DB CI pending | Unit/source/version assertions added to PostgreSQL integration |
| Non-visual map equivalent | Pass | Map and 38-row table share the same response values |
| Normative labels absent | Pass | Engine and UI tests reject prohibited wording |
| Responsive implementation | Pass in CSS/build; browser smoke deferred | 360 px breakpoints and production build pass |

## Verification

- Backend: Ruff/format/strict Mypy pass; 57 tests pass and 2 PostgreSQL tests are skipped
  locally pending the hosted database job.
- Frontend: ESLint, TypeScript, 8 component tests, and Next.js production build pass.
- Production build includes the static home route and dynamic `/regions/[code]` route.
- Database integration now benchmarks five full reports and asserts 38 map values,
  deterministic similarity, cluster evidence, and citation context.

## Boundary-source decision

The current geoBoundaries Indonesia ADM1 release covers a 2017, 34-unit universe, while the
available government ArcGIS service does not declare a redistribution license in its public
metadata. Phase 5 therefore redistributes neither source. The product uses an explicitly
schematic, self-authored tile representation until a compatible licensed 38-province source
is approved. See ADR 0004.

## Remaining completion evidence

- Run the isolated PostgreSQL benchmark and all hosted CI jobs on the pull request.
- Record hosted latency and merge evidence here after CI succeeds.
- Optional live browser/Docker smoke remains outside the local verification performed in
  this branch.
