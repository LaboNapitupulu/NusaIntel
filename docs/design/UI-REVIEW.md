# NusaIntel UI review

Scope: home, shared navigation, data-quality workspace, scenario comparison, regional analysis, regional detail, regulation search and version comparison, loading/error/empty states, light/dark themes, and mobile layouts.

Skills: [UI UX Pro Max](../../../.agents/skills/ui-ux-pro-max/SKILL.md) and [anti-slop](https://github.com/miqdadbadjuber/anti-slop/tree/439a2ef5b9dd0ebe74e8113ff43f5928d0fe2a6a). Anti-slop mode: during. Visual reasons and dials are in [UI-DIRECTION.md](UI-DIRECTION.md).

## What changed

- Replaced accumulated CSS overrides with one shared token and component system. Kept the existing paper/teal identity and Indonesian language.
- Removed the graphic logo cube, rotating scene, pointer tilt, animated counters, repeated marketing slogans, static catalog counts, and the unsupported 100% answer guarantee.
- Added explicit tab/panel relationships, keyboard tab switching, mobile-menu Escape behavior, visible focus, storage-failure tolerance, readable mobile inputs, and locally scrollable tables/maps.
- Fixed dataset reselection getting stuck in loading; added detail retry, a missing-health filter, complete fetched check lists, and incident submission feedback.
- Refresh comparison, score, and sensitivity together after scenario changes. Stale results and exports stay unavailable until the new configuration finishes. Perturbation changes now participate in the result fingerprint.
- Replaced the invented similarity percentage with the actual standardized profile distance, matching docs/regional-analytics-methodology.md. Map clicks inspect values without discarding the report. Cluster descriptions and limitations come from the API.
- Regulation questions start empty with an explicit example placeholder. Catalog/version/context failures are visible; version selection clears stale comparisons; source links and citation focus are usable.
- Regional detail remounts on code/year changes, supports retry, and provides the main-content anchor. Error and not-found pages use Indonesian copy.

## Verification and boundaries

- Production build: passed, all seven route entries generated/compiled.
- ESLint and TypeScript: passed.
- Vitest: 12 passed in seven files.
- Playwright: final non-updating verification is recorded in `artifacts/ui-review/e2e-verified.log`. The suite covers 32 executed cases; eight desktop-only screenshot cases are intentionally skipped by the mobile project, whose interactive journeys still run.
- Axe: no serious or critical violations in the exercised quality, comparison, regional map, and regulation evidence/compare screens, including both themes. This is automated coverage of those states, not a claim of a full assistive-technology certification.
- Desktop viewport: 1440 x 1000. Mobile viewport: 360 x 800. Screenshot baselines use a 0.1% pixel-difference limit with 0.1 pixelmatch threshold.
- Local API port 8000 was unavailable. Successful data journeys use deterministic test-only API fixtures; production has no fabricated fallback data. Backend computation, live source availability, and remote deployment were not certified by this UI work.
- Preview server: http://127.0.0.1:3101. API-dependent pages show their real error/retry states while the backend is offline.

## Recorded interaction coverage

| Area | Actions and observed outcomes | Evidence |
| --- | --- | --- |
| Navigation | Directory exposes four real routes; active navigation changes; mobile menu opens/closes; Escape returns focus; theme label/state persists | navigation-journey.spec.ts, site-header.test.tsx |
| Home | Health failure and retry; storage-blocked theme toggle; guide dismissal and persistence | workspace-journey.spec.ts, system-status.test.tsx, getting-started-guide.test.tsx |
| Data quality | Failed detail retries; selecting the same dataset preserves detail; search and health/status/severity filters change results; empty resolution disables submit; mocked resolution updates the incident | workspace-journey.spec.ts, control-tower.test.tsx |
| Scenario setup | Region/indicator checkboxes, next-step controls, normalization, all preset buttons, numeric weight validation, keyboard slider adjustment, and year selection | workspace-journey.spec.ts, opportunity-engine.test.tsx |
| Scenario output | All result tabs; arrow-key tab switching; comparison and sensitivity refresh with scores; sharing updates URL; download emits JSON; print exposes report sections | workspace-journey.spec.ts |
| Regional report | Run analysis, inspect tile without losing report, expand table with 38 fixture rows, all result tabs, share configuration, download JSON, open source-aware regional detail | regional-journey.spec.ts, regional-analytics.test.tsx |
| Regulation | Empty question validation; submit; insufficient-evidence response; citation navigation/focus; official-source href; open/close context; compare versions; inspect added/removed/modified text; equal-version comparison disabled | regulation-journey.spec.ts, regulation-lens.test.tsx |
| External links | Existing feedback URL retained; source URLs continue to come from API data. Tests inspect destinations; no feedback message or external write was submitted | layout.tsx, regional/regulation journey assertions |

Screenshots of populated fixtures are in `artifacts/ui-review/`, named by module, theme, and viewport width. Committed shell baselines are in `frontend/e2e/visual-regression.spec.ts-snapshots/`. Fixture values are test data, not public statistics for reuse.

## Anti-slop delivery gate

### Block 1: Hard gate

- R-02 PASS: source scan of app and production components found no em dashes.
- R-03 PASS: browser journeys assert page width does not exceed viewport width; wide tables and the schematic map scroll inside labeled containers.
- R-17 PASS: removed static 21-source/38-province/3-document marketing counts; displayed counts come from loaded collections or reports.
- R-18 PASS: no testimonials, fabricated people, or avatars are present.
- R-23 PASS: retained the existing wordmark and four route destinations; removed the graphic badge and scene; created no new logo or visual asset.
- R-24 PASS: all four navigation destinations are existing built Next.js routes, exercised by browser journeys.
- R-25 PASS: token foreground/background pairs and both-theme populated screens were checked by Axe; serious/critical contrast findings were absent in tested states.
- R-26 PASS: controls have implemented handlers/destinations; unavailable actions are disabled with contextual explanations; recorded actions are listed above.
- R-27 PASS: loading, empty, offline, detail failure, catalog failure, version failure, and insufficient-evidence paths render explicit feedback; retry paths exist where applicable.
- R-28 PASS: there is no generic FAQ section.
- R-32 PASS: focus outlines, skip link, native form controls, roving tab focus, labeled scroll areas, and mobile Escape behavior are implemented; keyboard journeys pass.
- R-33 PASS: changes were authored as source patches or direct file contents; no external string-rewriting script generated features.
- R-34 PASS: light/dark share semantic tokens; both-theme browser journeys and separate screenshot baselines cover layout and controls.
- R-35 PASS: production build and component/browser runs completed; interaction records above and screenshots document the exercised controls. External URLs were checked as links without sending messages.
- R-36 PASS: removed unsupported answer guarantee and all-features-ready claim; health copy describes service connectivity only.
- R-37 PASS: the existing editorial palette/type provided direction, refined through the documented design read and 1/2/1 dials.
- R-38 PASS: production reads API data and shows failures honestly; synthetic figures exist only in explicitly marked test fixtures.

### Block 2: Purpose gate

- R-01 PASS: no gradients or glow effects in the authored stylesheet.
- R-04 PASS: no generic icon library; the single theme symbol accompanies a visible mode label.
- R-06 PASS: existing serif gives editorial hierarchy; sans-serif controls and tabular numerals support reading. No wide-tracked uppercase labels or large monospace decoration.
- R-07 PASS: no background grid; the province grid represents actual schematic data positions and is labeled accordingly.
- R-08 PASS: no decorative arrows appended to navigation or actions.
- R-09 PASS: small rectangular status labels carry real health/document status; there are no marketing capsules above headings.
- R-10 PASS: no glassmorphism or backdrop blur.
- R-12 PASS: the only shadow belongs to the floating notification, separating feedback from underlying content.
- R-13 PASS: no glow layer on controls, borders, cards, or backgrounds.
- R-14 PASS: the four equal directory links represent equally available tasks; configuration, metrics, tables, and evidence use layouts appropriate to their content.
- R-19 PASS: no scroll reveal, tilt, or number tweening; short hover feedback is disabled for reduced motion.
- R-22 PASS: removed the unrelated 3D scene; added no stock or generated illustration.

### Block 3: Liveliness

- Dials PASS: ENERGY 1 / RHYTHM 2 / MOTION 1 are explicit in UI-DIRECTION.md.
- Consistency PASS: restrained colors and controls carry across routes; data tables, map, and source reading create purposeful layout variation.
- Focal point PASS: page title establishes the task; within each active result view, the ranking, map, or citation is the principal content.
- Whitespace PASS: spacing separates setup from results and sources, while tables remain compact; desktop/mobile screenshots were reviewed.
- Accent PASS: teal identifies links, selected tabs, primary actions, and data marks. Warning/error colors are reserved for status.
- Identity PASS: paper surfaces, serif titles, and ruled data sections repeat the existing editorial identity without a decorative badge.
- Design read PASS: the early decision to retain Indonesian copy and the existing paper/teal identity is recorded in UI-DIRECTION.md and guides the final refinements.

### Block 4: Craftsmanship and quality locks

- C-1 PASS: palette, typography, spacing, containers, icons, and motion each have a written product-specific reason.
- C-2 PASS: functional journeys and native-control behavior are recorded above; disabled controls explain unavailable actions.
- C-3 PASS: removed the repetitive three-step marketing strip; remaining sections serve dataset inspection, comparison, map reading, or source verification.
- C-4 PASS: tested both themes and two viewports; failures, blocked storage, keyboard navigation, and missing values remain usable.
- C-5 PASS: no invented production testimonials, figures, or capability guarantees.
- R-05 PASS: home is a task directory; internal layouts follow data and source-reading needs rather than a reusable marketing template.
- R-11 PASS: rectangular controls, small-radius panels, and compact status labels replace pill styling.
- R-15 PASS: actions name outcomes, including Hitung skenario, Muat ulang rincian, Bandingkan versi, and Buka konteks.
- R-16 PASS: UI copy contains no AI marketing buzzwords or unsupported superlatives.
- R-20 PASS: provincial indicators, schematic geography, data quality, and legal citations shape the interface's structure and language.
- R-21 PASS: light mode remains the default; the existing dark-mode choice works and persists when storage is available.
- R-29 PASS: neutral paper/ink with teal accent; warning/error status colors and the single-hue map scale have defined semantic roles.
- R-30 PASS: extended the product's existing identity rather than cloning a third-party product.
- R-31 PASS: one-line reasons are recorded in UI-DIRECTION.md, including the directory and bordered result panels.
