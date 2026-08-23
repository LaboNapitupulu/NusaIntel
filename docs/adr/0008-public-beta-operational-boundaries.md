# ADR 0008 — Put public-beta operational boundaries at both application and edge

- Status: Accepted
- Date: 2026-08-23

## Context

Phase 9 satisfies the product and grounding gates, but a public service also needs distinct
orchestrator probes, host/origin restrictions, response hardening, abuse controls, and a
repeatable configuration check. The repository does not yet have an approved hosting provider,
domain, budget, or distributed gateway.

## Decision

The API exposes dependency-free `/live` and PostgreSQL-aware `/ready`, retains `/health` for
compatibility, rejects unsafe production CORS/host configuration, and emits security headers.
Grounded-answer requests receive a bounded per-process fixed-window quota in addition to the
existing input, timeout, and concurrency controls. Quota state is memory-bounded and returns
HTTP 429 with `Retry-After` and visible rate-limit headers.

TLS termination, forwarded-client identity, globally consistent quotas, WAF controls, and
certificate rotation remain at a trusted deployment edge. The local limiter intentionally
uses the direct peer address and must not be presented as a distributed control.

## Consequences

- A single-process deployment has useful defense in depth before a gateway is configured.
- Multi-replica deployments must add a shared/edge limiter; per-process limits multiply with
  replicas and proxy peers may otherwise share one bucket.
- Production configuration fails early when only local hosts, wildcard hosts, HTTP browser
  origins, or a non-HTTPS public frontend API URL are supplied.
- No production deployment is claimed until infrastructure decisions and post-deploy evidence
  exist.
