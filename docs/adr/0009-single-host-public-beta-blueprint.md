# ADR 0009 — Use a single-host, edge-only Compose blueprint for the first public beta

- Status: Accepted
- Date: 2026-08-23

## Context

The application already runs as PostgreSQL, a migration job, API, worker, and web service.
The first beta needs a reproducible production topology before any paid infrastructure or DNS
change is authorized. The audience is expected to be small, so Kubernetes and multi-region
state would add operational cost without solving a measured problem.

Two credible low-operations paths were reviewed on 2026-08-23:

- Railway Hobby starts at USD 5/month including USD 5 of usage, offers a Singapore region and
  private networking, but the final bill remains usage-based across the continuously running
  API, worker, web, and database services.
- A small VPS provides a predictable single-host boundary. As a price reference rather than a
  provider commitment, Hetzner lists a 4 vCPU/8 GB CX33 in Germany/Finland at USD 9.99/month
  excluding VAT and IPv4 after its 15 June 2026 adjustment; its Singapore plans cost materially
  more.

Pricing links are snapshots, not guarantees:

- <https://docs.railway.com/pricing>
- <https://docs.railway.com/deployments/regions>
- <https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/>

## Decision

The repository will ship a provider-neutral, single-host Docker Compose blueprint. Caddy is the
only service publishing host ports and manages automatic HTTPS. PostgreSQL, migrations, API,
worker, and web remain unbound from the host. Separate internal edge/data networks restrict
lateral access; only the worker and Caddy receive outbound networking for BPS and ACME.

The production contract additionally requires:

- a commit-derived application image tag;
- a 32+ character URL-safe database password;
- distinct public frontend/API DNS names;
- read-only application filesystems and disabled privilege escalation;
- a 2 MB public request-body ceiling;
- public denial of quality-exception and incident mutation routes;
- persistent PostgreSQL and Caddy state volumes.

The first deployment is intentionally one API process. Its bounded application quota is
therefore globally consistent for that instance, although Caddy still does not provide a
distributed rate limiter. Moving to multiple API replicas requires a trusted-client-IP design
and a shared or provider-edge limiter before scaling.

## Consequences

- The same reviewed artifact can run on any Linux VPS with Docker Compose.
- Only ports 80/TCP, 443/TCP, and 443/UDP are public; the database has no published port.
- Caddy can obtain and renew certificates only after both DNS records point to the server and
  the public firewall permits ports 80/443.
- Host patching, encrypted off-host backups, monitoring, and restore drills remain operator
  responsibilities.
- Provider, region, domains, owner, budget, RPO, and RTO still require explicit approval before
  provisioning. This ADR authorizes a topology, not a purchase or deployment.
