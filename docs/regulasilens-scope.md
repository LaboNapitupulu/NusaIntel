# RegulasiLens initial corpus scope

- Domain: personal-data protection
- Corpus ID: `personal-data-protection-id`
- Manifest: `regulations/manifests/personal-data-protection.v1.json`
- Decision: ADR 0005
- Status checked: 2026-08-16

## Inclusion boundary

Include a document only when it is a national regulation from an official JDIH source and
its primary substance directly governs personal-data protection or operational data
protection in electronic systems. The official metadata page and PDF must both be reachable
over HTTPS, and the document must have a reviewed status, byte count, and SHA-256 checksum.

Exclude commentary, news, third-party copies, bills, court decisions, incidental sectoral
mentions, and any document with unresolved identity or status. External legal references may
be recorded as unresolved graph evidence but do not silently enter the corpus.

## Initial source set

| ID | Instrument | Status on source | Why included |
|---|---|---|---|
| `uu-27-2022` | UU 27/2022 — Pelindungan Data Pribadi | In force | Primary national personal-data statute |
| `pp-71-2019` | PP 71/2019 — Penyelenggaraan Sistem dan Transaksi Elektronik | In force | Operational electronic-system data obligations |
| `permenkominfo-20-2016` | Permenkominfo 20/2016 — Perlindungan Data Pribadi Dalam Sistem Elektronik | In force | Specific operational personal-data rule |

Official metadata:

- <https://peraturan.bpk.go.id/Details/229798/uu-no-27-tahun-2022>
- <https://peraturan.bpk.go.id/Details/122030/pp-no-71-tahun-2019>
- <https://peraturan.bpk.go.id/Details/150543/permenkominfo-no-20->

The UU 27/2022 page also exposes judicial-review evidence. The initial manifest retains the
portal's `in_force` status while keeping court decisions outside the regulation corpus; any
answer or comparison feature remains blocked until later phases model that evidence safely.

## Source use and attribution

Database Peraturan BPK states that it is part of JDIH BPK's effort to disseminate legal
information accurately and accessibly. This does not by itself grant NusaIntel permission to
republish a bulk document mirror. Therefore Phase 7 uses a link-and-local-cache-only policy:

- request only manifest-listed files, sequentially and without crawling;
- identify the client, use bounded timeouts, and do not retry aggressively;
- keep downloaded PDFs under ignored `data/regulations/` runtime storage;
- display source attribution and link back to the official metadata page;
- quarantine changed content until a human rechecks metadata and versions the manifest.

## Status vocabulary

| Value | Meaning | Retrieval eligibility |
|---|---|---|
| `in_force` | Official source states that the document is currently in force | Eligible after all quality gates pass |
| `amended` | Still relevant but some provisions were explicitly amended | Eligible only with visible version evidence |
| `revoked` | Official evidence states the instrument was revoked | Historical-only; never presented as current law |
| `superseded` | Replaced by a later official instrument | Historical-only |
| `unknown` | Status cannot be established | Quarantined and excluded from retrieval |

## Update mechanism

Metadata receives a manual review every 30 days and before release. The ingestion client
compares the server's declared content type, PDF signature, byte count, and SHA-256 against
the manifest. JDIH BPK currently serves these PDFs as `application/octet-stream`, so the
format is independently enforced by the `%PDF-` signature. An exact
match may be accepted or marked unchanged. Any mismatch is visible as quarantine evidence;
the previous approved corpus remains the last-known-good version.

Validate the checked-in manifest with:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\validate_regulation_manifest.py
```

Perform a live, non-persisting checksum and parser smoke against only the manifest-listed
official files with:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\inspect_regulation_sources.py
```
