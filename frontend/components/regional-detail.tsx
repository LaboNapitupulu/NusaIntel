"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

interface RegionDetailResponse {
  region_code: string;
  region_name: string;
  year: number;
  indicators: Array<{
    indicator_code: string;
    indicator_name: string;
    definition: string;
    value: number | null;
    missing: boolean;
    unit: string;
    reference_period: string;
    source: { name: string; url: string; attribution: string };
    dataset_version: { version_id: string };
  }>;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function formatNumber(value: number | null): string {
  if (value === null) return "Tidak tersedia";
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 }).format(value);
}

export function RegionalDetail({ code, year }: { code: string; year: number }) {
  const [detail, setDetail] = useState<RegionDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    void fetch(`${API_BASE_URL}/api/v1/opportunity/regions/${code}?year=${year}`, {
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) {
          const body = (await response.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail ?? `Request failed: ${response.status}`);
        }
        return response.json() as Promise<RegionDetailResponse>;
      })
      .then((payload) => active && setDetail(payload))
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Detail gagal dimuat.");
      });
    return () => { active = false; };
  }, [code, year, attempt]);

  if (error) return <main className="detail-page" id="main-content"><h1>Rincian wilayah</h1><p role="alert">Rincian wilayah belum dapat dimuat.</p><button type="button" onClick={() => { setError(null); setAttempt((current) => current + 1); }}>Coba lagi</button><p><Link href="/regional-analytics">Kembali ke analisis wilayah</Link></p></main>;
  if (!detail) return <main className="detail-page" id="main-content"><h1>Rincian wilayah</h1><p role="status">Memuat rincian wilayah…</p></main>;

  return (
    <main className="detail-page" id="main-content">
      <nav aria-label="Jejak navigasi"><Link href="/regional-analytics">Analisis wilayah</Link> / Rincian provinsi</nav>
      <header>
        <p className="kicker">Rincian wilayah · {detail.year}</p>
        <h1>{detail.region_name}</h1>
        <p>Lihat nilai indikator, periode pengukuran, dan sumber resmi untuk wilayah ini.</p>
      </header>
      <section className="detail-indicator-grid" aria-label="Indikator regional">
        {detail.indicators.map((indicator) => (
          <article key={indicator.indicator_code}>
            <span>{indicator.indicator_code}</span>
            <h2>{indicator.indicator_name}</h2>
            <strong>{formatNumber(indicator.value)} <small>{indicator.unit}</small></strong>
            <p>{indicator.definition}</p>
            <dl>
              <div><dt>Periode referensi</dt><dd>{indicator.reference_period}</dd></div>
              <div><dt>Sumber</dt><dd><a href={indicator.source.url} target="_blank" rel="noreferrer">{indicator.source.name}</a></dd></div>
            </dl>
          </article>
        ))}
      </section>
      <aside className="detail-limitation">Nilai ini bersifat deskriptif. Perbedaan antardaerah tidak membuktikan hubungan sebab-akibat.</aside>
    </main>
  );
}
