# MVP release scorecard

- Candidate branch: `codex/phase-6-mvp-hardening`
- Evaluated: 2026-08-11
- Status: conditional — technical gates pass; BPS key rotation and README screenshots remain

## PRD Section 4.3

| Criterion | Status | Evidence |
|---|---|---|
| Six indicators, three periods, available provinces | Pass | 6 contracts, 702 Gold observations, explicit source-unavailable handling |
| Contracts and ≥95% release quality checks | Pass | 18/18 datasets contracted; 36/36 populated release checks pass |
| Retrieval/reference visibility | Pass | Control Tower, Opportunity, regional detail, and exports include both timestamps/periods |
| Reproducible score | Pass | deterministic engine and row-order/version tests |
| Read API p95 <500 ms | Pass | health 76.36 ms; scoring 1.267 ms; report gate <500 ms |
| Main dashboard usable <3 s | Pass | warm homepage HTTP p95 62.37 ms; production E2E journeys pass |
| No critical automated accessibility finding | Pass | axe serious/critical count 0 on desktop and 360 px |
| Critical business coverage ≥80% | Pass | 88.83% branch coverage |
| Pipeline reliability ≥95% over 30 runs | Pass | 30/30 dry runs |
| README-only clean setup | Pass | disposable empty-volume Compose smoke follows documented commands |

## PRD Section 18.1

| Gate | Status | Evidence |
|---|---|---|
| Section 4.3 criteria | Pass | table above |
| Scheduled BPS connector | Pass | TPT scheduler completed with `unchanged`; 5-minute smoke interval, advisory lock guard |
| Critical check stops Gold | Pass | isolated invalid-value case creates two critical incidents and no invalid Gold version |
| Comparison/scoring/explanation/sensitivity | Pass | API, UI, export, deterministic tests, sensitivity case study |
| Methodology/source metadata visible | Pass | UI, reports, exports, methodology docs |
| Compose services healthy together | Pass | PostgreSQL, migrations, API, worker, web |
| CI quality/security jobs | Pending head rerun | prior PR #14 head passed; rerun required after this tranche |
| Safe public demo | Pass | checked-in/public BPS fixtures and published aggregate statistics only |
| Release documentation | Conditional | architecture, dictionary, limitations complete; README screenshots pending |

## Security disposition

During scheduler smoke, HTTP transport INFO logging exposed a credential-bearing request URL
in local container output. The application now forces `httpx` and `httpcore` to WARNING,
tests the logger threshold, and a second scheduled smoke confirms no request URL or `key=`
query appears. The affected BPS key must still be regenerated before release promotion.
