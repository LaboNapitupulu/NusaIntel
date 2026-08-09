# MVP Indicator Selection

- Decision date: 2026-08-08
- Geography: Province
- Target coverage: 38 provinces
- Comparison window: 2023–2025
- Status: Selected; TPT live API contract verified, five API IDs pending

## 1. Selection criteria

An indicator is eligible for MVP when it:

1. Is published by an official BPS source.
2. Has province-level values.
3. Has a comparable definition and unit across 2023–2025.
4. Has a defensible favorable/unfavorable direction for a user-defined opportunity scenario.
5. Adds a distinct analytical dimension or is explicitly grouped as a sub-indicator.
6. Preserves source notes, reference period, and provisional/revised flags.

## 2. Selected indicators

| ID | Indicator | Dimension | Unit | Direction | Reference period | Coverage target |
|---|---|---|---|---|---|---|
| `tpt` | Tingkat Pengangguran Terbuka | Labor market | Percent | Lower is favorable | August | 38 provinces, 2023–2025 |
| `tpak` | Tingkat Partisipasi Angkatan Kerja | Labor market | Percent | Higher is favorable | August | 38 provinces, 2023–2025 |
| `poverty_rate` | Persentase Penduduk Miskin | Inclusion | Percent | Lower is favorable | March | 38 provinces, 2023–2025 |
| `grdp_per_capita_current` | PDRB per Kapita ADHB | Prosperity level | Thousand rupiah | Higher is favorable, with caveat | Annual | 38 provinces, 2023–2025 |
| `grdp_growth_constant_2010` | Laju Pertumbuhan PDRB ADHK 2010 | Economic momentum | Percent | Higher is favorable, with caveat | Annual | 38 provinces, 2023–2025 |
| `hdi` | Indeks Pembangunan Manusia | Human development | Index points | Higher is favorable | Annual | 38 provinces, 2023–2025 |

## 3. Definitions and interpretation

### 3.1 Tingkat Pengangguran Terbuka

Share of the labor force that is unemployed under the applicable BPS/Sakernas definition.

- Direction: lower is favorable.
- Caveat: a low TPT does not guarantee high-quality or formal employment.
- Comparability rule: use the same observation season, August, for all years.

### 3.2 Tingkat Partisipasi Angkatan Kerja

Share of the working-age population participating in the labor force.

- Direction: higher is favorable for the baseline labor-utilization scenario.
- Caveat: participation may rise because of household economic pressure and is not a job-quality measure.
- Comparability rule: use August observations aligned with TPT.

### 3.3 Persentase Penduduk Miskin

Share of people whose average monthly per-capita expenditure is below the poverty line.

- Direction: lower is favorable.
- Caveat: poverty lines differ by region and period as part of the official methodology.
- Comparability rule: use March total values, not urban/rural subgroup values.

### 3.4 PDRB per Kapita ADHB

Regional gross domestic product at current prices divided by population, published in thousand rupiah.

- Direction: higher is favorable as an economic-output proxy.
- Caveat: it is not household income, is affected by price changes, and may be high in resource-producing provinces without broad household prosperity.
- Display rule: never label this value as average salary or income.

### 3.5 Laju Pertumbuhan PDRB ADHK 2010

Annual percentage growth in real regional output using constant 2010 prices.

- Direction: higher is favorable as a momentum proxy.
- Caveat: volatile commodity/base effects can produce exceptional values.
- Quality rule: preserve preliminary and revised markers.

### 3.6 Indeks Pembangunan Manusia

Composite measure representing health, education, and standard-of-living dimensions under the current BPS methodology.

- Direction: higher is favorable.
- Caveat: IPM is composite and must not be mixed with old-method series.
- Scoring rule: do not add IPM components to the default score without reviewing double counting.

## 4. Default scenario design

The product will not present one universal opportunity ranking. It will provide a transparent default demonstration scenario with five equally weighted dimensions:

| Dimension | Weight | Sub-indicators |
|---|---:|---|
| Labor market | 20% | TPT 10%, TPAK 10% |
| Inclusion | 20% | Poverty rate 20% |
| Prosperity level | 20% | PDRB per capita 20% |
| Economic momentum | 20% | PDRB growth 20% |
| Human development | 20% | IPM 20% |

Safeguards:

- Users can change every weight.
- Scores are scenario outputs, not official BPS rankings.
- The UI shows raw values, normalized values, and contribution per indicator.
- Missing values are never converted to zero.
- A region is not ranked when required coverage is below the configured threshold.
- Sensitivity analysis must accompany ranking before MVP release.

## 5. Initial normalization benchmark

MVP supports:

1. Min-max normalization for an intuitive 0–100 contribution scale.
2. Percentile/rank normalization as a robust alternative for strong outliers.

Before release, benchmark both methods on 2023–2025 data and report:

- Rank correlation between methods.
- Largest rank movers.
- Effect of extreme PDRB per-capita values.
- Rank stability under ±5 percentage-point weight perturbation.

No method is selected as default until the actual dataset benchmark is documented.

## 6. Compatibility matrix

| Check | TPT | TPAK | Poverty | PDRB/capita | PDRB growth | IPM |
|---|---:|---:|---:|---:|---:|---:|
| Official BPS table found | Yes | Yes | Yes | Yes | Yes | Yes |
| Province geography | Yes | Yes | Yes | Yes | Yes | Yes |
| 2023 table/series evidence | Yes | Yes | Yes | Yes | Yes | Yes |
| 2024/2025 current series evidence | Yes | Yes | Yes | Yes | Yes | Yes |
| Unit identified | Yes | Yes | Yes | Yes | Yes | Yes |
| Direction documented | Yes | Yes | Yes | Yes | Yes | Yes |
| API variable ID verified | Yes (`543`) | No | No | No | No | No |
| Live 2023–2025 coverage verified | Partial | No | No | No | No | No |

TPT live coverage is 113/117 expected geography-year cells (96.58%). August
2023 has no separate values for Papua Barat Daya, Papua Selatan, Papua Tengah,
and Papua Pegunungan; August 2024 and 2025 cover all 38 provinces. These cells
remain missing until a documented historical-geography policy is adopted.

## 7. Rejected/deferred indicators

### Internet access

Useful for digital-readiness analysis, but deferred until a consistent province-level 2023–2025 API series is verified.

### Population density

Deferred because high density is not universally favorable or unfavorable. It is better used as a context/filter variable than a default score component.

### Mean years of schooling and life expectancy

Deferred from default scoring because both are components related to IPM and would introduce double counting. They may be exposed as explanatory detail later.

### Investment realization

Deferred because it introduces an additional institution/source contract before the BPS vertical slice is stable.

## 8. Source links

- TPT and TPAK: <https://www.bps.go.id/id/statistics-table/3/V2pOVWJWcHJURGg0U2pONFJYaExhVXB0TUhacVFUMDkjMyMwMDAw/tingkat-pengangguran-terbuka-tpt-dan-tingkat-partisipasi-angkatan-kerja-tpak-menurut-provinsi.html?year=2023>
- Poverty: <https://www.bps.go.id/id/statistics-table/3/UkVkWGJVZFNWakl6VWxKVFQwWjVWeTlSZDNabVFUMDkjMw%3D%3D/jumlah-dan-persentase-penduduk-miskin-menurut-provinsi.html>
- PDRB per capita: <https://www.bps.go.id/id/statistics-table/3/YWtoQlRVZzNiMU5qU1VOSlRFeFZiRTR4VDJOTVVUMDkjMw%3D%3D/produk-domestik-regional-bruto-per-kapita-atas-dasar-harga-berlaku-menurut-provinsi>
- PDRB growth: <https://www.bps.go.id/id/statistics-table/3/WnpCcmNtcE1ibkF5VjFSelJHMUVhRE52WjNWSVp6MDkjMyMwMDAw/laju-pertumbuhan-produk-domestik-regional-bruto-atas-dasar-harga-konstan-2010--menurut-provinsi--persen-.html?year=2023>
- IPM: <https://www.bps.go.id/id/statistics-table/3/V25GaFNHaExaMnhITm1sWmRrUlJZelJzYUc1SGR6MDkjMw%3D%3D/indeks-pembangunan-manusia-menurut-provinsi--2023.html?year=2023>
