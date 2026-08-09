# NusaIntel — Product Requirements Document

| Field | Value |
|---|---|
| Document status | Draft v0.1 |
| Product stage | Pre-development |
| Owner | Labo John Noel Napitupulu |
| Created | 2026-08-08 |
| Primary release | Regional Opportunity Engine + Control Tower Lite |
| Follow-up release | RegulasiLens ID |
| Target platform | Responsive web application |
| Primary language | Bahasa Indonesia |

## 1. Product summary

NusaIntel adalah platform *public-data intelligence* Indonesia yang mengubah data statistik dan dokumen regulasi resmi menjadi insight yang dapat ditelusuri, dibandingkan, dan diverifikasi.

NusaIntel terdiri dari tiga produk yang berbagi fondasi data yang sama:

1. **Data Reliability Control Tower** memastikan dataset terdaftar, tervalidasi, memiliki histori, dan dapat dipercaya sebelum digunakan.
2. **Regional Opportunity Engine** membantu pengguna membandingkan karakteristik serta potensi wilayah menggunakan indikator resmi dan metode penilaian yang transparan.
3. **RegulasiLens ID** membantu pengguna mencari, membandingkan, dan memahami regulasi dengan kutipan yang dapat ditelusuri kembali ke dokumen resmi.

MVP berfokus pada Regional Opportunity Engine yang ditenagai Control Tower Lite. RegulasiLens dibangun setelah fondasi ingestion, observability, dan data contract terbukti stabil.

## 2. Problem statement

Data publik Indonesia tersedia melalui banyak portal, tetapi pemanfaatannya menghadapi beberapa hambatan:

- Dataset berbeda dalam struktur, kode wilayah, periode pembaruan, dan kelengkapan.
- Pengguna sering melihat visualisasi tanpa mengetahui freshness, kualitas, atau lineage datanya.
- Skor atau peringkat wilayah sering diberikan tanpa penjelasan mengenai bobot, normalisasi, dan dampak missing values.
- Dokumen regulasi panjang, tersebar, memiliki relasi perubahan atau pencabutan, dan sulit ditelusuri secara manual.
- Aplikasi berbasis AI dapat menghasilkan jawaban meyakinkan tanpa bukti yang memadai.

NusaIntel menyelesaikan masalah tersebut dengan prinsip **evidence first**: setiap insight harus memiliki sumber, versi data, metode, dan status kualitas yang terlihat.

## 3. Product vision

> Menjadi platform intelligence data publik Indonesia yang transparan, dapat direproduksi, dan dapat dipercaya untuk riset awal serta pengambilan keputusan berbasis bukti.

## 4. Goals

### 4.1 Product goals

- Menyatukan ingestion, validation, transformation, dan serving data resmi dalam satu alur yang dapat diaudit.
- Membantu pengguna membandingkan wilayah tanpa menyembunyikan asumsi penilaian.
- Menampilkan freshness, kualitas, dan sumber untuk setiap indikator.
- Menghasilkan insight regional yang dapat direproduksi dari konfigurasi dan versi dataset yang sama.
- Menghasilkan jawaban regulasi yang selalu disertai kutipan dan tautan sumber.
- Menjadi proyek portfolio unggulan untuk data engineering, decision intelligence, MLOps, dan trustworthy AI.

### 4.2 Portfolio goals

- Mendemonstrasikan arsitektur full-stack Python dan TypeScript.
- Mendemonstrasikan data contracts, orchestration, lineage, observability, dan automated testing.
- Mendemonstrasikan statistik regional, normalization, clustering, explainability, dan sensitivity analysis.
- Mendemonstrasikan hybrid retrieval, version-aware document processing, dan RAG evaluation.
- Mendemonstrasikan CI/CD, security controls, reproducible local setup, serta dokumentasi teknis.

### 4.3 MVP success criteria

MVP dinyatakan berhasil apabila seluruh kondisi berikut terpenuhi:

| Area | Minimum benchmark |
|---|---|
| Data coverage | Minimal 6 indikator, 3 tahun/periode, dan seluruh provinsi yang tersedia konsisten dari sumber |
| Data quality | 100% dataset memiliki contract; minimal 95% quality checks lulus pada release dataset |
| Freshness visibility | 100% indikator menampilkan waktu pengambilan dan periode referensi |
| Reproducibility | Skor yang dihitung ulang dari dataset version dan konfigurasi yang sama identik |
| API performance | p95 endpoint baca utama di bawah 500 ms pada dataset MVP lokal |
| Dashboard performance | Halaman utama usable dalam 3 detik pada koneksi broadband setelah aset termuat |
| Accessibility | Tidak ada pelanggaran accessibility kategori critical pada automated check |
| Backend quality | Minimal 80% coverage pada modul business logic kritis |
| Reliability | Pipeline sukses minimal 95% dalam 30 scheduled/dry runs terakhir sebelum release |
| Documentation | Setup baru dapat dijalankan mengikuti README tanpa langkah tak terdokumentasi |

## 5. Non-goals

Versi awal tidak bertujuan untuk:

- Memberikan keputusan investasi, hukum, kredit, atau kebijakan publik secara otomatis.
- Menyatakan satu wilayah secara absolut lebih baik daripada wilayah lain.
- Menggantikan analisis ahli atau verifikasi langsung terhadap publikasi resmi.
- Mengumpulkan data personal atau data mikro individu.
- Mencakup seluruh indikator BPS sejak release pertama.
- Mencakup seluruh regulasi Indonesia sejak release pertama.
- Memberikan real-time prediction jika sumber resmi hanya diperbarui bulanan atau tahunan.
- Menjadi data lake atau observability platform enterprise multi-tenant.
- Menggunakan LLM untuk menghasilkan skor peluang wilayah.

## 6. Product principles

### 6.1 Evidence first

Setiap angka, peringkat, cluster, dan kutipan harus dapat ditelusuri ke sumber serta versi data.

### 6.2 Quality is a feature

Status data tidak boleh disembunyikan. Missing values, stale data, failed checks, dan perubahan schema harus terlihat.

### 6.3 Explainable by default

Pengguna dapat melihat rumus normalisasi, bobot, kontribusi setiap indikator, serta perubahan hasil ketika bobot diubah.

### 6.4 Human-controlled assumptions

Bobot dan skenario adalah pilihan pengguna. Sistem tidak mengklaim satu konfigurasi sebagai kebenaran universal.

### 6.5 Fail closed for unsupported claims

RegulasiLens harus menolak atau membatasi jawaban ketika bukti tidak cukup. Tidak boleh membuat kutipan, nomor pasal, atau status regulasi yang tidak ditemukan.

### 6.6 Public and privacy-conscious

Gunakan data agregat resmi atau data sintetis. Jangan menyimpan kredensial, data personal, atau dokumen yang tidak memiliki izin distribusi di repository.

## 7. Target users

### 7.1 Mahasiswa dan peneliti

Membutuhkan data pembanding wilayah dengan sumber dan metodologi yang jelas untuk eksplorasi awal.

### 7.2 Analis organisasi atau kebijakan

Membutuhkan ringkasan regional, perbandingan indikator, dan export yang dapat diverifikasi sebelum melakukan analisis mendalam.

### 7.3 Pelaku usaha dan organisasi sosial

Membutuhkan pemetaan awal kondisi wilayah, tetapi tetap dapat mengubah bobot sesuai konteks keputusan mereka.

### 7.4 Data engineer atau data steward

Membutuhkan visibilitas mengenai freshness, schema, quality checks, lineage, dan kegagalan pipeline.

### 7.5 Pengguna RegulasiLens

Membutuhkan pencarian awal regulasi dengan kutipan resmi. Pengguna harus memahami bahwa hasil bukan nasihat hukum.

## 8. Core user journeys

### 8.1 Membandingkan wilayah

1. Pengguna memilih 2–5 wilayah dan periode.
2. Sistem menampilkan indikator yang comparable.
3. Pengguna melihat nilai, tren, sumber, dan status kualitas.
4. Pengguna mengubah bobot sesuai tujuan analisis.
5. Sistem menghitung ulang skor dan menjelaskan perubahan kontribusi.
6. Pengguna mengekspor ringkasan beserta metodologi dan metadata sumber.

### 8.2 Menemukan wilayah serupa

1. Pengguna memilih satu wilayah referensi.
2. Sistem menampilkan wilayah dengan profil indikator paling mirip.
3. Pengguna melihat jarak, indikator pembeda, missing values, dan periode data.

### 8.3 Memeriksa kesehatan data

1. Data steward membuka Control Tower.
2. Sistem menampilkan pipeline terakhir, freshness, dan check failures.
3. Pengguna membuka satu dataset untuk melihat contract dan histori hasil.
4. Pengguna menelusuri dataset sumber hingga tabel Gold yang digunakan aplikasi.

### 8.4 Mencari regulasi

1. Pengguna memasukkan pertanyaan atau kata kunci.
2. Sistem mengambil pasal dan dokumen relevan.
3. Jawaban hanya disusun berdasarkan evidence yang ditemukan.
4. Setiap klaim memiliki kutipan dan tautan dokumen.
5. Pengguna dapat membuka konteks sebelum dan sesudah pasal.

### 8.5 Membandingkan regulasi

1. Pengguna memilih dua dokumen atau versi.
2. Sistem menunjukkan bagian yang ditambah, diubah, atau dihapus.
3. Pengguna melihat metadata dan relasi antarperaturan.

## 9. Functional requirements

### 9.1 Shared data platform

#### FR-SDP-01 — Source registry

Sistem harus menyimpan nama sumber, URL resmi, pemilik data, metode akses, jadwal, dan terms/attribution notes.

#### FR-SDP-02 — Versioned ingestion

Setiap ingestion harus menghasilkan `run_id`, timestamp, checksum, source metadata, row count, dan status.

#### FR-SDP-03 — Medallion layers

- Bronze menyimpan respons sumber tanpa perubahan material.
- Silver menyimpan data bersih dengan kode, tipe, dan unit terstandar.
- Gold menyimpan tabel siap aplikasi dan fitur analitik.

#### FR-SDP-04 — Region identity

Sistem harus menggunakan kode wilayah stabil dan menyimpan mapping perubahan nama atau pemekaran jika tersedia.

#### FR-SDP-05 — Idempotency

Menjalankan ingestion ulang untuk sumber dan versi yang sama tidak boleh menghasilkan duplikasi.

### 9.2 Data Reliability Control Tower

#### FR-CT-01 — Dataset catalog

Pengguna dapat melihat daftar dataset, owner, layer, source, freshness SLA, last successful run, dan current health.

#### FR-CT-02 — Data contracts

Contract minimal mendukung:

- Column name dan type.
- Nullable/non-nullable.
- Unique key atau composite key.
- Min/max dan accepted values.
- Freshness SLA.
- Row-count change threshold.
- Custom validation rule.

#### FR-CT-03 — Quality runs

Setiap check menghasilkan status, observed value, expected value, severity, dan sample error yang aman ditampilkan.

#### FR-CT-04 — Schema drift

Sistem mendeteksi kolom bertambah, hilang, berganti tipe, atau mengalami perubahan constraint.

#### FR-CT-05 — Freshness monitoring

Sistem membedakan `source_reference_period`, `retrieved_at`, dan `processed_at`.

#### FR-CT-06 — Lineage

Pengguna dapat menelusuri hubungan source → Bronze → Silver → Gold → API/dashboard.

#### FR-CT-07 — Incident history

Failed run dan check failure dicatat dengan status open, acknowledged, resolved, atau ignored-with-reason.

#### FR-CT-08 — Quality gate

Dataset Gold tidak boleh dipublikasikan jika check severity critical gagal.

### 9.3 Regional Opportunity Engine

#### FR-ROE-01 — Indicator catalog

Setiap indikator menampilkan definisi, unit, arah interpretasi, periode, sumber, coverage, dan quality status.

#### FR-ROE-02 — Regional comparison

Pengguna dapat membandingkan 2–5 wilayah pada indikator dan periode yang sama.

#### FR-ROE-03 — Transparent normalization

MVP mendukung minimal min-max dan percentile/rank normalization. Metode aktif harus terlihat.

#### FR-ROE-04 — Configurable scoring

Pengguna dapat:

- Memilih indikator.
- Menentukan bobot dengan total 100%.
- Menentukan apakah nilai tinggi bersifat favorable atau unfavorable.
- Menyimpan atau menyalin konfigurasi sebagai JSON/shareable state.

#### FR-ROE-05 — Score explanation

Sistem menampilkan kontribusi setiap indikator dan alasan perubahan peringkat.

#### FR-ROE-06 — Sensitivity analysis

Sistem menunjukkan apakah ranking stabil ketika bobot berubah dalam rentang kecil yang ditentukan.

#### FR-ROE-07 — Similar-region search

Sistem menghasilkan wilayah serupa menggunakan fitur yang dinormalisasi, dengan daftar indikator yang digunakan dan jarak hasil.

#### FR-ROE-08 — Clustering

Cluster harus memiliki evaluation report, feature list, preprocessing version, dan deskripsi berbasis data. Sistem tidak memberikan label normatif seperti “buruk” atau “tertinggal” secara otomatis.

#### FR-ROE-09 — Map and trend views

Pengguna dapat melihat peta choropleth, tren waktu, distribusi, dan tabel raw/normalized.

#### FR-ROE-10 — Export report

Export minimal memuat tanggal, wilayah, periode, konfigurasi bobot, hasil, metodologi, sumber, dan peringatan kualitas.

### 9.4 RegulasiLens ID

#### FR-RL-01 — Limited-domain corpus

Release pertama hanya mencakup satu domain yang dipilih dan daftar sumber resmi yang terdokumentasi.

#### FR-RL-02 — Structure-aware parsing

Dokumen dipisahkan berdasarkan struktur seperti judul, konsiderans, BAB, bagian, pasal, dan ayat jika dapat dikenali.

#### FR-RL-03 — Regulation metadata

Simpan nomor, jenis, tahun, judul, instansi, tanggal, status, URL, checksum, dan tanggal pengambilan.

#### FR-RL-04 — Regulation graph

Simpan relasi `mengubah`, `diubah oleh`, `mencabut`, `dicabut oleh`, dan `melaksanakan` jika evidence metadata tersedia.

#### FR-RL-05 — Hybrid retrieval

Gunakan keyword retrieval dan semantic retrieval. Setiap hasil memiliki retrieval score dan source reference.

#### FR-RL-06 — Grounded answer

Jawaban harus:

- Menggunakan konteks hasil retrieval.
- Menyertakan citation pada setiap klaim material.
- Tidak membuat nomor pasal atau status hukum.
- Menyatakan keterbatasan jika evidence tidak memadai.

#### FR-RL-07 — Context viewer

Pengguna dapat membuka teks sebelum dan sesudah bagian yang dikutip.

#### FR-RL-08 — Version comparison

Sistem dapat menunjukkan perubahan teks antara dua dokumen/versi yang tersedia.

#### FR-RL-09 — Evaluation harness

Evaluation set harus versioned dan mencakup answerable, unanswerable, multi-document, serta version-sensitive questions.

## 10. Initial data scope

### 10.1 Regional Opportunity Engine MVP

Kandidat indikator awal:

1. Tingkat pengangguran terbuka.
2. Persentase penduduk miskin.
3. PDRB per kapita atau pertumbuhan ekonomi.
4. Indeks Pembangunan Manusia.
5. Rata-rata lama sekolah atau indikator pendidikan sejenis.
6. Akses internet atau indikator infrastruktur digital.
7. Kepadatan penduduk sebagai indikator opsional.

Daftar final bergantung pada keseragaman coverage, periodisasi, definisi, dan akses melalui sumber resmi.

### 10.2 Official source candidates

- BPS WebAPI: <https://webapi.bps.go.id/developer>
- Portal BPS: <https://www.bps.go.id/>
- Satu Data Indonesia: <https://data.go.id/>
- JDIH BPK: <https://peraturan.bpk.go.id/>

Setiap connector harus mematuhi terms, rate limits, attribution requirements, serta tidak mengandalkan endpoint yang tidak didokumentasikan tanpa fallback.

## 11. Scoring and analytical methodology

### 11.1 Score definition

Opportunity score adalah hasil skenario pengguna, bukan fakta objektif. Formula dasar:

```text
score(region) = Σ normalized_indicator(region, i) × weight(i)
```

Untuk indikator unfavorable, nilai normalized dibalik secara eksplisit. Missing value tidak boleh diam-diam diubah menjadi nol.

### 11.2 Missing-data policy

- Tampilkan coverage per wilayah dan indikator.
- Jangan memberi skor jika coverage berada di bawah threshold yang dikonfigurasi.
- MVP menggunakan complete-case scoring untuk indikator terpilih.
- Imputation, jika ditambahkan, harus opsional, terdokumentasi, dan diberi label.

### 11.3 Ranking safeguards

- Tampilkan score interval atau sensitivity band bila tersedia.
- Hindari presisi palsu; batasi digit score yang ditampilkan.
- Tampilkan peringkat bersama nilai indikator dan kontribusinya.
- Jangan menyimpulkan sebab-akibat dari korelasi atau ranking.

### 11.4 Clustering safeguards

- Evaluasi beberapa nilai `k` menggunakan silhouette dan stability checks.
- Standardization hanya di-fit pada data analisis yang terdokumentasi.
- Cluster description harus berdasarkan fitur dominan, bukan stereotipe wilayah.

## 12. RegulasiLens evaluation benchmarks

RegulasiLens tidak boleh dirilis hanya berdasarkan penilaian visual. Minimum benchmark untuk beta:

| Metric | Target beta |
|---|---|
| Evaluation set | Minimal 100 pertanyaan yang direview manual |
| Retrieval Recall@10 | ≥ 0.85 pada pertanyaan answerable |
| Citation correctness | ≥ 0.95 |
| Citation coverage | ≥ 0.90 untuk klaim material |
| Unanswerable refusal accuracy | ≥ 0.90 |
| Fabricated citation rate | 0% pada evaluation set |
| Version-sensitive accuracy | ≥ 0.85 |
| Search latency | p95 < 1.5 detik, tidak termasuk generation |
| End-to-end answer latency | p95 < 10 detik pada environment benchmark yang dicatat |

Model dan embedding provider belum ditentukan. Evaluation harus tetap dapat dijalankan ketika provider diganti.

## 13. Non-functional requirements

### 13.1 Reliability

- Pipeline memiliki retry terbatas dan failure state yang eksplisit.
- Tidak ada partial publish ke Gold apabila transaksi gagal.
- Semua migration dan ingestion bersifat idempotent atau memiliki recovery procedure.

### 13.2 Performance

- Gunakan precomputation untuk agregasi yang mahal.
- API mendukung pagination dan query limits.
- Request eksternal menggunakan timeout, retry dengan backoff, dan cache yang sesuai.

### 13.3 Security

- Tidak ada secret dalam repository, frontend bundle, logs, atau fixtures.
- Input pengguna divalidasi dan dibatasi ukurannya.
- Export dinetralisasi dari spreadsheet formula injection.
- Dependency dan secret scanning dijalankan di CI.
- LLM/provider key, jika digunakan, hanya tersedia di backend.

### 13.4 Privacy

- Tidak mengumpulkan identitas pengguna pada MVP.
- Analytics penggunaan, jika ditambahkan, harus opt-in atau privacy-preserving.
- Log tidak menyimpan prompt sensitif atau credential.

### 13.5 Accessibility

- Navigasi keyboard untuk alur utama.
- Kontras warna memenuhi WCAG AA pada komponen utama.
- Chart memiliki ringkasan tekstual atau tabel alternatif.
- Peta bukan satu-satunya cara memperoleh informasi.

### 13.6 Maintainability

- Python dan TypeScript menggunakan strict lint/type checks.
- Business logic dipisahkan dari route dan UI.
- Public API memiliki schema/versioning.
- Architecture decision penting dicatat sebagai ADR.

### 13.7 Reproducibility

Setiap output analitik harus dapat mereferensikan:

- Dataset version/checksum.
- Transformation version.
- Scoring/model configuration.
- Code commit.
- Generated timestamp.

## 14. Proposed architecture

```text
Official Sources
  ├── BPS WebAPI
  ├── data.go.id
  └── JDIH BPK
          │
          ▼
Connectors + Orchestrator
          │
          ▼
Bronze → Data Contracts → Silver → Gold
                 │                   │
                 ▼                   ▼
        Control Tower        Analytics / Retrieval
                                     │
                    ┌────────────────┴───────────────┐
                    ▼                                ▼
          Regional Opportunity              RegulasiLens ID
```

Proposed stack:

- Backend: Python 3.11+, FastAPI, SQLAlchemy, Alembic.
- Frontend: Next.js, React, TypeScript.
- Database: PostgreSQL; `pgvector` hanya jika dipilih untuk RegulasiLens.
- Data validation: Pandera/Pydantic dan custom rules.
- Orchestration: Prefect atau scheduler sederhana untuk MVP.
- Analytics: Pandas/Polars, scikit-learn.
- Testing: Pytest, Vitest, Playwright.
- Infrastructure: Docker Compose, GitHub Actions.

Final dependency decisions dibuat melalui ADR setelah spike, bukan berdasarkan popularitas semata.

## 15. Core entities

Entity minimum:

- `Source`
- `Dataset`
- `DatasetVersion`
- `PipelineRun`
- `DataContract`
- `QualityCheckResult`
- `LineageEdge`
- `Region`
- `Indicator`
- `Observation`
- `ScoreConfiguration`
- `ScoreResult`
- `Regulation`
- `RegulationVersion`
- `RegulationRelation`
- `DocumentSection`
- `RetrievalEvaluationCase`
- `EvaluationRun`

## 16. API surface — initial draft

### Control Tower

- `GET /api/v1/health`
- `GET /api/v1/datasets`
- `GET /api/v1/datasets/{id}`
- `GET /api/v1/datasets/{id}/quality`
- `GET /api/v1/pipeline-runs`
- `GET /api/v1/lineage/{dataset_id}`

### Regional Opportunity Engine

- `GET /api/v1/regions`
- `GET /api/v1/indicators`
- `GET /api/v1/observations`
- `POST /api/v1/scores/calculate`
- `POST /api/v1/scores/sensitivity`
- `POST /api/v1/regions/similar`
- `GET /api/v1/exports/regional-report`

### RegulasiLens

- `GET /api/v1/regulations`
- `GET /api/v1/regulations/{id}`
- `GET /api/v1/regulations/{id}/relations`
- `POST /api/v1/regulations/search`
- `POST /api/v1/regulations/answer`
- `GET /api/v1/regulations/compare`

## 17. Product metrics

### 17.1 Reliability metrics

- Pipeline success rate.
- Mean time to detect failed quality checks.
- Mean time to resolve incidents.
- Percentage dataset with current contracts.
- Number of critical failures reaching Gold; target zero.

### 17.2 Regional Engine metrics

- Percentage indicator with complete source metadata.
- Percentage comparison requests without hidden imputation.
- Score reproducibility pass rate.
- Export success rate.
- Percentage users who inspect methodology or contribution details during usability test.

### 17.3 RegulasiLens metrics

- Retrieval Recall@k.
- Citation correctness and coverage.
- Refusal accuracy.
- Fabricated citation rate.
- Percentage answers whose cited section can be opened successfully.

### 17.4 Engineering metrics

- CI pass rate.
- Automated test coverage for critical logic.
- Dependency vulnerability count at high/critical severity.
- Setup success from a clean environment.
- p50/p95 API latency.

## 18. Release criteria

### 18.1 MVP release gate

- [ ] Seluruh MVP success criteria pada Section 4.3 terpenuhi.
- [ ] Minimal satu end-to-end BPS connector berjalan terjadwal.
- [ ] Critical quality check menghentikan Gold publish.
- [ ] Regional comparison, scoring, explanation, dan sensitivity tersedia.
- [ ] Methodology dan source metadata terlihat di UI.
- [ ] Backend, frontend, database, dan worker healthy melalui Docker Compose.
- [ ] Unit, integration, E2E, lint, typecheck, migration, dan security checks lulus di CI.
- [ ] Demo menggunakan data publik yang aman dipublikasikan.
- [ ] README, architecture, data dictionary, dan limitations selesai.

### 18.2 RegulasiLens beta gate

- [ ] Satu domain regulasi memiliki corpus dan source manifest terdokumentasi.
- [ ] Semua benchmark Section 12 terpenuhi.
- [ ] Tidak ada fabricated citation pada evaluation set.
- [ ] Status dan versi dokumen terlihat jelas.
- [ ] Disclaimer dan refusal behavior diuji.
- [ ] Pipeline document update terpantau oleh Control Tower.

## 19. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| BPS schema atau endpoint berubah | Pipeline gagal atau data salah | Contract tests, schema drift alert, cached raw response, connector versioning |
| Periode/definisi indikator tidak comparable | Ranking menyesatkan | Metadata wajib, compatibility rules, disable comparison jika tidak valid |
| Missing data mengubah ranking | False confidence | Coverage threshold, no silent zero-fill, sensitivity report |
| Ranking dianggap rekomendasi absolut | Misuse | Configurable weights, methodology panel, disclaimer, contribution chart |
| Portal resmi lambat/tidak tersedia | Ingestion gagal | Timeout, bounded retry, last-known-good version, visible freshness |
| Dokumen regulasi sulit diparsing | Kutipan salah | Structure validation, manual spot checks, quarantine failed documents |
| LLM mengarang jawaban | Harmful misinformation | Evidence-only prompt, citation validation, refusal, evaluation gate |
| Scope terlalu besar | Proyek tidak selesai | Regional MVP first, one connector first, one regulation domain only |
| Tooling terlalu berat | Development melambat | ADR dan spike; pilih komponen minimum yang memenuhi requirement |

## 20. Milestone roadmap

### Release 0.1 — Foundation

Repository, local stack, schemas, first connector, Bronze/Silver/Gold, dan baseline CI.

### Release 0.2 — Control Tower Lite

Catalog, contracts, quality history, freshness, schema drift, dan quality gate.

### Release 0.3 — Regional Opportunity MVP

Comparison, scoring, explainability, sensitivity, similar regions, map, dan export.

### Release 0.4 — Portfolio hardening

Performance benchmark, accessibility, security audit, documentation, demo dataset, dan deployment.

### Release 0.5 — RegulasiLens ingestion

Satu domain regulasi, structure-aware parsing, metadata, relations, dan retrieval baseline.

### Release 0.6 — RegulasiLens beta

Grounded answers, citations, comparison, evaluation harness, dan release gate.

## 21. Open decisions

Keputusan berikut harus diselesaikan melalui spike/ADR:

- Level wilayah MVP: provinsi saja atau provinsi + kabupaten/kota.
- Daftar indikator final berdasarkan coverage aktual.
- Polars versus Pandas untuk transformation utama.
- Prefect versus scheduler aplikasi sederhana.
- Storage Bronze lokal/S3-compatible.
- Metode similarity dan clustering final.
- Domain pertama RegulasiLens.
- Embedding model, reranker, dan generation provider.
- Strategi deployment portfolio dengan biaya minimum.

## 22. Definition of product success

NusaIntel berhasil bukan ketika memiliki dashboard terbanyak, tetapi ketika:

1. Pengguna dapat menelusuri setiap insight hingga sumber dan versi datanya.
2. Data berkualitas buruk tidak diam-diam mencapai aplikasi.
3. Perbandingan wilayah dapat dijelaskan dan direproduksi.
4. Jawaban regulasi memiliki evidence atau secara eksplisit menolak menjawab.
5. Proyek dapat dijalankan, diuji, dan dipahami oleh developer lain tanpa akses ke mesin pembuatnya.
