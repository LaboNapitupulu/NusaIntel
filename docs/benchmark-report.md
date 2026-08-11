# Benchmark report

- Environment: see `docs/benchmark-environment.md`
- Release candidate: Phase 6 baseline after merge commit `a0b2e07`
- Updated: 2026-08-11

| Capability | Target | Recorded evidence |
|---|---:|---:|
| Six-contract execution | < 60 s | 0.7787 s hosted integration baseline |
| Pipeline dry-run success | ≥ 95% | 30/30 (100%) |
| Dataset-health API p95 | < 500 ms | 76.36 ms over 30 calls |
| Opportunity score, 38 regions p95 | < 500 ms | 1.267 ms deterministic engine fixture |
| Regional full report p95 | < 500 ms | Pass; enforced across five hosted PostgreSQL calls |
| Hidden zero imputation | 0 | 0 across score/similarity tests |
| Critical engine branch coverage | ≥ 85% | 88.83% local Phase 6 baseline |
| Desktop/360px critical journey | Pass | 4/4 Playwright cases |
| Serious/critical axe findings | 0 | 0 after contrast/focus remediation |
| Empty-database migration | Pass | 17 domain tables + Gold view at `20260811_0003` |
| Backup/restore recovery | Pass | 17 domain tables + Gold view restored in scratch DB |
| Dependency vulnerabilities | 0 known | `pip-audit` and `npm audit`: 0 known findings |

## Reproduction

Run `scripts/verify_release.ps1 -SkipSecurityAudit` from a dependency-complete checkout.
This executes Ruff, format, strict Mypy, critical-engine branch coverage, frontend lint/type
and component tests, production build, desktop/360px Playwright journeys, axe scan, and
Compose configuration validation. Without the switch it also performs dependency audits.

Database benchmarks run in the CI backend job with PostgreSQL 17 and `RUN_DB_TESTS=1`.
Measurements are regression gates, not a cloud capacity forecast. Browser timings use a
deterministic mocked public API so layout/accessibility failures are isolated from network
variance; populated-stack smoke remains a separate release check.

The populated stack and clean-stack smoke both passed on 2026-08-11. The clean test used an
isolated Compose project and empty volume, verified PostgreSQL migration, API and web health,
then removed only its disposable resources. Backup restore was verified separately against
the primary local stack without overwriting its database.
