# ADR 0005 — Start RegulasiLens with personal-data protection

- Status: Accepted
- Date: 2026-08-16

## Context

RegulasiLens must begin with one bounded legal domain. Employment law has a broad,
version-sensitive surface after multiple omnibus-law changes, while education spans many
institutional levels and sectoral instruments. Both would make parser and status failures
harder to isolate in the first corpus.

Personal-data protection has one clear primary statute plus a small set of directly relevant
electronic-system rules. It still exercises the difficult requirements: multiple regulation
levels, status checks, checksum-pinned documents, external relations, and conservative legal
scope.

## Decision

The first corpus uses the `personal-data-protection` domain and begins with:

1. UU 27/2022 on Personal Data Protection.
2. PP 71/2019 on Electronic Systems and Transactions.
3. Permenkominfo 20/2016 on Personal Data Protection in Electronic Systems.

Only manifest-listed HTTPS documents from `peraturan.bpk.go.id` are approved. PDFs remain in
ignored local runtime storage; the repository retains official links, attribution, metadata,
expected byte counts, and SHA-256 checksums. A content or checksum change is quarantined until
the manifest receives a human-reviewed version bump.

Phase 7 does not provide legal advice, grounded answers, or semantic retrieval. Judicial
decisions, bills, news, commentary, and incidental sectoral references remain outside the
initial retrieval corpus.

## Consequences

- Parser and ingestion quality can be measured on a small, auditable corpus.
- The system cannot claim comprehensive Indonesian data-protection coverage.
- Official status must be rechecked every 30 days and before any public release.
- A later ADR is required before adding another domain or a second source host.
