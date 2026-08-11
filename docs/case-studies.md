# Phase 6 evidence case studies

## 1. Critical data-quality incident preserves last-known-good Gold

The isolated smoke case replays the public TPT fixture through a freshly migrated scratch
database. A valid payload publishes 117 Gold observations and an identical replay is
idempotent. The case then replaces source key `11005430123190` with the nonnumeric string
`invalid`.

Observed outcome:

| Evidence | Result |
|---|---|
| Valid payload | `published` |
| Identical replay | `unchanged` |
| Invalid payload | `rejected` |
| Failed checks | 2 |
| Incidents | `coverage_2023` and `numeric_values_valid`, both critical |
| Gold version for invalid input | None |
| Last-known-good Gold rows | 117, unchanged |

The rejection is fail-closed: evidence and incidents are retained, while the invalid
candidate never becomes a Gold version. Reproduce it with:

```powershell
.\scripts\quality_incident_smoke.ps1
```

The script uses the Compose network, operates only on
`nusa_intel_quality_case_smoke`, and removes that scratch database in `finally`.

## 2. Ranking changes when weights change

The public 2024 scenario compares DKI Jakarta, Bali, Jawa Timur, Nusa Tenggara Timur, and
Papua using all six indicators, min-max normalization, complete coverage, equal base
weights, and a 50% sensitivity perturbation.

Base ranks:

| Rank | Region | Score |
|---:|---|---:|
| 1 | Bali | 60.658683 |
| 2 | DKI Jakarta | 54.929700 |
| 3 | Jawa Timur | 45.234567 |
| 4 | Nusa Tenggara Timur | retained in evidence response |
| 5 | Papua | retained in evidence response |

Two scenarios reverse the top pair:

- Increasing the PDRB-per-capita weight from 16.666667% to 23.076923% moves DKI Jakarta
  from rank 2 to rank 1 and Bali from rank 1 to rank 2.
- Decreasing the TPT weight from 16.666667% to 9.090909% produces the same reversal.

Across all 12 perturbation scenarios, DKI Jakarta and Bali each retain their base rank in
83.333333% of scenarios and span ranks 1–2. The other three regions stay at their base rank.
This is the intended product message: the ranking is conditional on declared weights. The
sensitivity range is not a confidence interval and does not imply causality.
