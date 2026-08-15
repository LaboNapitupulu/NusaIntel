# Privacy and security

## Data classification

NusaIntel MVP processes public aggregate BPS statistics and operational metadata. It does
not require accounts, personal profiles, cookies, precise user location, or individual-level
records. Scenario URLs contain public region/indicator codes and method parameters only.

Secrets are limited to infrastructure credentials and the BPS API key. They belong in local
`.env` files or a deployment secret manager and must never enter browser bundles, logs,
fixtures, reports, screenshots, or Git history.

## Threats and controls

| Threat | Control |
|---|---|
| Secret committed or logged | `.gitignore`, backend-only variable, structured safe logging, Gitleaks CI |
| Vulnerable dependency | Pinned runtime packages, `pip-audit`, `npm audit --audit-level=high` |
| Malformed/unexpected API input | Strict Pydantic schemas, forbidden extra fields, bounded list/number limits |
| Source payload drift or corruption | Size/time/retry limits, checksum, contracts, quarantine, schema drift, critical gate |
| SQL injection | SQLAlchemy expressions and fixed service queries; no user-supplied SQL |
| Browser script/content injection | React escaping, JSON-only exports, no arbitrary HTML rendering, security headers |
| Cross-origin misuse | Explicit CORS allow-list; no credentialed CORS |
| Denial by expensive analytics | Max 6 features, 10 results/seeds, 5 candidate k values, fixed 38-region universe |
| Misleading output | Null-preserving logic, version/source context, validation withholding, limitations |
| Database loss | Named volume, custom-format backup, isolated restore smoke, forward migration policy |
| Duplicate scheduled ingestion | Disabled-by-default scheduler, bounded cadence, PostgreSQL advisory lock |

## Browser and API policy

- Only variables prefixed `NEXT_PUBLIC_` may enter the frontend build; no secret uses that
  prefix.
- Responses contain public aggregates and provenance, not internal connection strings or
  stack traces.
- `httpx` and `httpcore` request logging is forced to WARNING because the BPS credential is
  a query parameter; scheduled logs contain only safe status, indicator, and run IDs.
- The MVP has no authorization boundary because all product data is public and read-only;
  incident mutation endpoints are deployment-admin functionality and must be protected by
  an upstream access layer before public internet exposure.
- Production deployments should terminate TLS at a trusted proxy, restrict PostgreSQL to a
  private network, enforce request/body limits, and add rate limiting at the edge.

## Retention and deletion

Immutable versions/checks/incidents are audit evidence and should follow an explicit
deployment retention policy. Raw payloads contain public aggregate data but may be large;
archive or expire them only after lineage and reproducibility requirements are met. Backup
retention and secure deletion are deployment-owner responsibilities.

## Verification

CI runs Gitleaks over full history, Python and npm dependency audits, strict typing/linting,
unit/integration tests, Compose build, E2E at desktop/360px, and automated accessibility
checks. Findings rated high/critical block release unless documented with owner and expiry.
Rotate any credential that has appeared in a terminal, container, CI, screenshot, or chat
log even after the logging defect is fixed.
