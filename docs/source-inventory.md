# Source Inventory

- Status: Phase 2 six-indicator benchmark complete
- Last reviewed: 2026-08-09
- Scope: Regional Opportunity Engine MVP

## 1. Primary source

### BPS WebAPI

| Field | Value |
|---|---|
| Owner | Badan Pusat Statistik |
| Portal | <https://webapi.bps.go.id/developer/> |
| Documentation | <https://webapi.bps.go.id/documentation/> |
| Response format | JSON |
| Authentication | Key token from API portal |
| Environment variable | `BPS_API_KEY` |
| Key configured during Phase 0 | Yes, local `.env` only; ignored by Git |
| MVP domain | `0000` / BPS pusat, verified live |
| Dynamic data endpoint | `https://webapi.bps.go.id/v1/api/list` |
| Source status | Authenticated TPT contract ingested live through Bronze, Silver, and Gold |

The official documentation states that users are identified using a key token and can obtain two to three tokens from the API portal. The API exposes domain, subject, variable, period, unit, dynamic data, static table, publication, and other models.

A live request without a key reached the official endpoint on 2026-08-08 and returned:

```json
{
  "status": "Error",
  "message": "Parameter Key is Missing."
}
```

The unchanged response is stored as `tests/fixtures/bps/missing_key_error.json`.

An authenticated request on 2026-08-08 verified variable `543` as "Tingkat
Pengangguran Terbuka Menurut Provinsi" in percent. The confirmed dimension IDs
are:

| Dimension | ID |
|---|---:|
| 2023 | `123` |
| 2024 | `124` |
| 2025 | `125` |
| February | `189` |
| August | `190` |
| Annual | `191` (no data available for this request) |

The comparable MVP TPT series therefore uses August. The unchanged live
response is stored as
`tests/fixtures/bps/tpt_august_543_2023_2025_live.json`; request parameters and
its checksum are recorded in `tests/fixtures/bps/README.md`.

Example request shape:

```text
GET https://webapi.bps.go.id/v1/api/list
  ?model=data
  &lang=ind
  &domain=0000
  &var={variable_id}
  &th={period_id}
  &key={BPS_API_KEY}
```

Security requirements:

- Never send the key to the frontend.
- Redact `key` from logs and error reports.
- Do not store request URLs containing the key.
- Use explicit timeout and bounded retry.
- Cache successful raw responses and serve last-known-good Gold data during source outage.

## 2. MVP table inventory

### SRC-BPS-001 — Labor force indicators

| Field | Value |
|---|---|
| Indicators | TPT and TPAK |
| Official table | <https://www.bps.go.id/id/statistics-table/3/V2pOVWJWcHJURGg0U2pONFJYaExhVXB0TUhacVFUMDkjMyMwMDAw/tingkat-pengangguran-terbuka-tpt-dan-tingkat-partisipasi-angkatan-kerja-tpak-menurut-provinsi.html?year=2023> |
| Geography | Province |
| Target periods | 2023, 2024, 2025 |
| Unit | Percent |
| Frequency note | Use the same reference period, targeted to August, across all years |
| API variable IDs | TPT=`543`; TPAK=`2396` |
| Live TPT coverage | 113/117 cells (96.58%): 34 provinces + Indonesia in 2023; 38 provinces + Indonesia in 2024 and 2025 |
| Risks | February/August observations must not be mixed; four new Papua provinces have no separate August 2023 value |

### SRC-BPS-002 — Poverty

| Field | Value |
|---|---|
| Indicator | Percentage of poor population |
| Official table | <https://www.bps.go.id/id/statistics-table/3/UkVkWGJVZFNWakl6VWxKVFQwWjVWeTlSZDNabVFUMDkjMw%3D%3D/jumlah-dan-persentase-penduduk-miskin-menurut-provinsi.html> |
| Metadata evidence | <https://sirusa.web.bps.go.id/metadata/indikator/1104> |
| Geography | Province |
| Target periods | 2023, 2024, 2025 |
| Unit | Percent |
| Frequency note | Use March condition across all years for comparability |
| API variable ID | `192`; derived variable `434` (total); March `turth=61` |
| Risks | Urban/rural breakdown and total must not be confused |

### SRC-BPS-003 — PDRB per capita

| Field | Value |
|---|---|
| Indicator | GRDP per capita at current prices |
| Official table | <https://www.bps.go.id/id/statistics-table/3/YWtoQlRVZzNiMU5qU1VOSlRFeFZiRTR4VDJOTVVUMDkjMw%3D%3D/produk-domestik-regional-bruto-per-kapita-atas-dasar-harga-berlaku-menurut-provinsi> |
| Geography | Province |
| Target periods | 2023, 2024, 2025 |
| Unit | Thousand rupiah |
| API variable ID | `288`; derived variable `530` (current prices) |
| Risks | Current-price values are not real growth and may be affected by price levels and extractive industries |

### SRC-BPS-004 — Economic growth

| Field | Value |
|---|---|
| Indicator | Growth rate of GRDP at constant 2010 prices |
| Official table | <https://www.bps.go.id/id/statistics-table/3/WnpCcmNtcE1ibkF5VjFSelJHMUVhRE52WjNWSVp6MDkjMyMwMDAw/laju-pertumbuhan-produk-domestik-regional-bruto-atas-dasar-harga-konstan-2010--menurut-provinsi--persen-.html?year=2023> |
| Geography | Province |
| Target periods | 2023, 2024, 2025 |
| Unit | Percent |
| Base year | 2010 |
| API variable ID | `291` |
| Risks | Preliminary/revised flags must be preserved |

### SRC-BPS-005 — Human development

| Field | Value |
|---|---|
| Indicator | Human Development Index |
| Official table | <https://www.bps.go.id/id/statistics-table/3/V25GaFNHaExaMnhITm1sWmRrUlJZelJzYUc1SGR6MDkjMw%3D%3D/indeks-pembangunan-manusia-menurut-provinsi--2023.html?year=2023> |
| 2025 publication | <https://www.bps.go.id/publication/2026/04/24/f96755ab0e48765d028c0462/indeks-pembangunan-manusia-2025.html> |
| Geography | Province |
| Target periods | 2023, 2024, 2025 |
| Unit | Index points |
| API variable ID | `494` (method-new province series) |
| Risks | New-method IPM only; old-method series must be rejected |

API variable `494` is the verified province-level method-new series. As of the
2026-08-09 live discovery, it exposes period IDs `123` (2023) and `124` (2024)
but not `125` (2025). NusaIntel therefore preserves 2025 as unavailable/missing.

## 3. Deferred official sources

### Internet access

- Candidate table: <https://www.bps.go.id/id/statistics-table/2/NzAjMg%3D%3D/population-5-years-of-age-and-over-who-ever-accessing-internet--in-the-last-3-months-by-province-and-gender.html>
- Status: Post-MVP candidate.
- Reason deferred: a single compatible API series for all provinces and 2023–2025 has not been verified.

### Satu Data Indonesia

- Portal: <https://data.go.id/>
- Status: Secondary source only after BPS MVP.
- Requirement: each dataset receives its own source contract and license/attribution review.

### JDIH BPK

- Portal: <https://peraturan.bpk.go.id/>
- Status: Active for the bounded Phase 7 personal-data-protection corpus.
- Policy: manifest-listed HTTPS pages and PDFs only; sequential retrieval, official
  attribution, ignored local cache, checksum/metadata review, and no bulk crawling.
- Manifest: `regulations/manifests/personal-data-protection.v1.json`.
- Scope and status vocabulary: `docs/regulasilens-scope.md`.

## 4. Attribution and usage policy

- Every application view and export must name BPS as the data source.
- The source URL, reference period, retrieval timestamp, and dataset version/checksum must be retained.
- Original BPS notes and provisional/revised markers must be preserved.
- The API key is a credential and is never part of an attribution URL.
- Rate-limit details were not found in the publicly rendered documentation during Phase 0. The connector will default to conservative sequential requests, caching, timeout, and bounded retries until an official limit is confirmed.
- Public release requires one final review of the BPS portal Terms of Use and any dataset-specific note.

## 5. Source readiness checklist

- [x] Official portal identified.
- [x] Official API documentation reviewed.
- [x] Authentication mechanism identified.
- [x] Live endpoint reachability and missing-key behavior verified.
- [x] Six MVP indicators mapped to official tables.
- [x] Reference-period risks documented.
- [x] `BPS_API_KEY` configured locally and ignored by Git.
- [x] Live domain/period/subperiod discovery completed for TPT.
- [x] Raw authenticated TPT API fixture captured without modification.
- [x] Live variable/period discovery completed for all six indicators.
- [x] Credential-safe live fixtures captured for all six indicators.
- [x] Six-indicator coverage benchmark completed with deterministic checksums.
- [ ] Official rate-limit or support guidance confirmed.
