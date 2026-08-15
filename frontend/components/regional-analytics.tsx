"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type ViewState = "loading" | "ready" | "empty" | "error";

interface Indicator {
  code: string;
  name: string;
  unit: string;
  periods: Array<{ period: string; coverage_percent: number }>;
}

interface Region {
  code: string;
  name: string;
}

interface Source {
  name: string;
  url: string;
  attribution: string;
}

interface AnalyticsReport {
  generated_at: string;
  methodology_version: string;
  target_region: {
    region_code: string;
    region_name: string;
  };
  similarity: {
    feature_set_version: string;
    preprocessing_version: string;
    selected_features: Array<{
      indicator_code: string;
      indicator_name: string;
      coverage: number;
      unit: string;
    }>;
    excluded_features: string[];
    excluded_regions: Array<{ code: string; name: string }>;
    results: Array<{
      region_code: string;
      region_name: string;
      distance: number;
      drivers: Array<{
        indicator_code: string;
        indicator_name: string;
        target_value: number;
        candidate_value: number;
        distance_share: number;
        unit: string;
      }>;
    }>;
  };
  clustering: {
    publishable: boolean;
    chosen_k: number | null;
    validation_message: string;
    candidate_evidence: Array<{
      k: number;
      silhouette: number;
      stability: number;
      minimum_cluster_size: number;
    }>;
    assignments: Array<{
      region_code: string;
      region_name: string;
      cluster_id: number;
    }>;
    clusters: Array<{
      cluster_id: number;
      description: string;
      regions: Array<{ code: string; name: string }>;
    }>;
  };
  map: {
    indicator_code: string;
    indicator_name: string;
    unit: string;
    disclaimer: string;
    values: Array<{
      region_code: string;
      region_name: string;
      value: number | null;
    }>;
  };
  citations: Array<{
    indicator_code: string;
    indicator_name: string;
    unit: string;
    source: Source;
    reference_period: string;
    dataset_version: { version_id: string };
  }>;
  limitations: string[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const preferredIndicators = ["tpt", "poverty_rate", "hdi"];
const tilePositions: Record<string, [number, number, string]> = {
  "1100": [1, 1, "AC"], "1200": [2, 2, "SU"], "1300": [2, 3, "SB"],
  "1400": [3, 3, "RI"], "1500": [3, 4, "JA"], "1600": [4, 4, "SS"],
  "1700": [3, 5, "BE"], "1800": [4, 5, "LA"], "1900": [5, 4, "BB"],
  "2100": [5, 2, "KR"], "3100": [5, 6, "JK"], "3200": [6, 6, "JB"],
  "3300": [7, 6, "JT"], "3400": [8, 7, "YO"], "3500": [8, 6, "JI"],
  "3600": [5, 7, "BT"], "5100": [9, 7, "BA"], "5200": [10, 7, "NB"],
  "5300": [11, 7, "NT"], "6100": [7, 3, "KB"], "6200": [8, 4, "KT"],
  "6300": [9, 4, "KS"], "6400": [9, 3, "KI"], "6500": [9, 2, "KU"],
  "7100": [11, 2, "SA"], "7200": [11, 4, "ST"], "7300": [11, 5, "SN"],
  "7400": [12, 5, "SG"], "7500": [10, 3, "GO"], "7600": [10, 5, "SR"],
  "8100": [13, 5, "MA"], "8200": [13, 3, "MU"], "9100": [15, 3, "PB"],
  "9200": [14, 3, "PD"], "9400": [16, 3, "PA"], "9500": [16, 6, "PS"],
  "9600": [15, 5, "PT"], "9700": [15, 4, "PP"],
};

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

function formatNumber(value: number | null, digits = 2): string {
  if (value === null || Number.isNaN(value)) return "Tidak tersedia";
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: digits }).format(value);
}

function commonYears(codes: string[], indicators: Indicator[]): number[] {
  const selected = codes
    .map((code) => indicators.find((indicator) => indicator.code === code))
    .filter((indicator): indicator is Indicator => Boolean(indicator));
  if (!selected.length) return [];
  const years = selected[0].periods.map((period) => Number(period.period.slice(0, 4)));
  return years
    .filter((year) =>
      selected.every((indicator) =>
        indicator.periods.some(
          (period) => Number(period.period.slice(0, 4)) === year && period.coverage_percent > 0,
        ),
      ),
    )
    .filter((year, index, all) => all.indexOf(year) === index)
    .sort((left, right) => right - left);
}

function quantileBreaks(values: number[]): number[] {
  const sorted = [...values].sort((left, right) => left - right);
  if (!sorted.length) return [];
  return [0.2, 0.4, 0.6, 0.8].map(
    (quantile) => sorted[Math.min(sorted.length - 1, Math.floor(quantile * sorted.length))],
  );
}

function valueBand(value: number | null, breaks: number[]): number {
  if (value === null || !breaks.length) return -1;
  const band = breaks.findIndex((boundary) => value <= boundary);
  return band === -1 ? 4 : band;
}

export function RegionalAnalytics() {
  const [state, setState] = useState<ViewState>("loading");
  const [indicators, setIndicators] = useState<Indicator[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [selected, setSelected] = useState<string[]>(preferredIndicators);
  const [target, setTarget] = useState("1100");
  const [year, setYear] = useState(2024);
  const [report, setReport] = useState<AnalyticsReport | null>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void Promise.all([
      fetchJson<{ items: Indicator[] }>("/api/v1/opportunity/indicators"),
      fetchJson<{ items: Region[] }>("/api/v1/opportunity/regions"),
    ])
      .then(([indicatorPayload, regionPayload]) => {
        if (!active) return;
        setIndicators(indicatorPayload.items);
        setRegions(regionPayload.items);
        if (indicatorPayload.items.length < 2 || !regionPayload.items.length) {
          setState("empty");
          return;
        }
        const available = new Set(indicatorPayload.items.map((item) => item.code));
        const defaults = preferredIndicators.filter((code) => available.has(code));
        setSelected(defaults.length >= 2 ? defaults : indicatorPayload.items.slice(0, 3).map((item) => item.code));
        setTarget(regionPayload.items.some((item) => item.code === "1100") ? "1100" : regionPayload.items[0].code);
        setState("ready");
      })
      .catch(() => active && setState("error"));
    return () => { active = false; };
  }, []);

  const years = useMemo(() => commonYears(selected, indicators), [selected, indicators]);
  const activeYear = years.includes(year) ? year : (years[0] ?? 0);
  const mapRows = useMemo(
    () => report?.map.values.map((row) => ({ ...row, tile: tilePositions[row.region_code] })) ?? [],
    [report],
  );
  const breaks = useMemo(
    () => quantileBreaks(mapRows.flatMap((row) => (row.value === null ? [] : [row.value]))),
    [mapRows],
  );

  function toggleIndicator(code: string) {
    setSelected((current) => {
      if (current.includes(code)) return current.length === 2 ? current : current.filter((item) => item !== code);
      return current.length === 6 ? current : [...current, code];
    });
    setReport(null);
  }

  async function runReport() {
    if (selected.length < 2 || !target || !activeYear) return;
    setRunning(true);
    setMessage(null);
    try {
      const next = await fetchJson<AnalyticsReport>("/api/v1/opportunity/analytics/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          indicator_codes: selected,
          year: activeYear,
          target_region_code: target,
          minimum_feature_coverage: 0.95,
          limit: 5,
        }),
      });
      setReport(next);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Analisis regional gagal.");
    } finally {
      setRunning(false);
    }
  }

  function downloadReport() {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `nusa-intel-regional-${target}-${activeYear}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  if (state !== "ready") {
    const copy = state === "loading" ? "Memuat Regional Analytics..." : state === "empty"
      ? "Data Gold belum cukup untuk analitik regional."
      : "Katalog analitik regional belum dapat dimuat.";
    return <section className="analytics-shell analytics-state">{copy}</section>;
  }

  return (
    <section className="analytics-shell" id="regional-analytics" aria-labelledby="analytics-title">
      <header className="analytics-header">
        <div>
          <p className="kicker">Release 0.4 / Regional Analytics</p>
          <h2 id="analytics-title">Temukan kemiripan tanpa mengubah deskripsi menjadi vonis.</h2>
          <p>
            Jarak profil, cluster tervalidasi, dan peta tile 38 provinsi disajikan bersama
            konfigurasi, versi fitur, sumber, serta keterbatasannya.
          </p>
        </div>
        <div className="scenario-actions no-print">
          <button className="secondary-button" type="button" disabled={!report} onClick={downloadReport}>Unduh JSON</button>
          <button className="secondary-button" type="button" disabled={!report} onClick={() => window.print()}>Cetak laporan</button>
        </div>
      </header>

      <div className="analytics-config no-print">
        <fieldset>
          <legend>Fitur pembanding (2-6)</legend>
          <div className="analytics-feature-list">
            {indicators.map((indicator) => (
              <label key={indicator.code}>
                <input type="checkbox" checked={selected.includes(indicator.code)} onChange={() => toggleIndicator(indicator.code)} />
                <span>{indicator.name}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <label>Provinsi acuan
          <select value={target} onChange={(event) => { setTarget(event.target.value); setReport(null); }}>
            {regions.map((region) => <option value={region.code} key={region.code}>{region.name}</option>)}
          </select>
        </label>
        <label>Tahun comparable
          <select value={activeYear} onChange={(event) => { setYear(Number(event.target.value)); setReport(null); }}>
            {years.map((candidate) => <option value={candidate} key={candidate}>{candidate}</option>)}
          </select>
        </label>
        <button className="primary-button" type="button" disabled={running || selected.length < 2 || !activeYear} onClick={() => void runReport()}>
          {running ? "Menghitung..." : "Jalankan analisis"}
        </button>
        {message && <p role="alert" className="analytics-message">{message}</p>}
      </div>

      {!report ? (
        <div className="analytics-placeholder">Pilih provinsi acuan dan jalankan analisis untuk membuat laporan yang dapat direproduksi.</div>
      ) : (
        <div className="analytics-report">
          <section className="analytics-evidence">
            <div><span>Provinsi acuan</span><strong>{report.target_region.region_name}</strong></div>
            <div><span>Feature set</span><code>{report.similarity.feature_set_version}</code></div>
            <div><span>Preprocessing</span><code>{report.similarity.preprocessing_version}</code></div>
            <div><span>Cakupan</span><strong>{report.similarity.selected_features.length} fitur / {38 - report.similarity.excluded_regions.length} provinsi</strong></div>
          </section>

          <section className="analytics-panel map-panel" aria-labelledby="map-title">
            <div className="result-heading"><div><p className="kicker">Schematic choropleth</p><h3 id="map-title">{report.map.indicator_name}</h3></div><span>{activeYear}</span></div>
            <p className="map-disclaimer">{report.map.disclaimer}</p>
            <div className="tile-map" aria-label={`Peta tile ${report.map.indicator_name}`}>
              {mapRows.map((row) => row.tile && (
                <button
                  type="button"
                  key={row.region_code}
                  className="province-tile no-print"
                  data-band={valueBand(row.value, breaks)}
                  data-selected={row.region_code === target}
                  style={{ gridColumn: row.tile[0], gridRow: row.tile[1] }}
                  title={`${row.region_name}: ${formatNumber(row.value)} ${report.map.unit}`}
                  aria-label={`${row.region_name}, ${formatNumber(row.value)} ${report.map.unit}`}
                  onClick={() => { setTarget(row.region_code); setReport(null); }}
                >{row.tile[2]}</button>
              ))}
            </div>
            <div className="map-legend" aria-label="Legenda kuantil">
              <span data-band="0">Lebih rendah</span><span data-band="1" /><span data-band="2" /><span data-band="3" /><span data-band="4">Lebih tinggi</span><span data-band="-1">Tidak ada data</span>
            </div>
            <details className="map-table">
              <summary>Alternatif tabel aksesibel (38 provinsi)</summary>
              <div className="table-scroll" tabIndex={0} aria-label="Tabel nilai peta dapat digulir"><table><caption>Nilai yang sama dengan peta tile.</caption><thead><tr><th>Provinsi</th><th>Nilai</th><th>Unit</th></tr></thead><tbody>
                {mapRows.map((row) => <tr key={row.region_code}><th scope="row">{row.region_name}</th><td>{formatNumber(row.value)}</td><td>{report.map.unit}</td></tr>)}
              </tbody></table></div>
            </details>
          </section>

          <div className="analytics-columns">
            <section className="analytics-panel">
              <div className="result-heading"><div><p className="kicker">Distance search</p><h3>Wilayah paling mirip</h3></div></div>
              <ol className="similarity-list">
                {report.similarity.results.map((row) => (
                  <li key={row.region_code}>
                    <div><Link href={`/regions/${row.region_code}?year=${activeYear}`}>{row.region_name}</Link><strong>jarak {formatNumber(row.distance, 3)}</strong></div>
                    <ul>{row.drivers.slice(0, 3).map((driver) => <li key={driver.indicator_code}>{driver.indicator_name}: {formatNumber(driver.distance_share * 100, 1)}% jarak ({formatNumber(driver.target_value)} vs {formatNumber(driver.candidate_value)} {driver.unit})</li>)}</ul>
                  </li>
                ))}
              </ol>
              <Link className="detail-link" href={`/regions/${target}?year=${activeYear}`}>Buka detail {report.target_region.region_name}</Link>
            </section>

            <section className="analytics-panel">
              <div className="result-heading"><div><p className="kicker">Validation evidence</p><h3>Cluster regional</h3></div></div>
              {!report.clustering.publishable ? <p className="withheld-result">Keanggotaan cluster tidak ditampilkan. {report.clustering.validation_message}</p> : <>
                <p className="cluster-summary">Model terpilih: k={report.clustering.chosen_k}. Label bersifat deskriptif dan non-normatif.</p>
                <div className="cluster-list">{report.clustering.clusters.map((cluster) => <article key={cluster.cluster_id}><strong>Cluster {cluster.cluster_id}</strong><p>{cluster.description}</p><small>{cluster.regions.length} provinsi</small></article>)}</div>
              </>}
              <div className="table-scroll" tabIndex={0} aria-label="Tabel evidence cluster dapat digulir"><table><caption>Evidence seluruh kandidat k.</caption><thead><tr><th>k</th><th>Silhouette</th><th>Stability</th><th>Min. anggota</th></tr></thead><tbody>
                {report.clustering.candidate_evidence.map((row) => <tr key={row.k}><td>{row.k}</td><td>{formatNumber(row.silhouette, 3)}</td><td>{formatNumber(row.stability, 3)}</td><td>{row.minimum_cluster_size}</td></tr>)}
              </tbody></table></div>
            </section>
          </div>

          <section className="analytics-panel methodology-panel">
            <div className="result-heading"><div><p className="kicker">Audit trail</p><h3>Metodologi, sumber, dan batas penggunaan</h3></div><span>{report.methodology_version}</span></div>
            <div className="methodology-grid">
              <div><h4>Sumber</h4><ul>{report.citations.map((citation) => <li key={citation.indicator_code}><a href={citation.source.url} target="_blank" rel="noreferrer">{citation.indicator_name}</a> — {citation.unit}; periode {citation.reference_period}; versi <code>{citation.dataset_version.version_id}</code></li>)}</ul></div>
              <div><h4>Keterbatasan</h4><ul>{report.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></div>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
