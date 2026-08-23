# Phase 11 status — Deployment blueprint

- Date: 2026-08-23
- Branch: `codex/phase-11-deployment-blueprint`
- Status: implementation complete; hosted CI and merge pending

## Outcome

NusaIntel now has a production-only Compose topology with Caddy automatic HTTPS, isolated
application/data networks, persistent state, immutable candidate tags, and no direct host port
for PostgreSQL, API, worker, migrations, or web. Administrative Control Tower mutations and
the interactive API schema are denied at the public edge.

## Acceptance evidence

| Gate | Target | Result |
|---|---|---|
| Published services | Caddy only | Pass — topology validator enforces the exact service set |
| Public ports | 80/TCP, 443/TCP, 443/UDP only | Pass |
| Database reachability | Internal data network, no host port | Pass |
| Candidate identity | Explicit non-`latest` image tag | Pass |
| Container hardening | Read-only app roots and no privilege escalation | Pass |
| Edge controls | HTTPS, 2 MB body ceiling, admin mutations denied | Pass |
| CI contract | Rendered Compose and Caddy syntax checked | Added; hosted run pending |
| Real deployment | Provider/DNS/owner/budget/recovery approved | Pending owner decision |

## Boundaries

This phase does not provision a server, buy a domain, change DNS, create a paid account, or
claim public availability. The BPS credential previously exposed to local command output must
be rotated before it can be placed in any deployment secret store.
