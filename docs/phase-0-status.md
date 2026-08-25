# Phase 0 Status

- Started: 2026-08-08
- Last updated: 2026-08-25
- Status: complete; carried risks reconciled against Phases 2–12

## Decisions completed

- [x] Repository name confirmed as `nusa-intel`.
- [x] Planned as a public portfolio repository after hardening.
- [x] MVP geography selected: 38 provinces.
- [x] Comparison window selected: 2023–2025.
- [x] Six MVP indicators selected.
- [x] Source URLs and reference-period risks documented.
- [x] PostgreSQL schema strategy selected.
- [x] Pandas selected with explicit revisit thresholds.
- [x] Lightweight worker scheduling selected; Prefect deferred with revisit triggers.
- [x] MapLibre GL JS selected with local province GeoJSON.
- [x] Initial logical ERD completed.
- [x] Architecture decisions recorded in ADR-0001.
- [x] Documentation-derived BPS fixture validated offline.
- [x] Live BPS endpoint reached and missing-key behavior captured unchanged.
- [x] BPS API key configured locally and confirmed ignored by Git.
- [x] Authenticated domain, period, subperiod, and TPT data requests completed.
- [x] Unchanged live TPT response captured and decoded offline.
- [x] TPT 2023 coverage limitation for four new Papua provinces documented.

## Authenticated discovery result

- [x] Obtain a BPS WebAPI token from <https://webapi.bps.go.id/developer/>.
- [x] Configure it locally as `BPS_API_KEY` without committing it.
- [x] Run authenticated domain/variable/period discovery for TPT.
- [x] Capture one unchanged response-body fixture for an MVP indicator.
- [x] Record the six live BPS variable IDs and period IDs.

TPT is verified as variable `543`. Period IDs are 2023=`123`, 2024=`124`,
and 2025=`125`; August is derived-period `190`. The annual derived period
(`191`) returned `list-not-available`, so the comparable series uses August.
The response contains 113/117 expected cells (96.58%). Four new Papua
provinces have no separate 2023 observation; 2024 and 2025 each contain all 38
provinces plus the Indonesia aggregate.

## Exit gate

| Gate | Result | Evidence |
|---|---|---|
| Six indicators have source, definition, unit, direction, and coverage evidence | Pass | `indicator-selection.md` and `source-inventory.md` |
| One API-shape fixture can be parsed without live network access | Pass | `tests/fixtures/bps/` and `spikes/parse_bps_fixture.py` |
| No unresolved decision blocks Phase 1 scaffolding | Pass | ADR-0001 |

## Carried risks and disposition

1. Five remaining indicator IDs and dimensions were verified and fixture-backed in Phase 2.
2. Official rate-limit guidance was not visible in the rendered public documentation reviewed during Phase 0.
3. Phase 5 selected a self-authored schematic tile map, avoiding unverified boundary redistribution.
4. Missing 2023 Papua observations remain explicit nulls; scoring never silently imputes zero.

## Next gate

No historical Phase 0 item blocks the current release. Official BPS rate-limit guidance
remains an external documentation dependency; the client retains conservative bounded
throttling and retry defaults.
