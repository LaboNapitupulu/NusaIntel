# Phase 10 status — Public beta hardening

- Status: Local exit gate passed — hosted CI and infrastructure decisions pending
- Date started: 2026-08-23
- Branch: `codex/phase-10-public-beta-hardening`
- Baseline: Phase 9 merge commit `6bd5c87`

## Delivered

- Separate liveness and readiness probes.
- Production HTTPS CORS and trusted-host fail-closed validation.
- Security/no-store headers and bounded grounded-answer rate limiting.
- Non-secret environment template and production configuration preflight.
- Deployment, smoke, rollback, and edge-control contract.

## Remaining gate

- Pass hosted CI and merge.
- Rotate the exposed BPS key before any public deployment.
- Select real provider/domain/owner/budget/RPO/RTO and execute post-deploy smoke; this is an
  infrastructure decision, not a local implementation assumption.

## Local evidence

- Backend: 92 passed, 3 environment-gated integration skips, 88.83% critical coverage.
- Frontend: lint/typecheck, 10 component tests, production build, and 6 desktop/mobile E2E
  journeys including accessibility pass.
- Phase 9 benchmark remains passing: Recall@10 0.8917, citation correctness/coverage 1.0,
  refusal 0.95, fabricated citation 0, version accuracy 0.90, p95 0.0262 seconds.
- Built container smoke: liveness/readiness 200, database ready, security headers present,
  untrusted host rejected with 400.
- Python/npm dependency audits: no known vulnerabilities.
