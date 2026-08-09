# ADR-0001: Arsitektur MVP dan batas produk

- Status: Accepted
- Date: 2026-08-08
- Decision owners: Project owner and implementation team
- Applies to: NusaIntel MVP

## Context

NusaIntel memiliki tiga product surfaces: Data Reliability Control Tower, Regional Opportunity Engine, dan RegulasiLens ID. Membangun seluruh scope sekaligus akan meningkatkan risiko data tidak comparable, tooling berlebihan, dan release yang tidak selesai.

Phase 0 harus menetapkan vertical slice terkecil yang tetap membuktikan kualitas data, traceability, analitik, dan pengalaman pengguna end to end.

## Decisions

### 1. Repository dan visibility

- Nama repository tetap `nusa-intel`.
- Repository dirancang sebagai public portfolio project.
- Development awal dilakukan secara lokal/private sampai `.gitignore`, secret scanning, fixture review, dan public-data review selesai.
- Phase 1 mengonfirmasi `nusa-intel` sebagai standalone Git repository agar tidak tercampur dengan repository workspace induk yang tidak terkait.

### 2. Scope geografis MVP

- MVP menggunakan level **provinsi**.
- Target coverage adalah 38 provinsi Indonesia yang tersedia pada periode 2023–2025.
- Agregat Indonesia boleh disimpan sebagai benchmark nasional, tetapi tidak ikut ranking provinsi.
- Kabupaten/kota ditunda sampai mapping pemekaran, coverage, dan perbedaan domain BPS dapat ditangani dengan benar.

Alasan:

- BPS WebAPI memiliki domain pusat, provinsi, dan kabupaten/kota; dokumentasi saat ini menyebut 1 domain pusat, 34 domain provinsi, dan 514 domain kabupaten/kota.
- Enam tabel kandidat tersedia sebagai tabel menurut provinsi.
- Scope provinsi memberi vertical slice yang cukup bermakna dengan risiko mapping lebih rendah.

### 3. Indikator MVP

Enam indikator awal:

1. Tingkat Pengangguran Terbuka (TPT).
2. Tingkat Partisipasi Angkatan Kerja (TPAK).
3. Persentase Penduduk Miskin.
4. PDRB per Kapita Atas Dasar Harga Berlaku.
5. Laju Pertumbuhan PDRB Atas Dasar Harga Konstan 2010.
6. Indeks Pembangunan Manusia (IPM).

Internet access tetap menjadi kandidat pertama setelah MVP, tetapi tidak masuk baseline karena ketersediaan seri provinsi 2023–2025 melalui satu kontrak API belum terverifikasi.

### 4. Data source dan authentication

- Source utama adalah BPS WebAPI dan tabel statistik resmi BPS.
- Dynamic Data API menggunakan endpoint `https://webapi.bps.go.id/v1/api/list` dengan `model=data`.
- BPS mengidentifikasi user menggunakan key token yang diperoleh dari portal API.
- Secret akan dibaca dari environment variable `BPS_API_KEY`; key tidak boleh ada dalam URL yang dicatat ke log, fixture, frontend, atau Git.
- API key telah dikonfigurasi lokal dan fixture TPT Agustus 2023–2025 telah diverifikasi live tanpa menyimpan credential. Detail kontrak terdapat di `docs/source-inventory.md`.

### 5. Dataframe engine

- MVP menggunakan **Pandas**.
- Dataset analitik MVP diperkirakan hanya ratusan hingga ribuan observation rows, sehingga engine performance bukan bottleneck material.
- Pandas tersedia pada runtime pengembangan dan sesuai dengan skill serta library statistik existing.
- Polars tidak ditambahkan hanya untuk benchmark sintetis yang tidak representatif.
- Keputusan ditinjau ulang jika salah satu kondisi berikut tercapai:
  - Satu transformation input melebihi 1 juta rows.
  - Median transformation time melebihi 2 detik pada benchmark environment.
  - Peak memory pipeline melebihi 1 GB untuk workload normal.

### 6. Scheduling dan orchestration

- MVP menggunakan dedicated Python worker dengan scheduler ringan dan pipeline-run state di Control Tower.
- Scheduling harus berjalan dalam process terpisah dari web API.
- PostgreSQL advisory lock atau mekanisme equivalent digunakan untuk mencegah duplicate concurrent schedule.
- Prefect ditunda karena Control Tower sudah menjadi source of truth untuk run state, quality results, dan incident history.
- Prefect dipertimbangkan kembali jika pipeline memiliki branching kompleks, backfill lintas banyak dataset, distributed workers, atau manual retry per task.

### 7. PostgreSQL schema strategy

Gunakan satu PostgreSQL database dengan logical schemas:

- `ops`: sources, datasets, versions, contracts, runs, checks, incidents, dan lineage.
- `bronze`: raw BPS response JSONB dan immutable retrieval metadata.
- `silver`: region, indicator, period, dan normalized observations.
- `gold`: application-ready regional facts, coverage summaries, dan materialized analytical outputs.

Gold publication dilakukan atomically. Critical quality failure mempertahankan last-known-good Gold version.

Raw payload BPS disimpan dalam JSONB selama ukuran payload masih kecil. Object storage abstraction baru ditambahkan jika corpus dokumen RegulasiLens atau payload size membuat PostgreSQL tidak lagi sesuai.

### 8. Map rendering

- Gunakan **MapLibre GL JS** dengan local province GeoJSON dan source attribution yang terlihat.
- Choropleth MVP tidak bergantung pada paid map token.
- Basemap eksternal bukan requirement; aplikasi harus tetap dapat menampilkan batas provinsi dari local GeoJSON.
- Table alternative wajib tersedia agar peta bukan satu-satunya akses informasi.
- License MapLibre GL JS adalah BSD-3-Clause dan harus dicatat dalam dependency attribution.

### 9. Initial architecture

```text
BPS WebAPI / Official Tables
            │
            ▼
     Connector Worker
            │
            ▼
     bronze.raw_payload
            │
     contract + transform
            │
            ▼
  silver.observations
            │
     quality gate
            │
            ▼
    gold.regional_facts
       │             │
       ▼             ▼
 Control Tower   Regional Engine
```

## Consequences

### Positive

- Scope dapat diselesaikan sebagai vertical slice.
- Data health dan lineage dibangun sebelum scoring.
- Tidak ada paid map dependency.
- Tooling tetap ringan dan dapat dijelaskan end to end.
- Architecture dapat berkembang ke RegulasiLens tanpa memaksakan document storage pada MVP regional.

### Negative

- Province-only MVP tidak menjawab kebutuhan lokasi granular.
- Scheduler ringan membutuhkan implementasi locking dan recovery sendiri.
- Postgres JSONB bukan storage ideal untuk corpus dokumen besar.
- Lima kontrak indikator selain TPT masih harus diverifikasi live sebelum Phase 2 ditutup.

## Revisit triggers

ADR ini harus ditinjau ulang jika:

- MVP memerlukan kabupaten/kota sebelum province release stabil.
- Workload melampaui threshold dataframe pada Section 5.
- Pipeline branching/backfill tidak lagi dapat dikelola worker sederhana.
- RegulasiLens corpus membuat raw storage tumbuh material.
- Local GeoJSON tidak memiliki license atau boundary version yang dapat dipublikasikan.

## References

- BPS WebAPI documentation: <https://webapi.bps.go.id/documentation/>
- BPS WebAPI portal: <https://webapi.bps.go.id/developer/>
- MapLibre GL JS documentation: <https://maplibre.org/maplibre-gl-js/docs/>
- MapLibre GL JS license: <https://github.com/maplibre/maplibre-gl-js/blob/main/LICENSE.txt>
- Prefect scheduling concepts: <https://docs.prefect.io/v3/concepts/schedules>
- APScheduler user guide: <https://apscheduler.readthedocs.io/en/master/userguide.html>
