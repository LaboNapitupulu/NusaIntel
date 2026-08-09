# Phase 2 Status — Complete

- Date: 2026-08-09
- Status: Complete; hosted CI passed on the pull request and merged `main`
- Migration head: `20260809_0002`

## Delivered

The six-indicator ingestion path retrieves TPT, TPAK, poverty, PDRB per capita,
PDRB growth, and HDI from BPS. It stores each exact response and safe request
metadata in Bronze, normalizes the 38-province contract plus national aggregate
in Silver, and publishes Gold only after all critical checks pass. Credentials
are never included in stored URLs, parameters, errors, or command output.

The composite BPS keys are decoded by generating combinations from response
metadata. No fixed-width key slicing is used. Missing, invalid, and observed
values remain distinct; invalid data is never coerced to zero.

## Reproducible evidence

| Check | Result |
|---|---:|
| Raw BPS observations | 768 |
| Normalized/Gold contract rows | 702 |
| Observed values | 651 |
| Explicit missing values | 51 |
| Quarantined values | 0 |
| Critical quality failures | 0 |
| Dataset versions after two identical live runs | 18 (six per layer) |
| Pipeline runs after two identical live runs | 6 |
| Lineage edges | 12 |
| Fresh migration | Empty database → `20260809_0002`, 15 application tables |
| Failure injection | Invalid numeric rejected; existing 117-row Gold remained unchanged |

TPT, TPAK, and poverty cover `34/38` provinces in 2023 and `38/38` in 2024–2025.
Both PDRB indicators cover `38/38` for all three years. IPM method-new variable
`494` covers `38/38` for 2023–2024; WebAPI does not expose its 2025 period, so
the 38 province cells and national aggregate remain explicit `missing` values.

## Commands

Start or upgrade the stack:

```powershell
docker compose up --build --detach
```

Run live ingestion:

```powershell
.\scripts\run_tpt_pipeline.ps1
```

Run all six live contracts:

```powershell
.\scripts\run_bps_pipeline.ps1
```

Run against the immutable fixture:

```powershell
.\scripts\run_tpt_pipeline.ps1 -Fixture
```

## Failure and recovery

- Retrieval/configuration failure exits before transformation; the last
  published Gold version remains available.
- Invalid values, unknown regions, duplicate keys, or coverage below contract
  create a rejected Silver run and do not create or replace Gold.
- A retry is safe. The Bronze, Silver, and Gold version identities are protected
  by source identity plus checksum; identical input returns `unchanged`.
- Inspect `ops.pipeline_runs`, `ops.quality_check_results`, and
  `ops.quarantine_records` to diagnose a rejected run. Do not edit a published
  dataset version in place; correct the contract/code or obtain a corrected
  source response, then run again.
- Database schema recovery uses `alembic upgrade head`. Destructive volume reset
  is unnecessary and should only be used intentionally for disposable local data.

## Benchmark

Three sequential live connector-plus-normalization runs completed in `5.555`,
`5.539`, and `5.576` seconds; median `5.555` seconds. All six normalized
checksums remained identical across runs. See `docs/benchmark-environment.md`.

## Hosted verification

- Pull request [#7](https://github.com/LaboNapitupulu/NusaIntel/pull/7)
  passed backend, frontend, security, and Compose checks in GitHub Actions run
  [`31288960900`](https://github.com/LaboNapitupulu/NusaIntel/actions/runs/31288960900)
  for commit `d36c890`.
- The merged `main` branch passed the same four jobs in run
  [`31289068592`](https://github.com/LaboNapitupulu/NusaIntel/actions/runs/31289068592)
  for merge commit `49962b1`.

Phase 2 has no remaining implementation or verification item. Phase 3 can
start from the verified `main` branch after repository dependency hygiene.
