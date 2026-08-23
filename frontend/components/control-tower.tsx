"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AnimatedNumber, EmptyState, WorkspaceSkeleton, WorkspaceTabs, WorkspaceToast } from "./workspace-ui";

type Health = "healthy" | "warning" | "critical" | "unknown";
type LoadState = "loading" | "ready" | "empty" | "error";
type TowerTab = "overview" | "quality" | "incidents";

interface DatasetSummary {
  id: string;
  code: string;
  name: string;
  layer: string;
  owner: string;
  health: Health;
  freshness: {
    status: "fresh" | "stale" | "unknown";
    source_reference_at: string | null;
    retrieved_at: string | null;
    processed_at: string | null;
  };
  latest_version_status: string | null;
  last_known_good_version_id: string | null;
  open_incident_count: number;
  failed_check_count: number;
}

interface DatasetDetail extends DatasetSummary {
  contract: { version: number; checksum: string } | null;
  schema_drift: Array<{
    id: string;
    change_type: string;
    column_name: string;
  }>;
}

interface QualityCheck {
  id: string;
  check_code: string;
  severity: "info" | "warning" | "critical";
  status: "passed" | "failed" | "waived";
  contract_version: number | null;
  observed: Record<string, unknown> | null;
  created_at: string;
}

interface Incident {
  id: string;
  dataset_code: string;
  check_code: string;
  status: string;
  title: string;
  resolution_note: string | null;
  created_at: string;
}

const healthLabels: Record<Health, string> = {
  healthy: "Sehat",
  warning: "Perlu perhatian",
  critical: "Kritis",
  unknown: "Belum ada data",
};

const freshnessLabels: Record<DatasetSummary["freshness"]["status"], string> = {
  fresh: "Terkini",
  stale: "Perlu diperbarui",
  unknown: "Belum diketahui",
};

const checkStatusLabels: Record<QualityCheck["status"], string> = {
  passed: "Lulus",
  failed: "Perlu diperiksa",
  waived: "Dikecualikan",
};

function readableCheckName(value: string): string {
  const label = value.replaceAll("_", " ").replaceAll("-", " ").trim();
  return label ? label.charAt(0).toLocaleUpperCase("id-ID") + label.slice(1) : "Pemeriksaan data";
}

function displayDatasetName(value: string): string {
  return value.replace(/\s+(raw|normalized|curated)$/i, "").trim();
}

function formatTime(value: string | null): string {
  if (!value) return "Belum tersedia";
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Jakarta",
  }).format(new Date(value));
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: "no-store", ...init });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return (await response.json()) as T;
}

async function fetchOverview(apiBaseUrl: string) {
  return Promise.all([
    fetchJson<{ items: DatasetSummary[] }>(`${apiBaseUrl}/api/v1/datasets`),
    fetchJson<{ items: Incident[] }>(`${apiBaseUrl}/api/v1/incidents?limit=12`),
  ]);
}

function preferredDatasetId(datasets: DatasetSummary[]): string | null {
  return datasets.find((dataset) => dataset.layer === "silver")?.id ?? datasets[0]?.id ?? null;
}

export function ControlTower() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const [state, setState] = useState<LoadState>("loading");
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DatasetDetail | null>(null);
  const [quality, setQuality] = useState<QualityCheck[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [severityFilter, setSeverityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [resolutionNotes, setResolutionNotes] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<TowerTab>("overview");
  const [datasetQuery, setDatasetQuery] = useState("");
  const [healthFilter, setHealthFilter] = useState<Health | "all">("all");
  const [toast, setToast] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    try {
      const [datasetPayload, incidentPayload] = await fetchOverview(apiBaseUrl);
      setDatasets(datasetPayload.items);
      setIncidents(incidentPayload.items);
      setSelectedId((current) => current ?? preferredDatasetId(datasetPayload.items));
      setState(datasetPayload.items.length ? "ready" : "empty");
    } catch {
      setState("error");
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    let active = true;
    void fetchOverview(apiBaseUrl)
      .then(([datasetPayload, incidentPayload]) => {
        if (!active) return;
        setDatasets(datasetPayload.items);
        setIncidents(incidentPayload.items);
        setSelectedId(preferredDatasetId(datasetPayload.items));
        setState(datasetPayload.items.length ? "ready" : "empty");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl]);

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    let active = true;
    void Promise.all([
      fetchJson<DatasetDetail>(`${apiBaseUrl}/api/v1/datasets/${selectedId}`),
      fetchJson<{ items: QualityCheck[] }>(
        `${apiBaseUrl}/api/v1/datasets/${selectedId}/quality?limit=100`,
      ),
    ])
      .then(([nextDetail, qualityPayload]) => {
        if (!active) return;
        setDetail(nextDetail);
        setQuality(qualityPayload.items);
      })
      .catch(() => {
        if (active) setDetail(null);
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, selectedId]);

  const filteredQuality = useMemo(
    () =>
      quality.filter(
        (check) =>
          (severityFilter === "all" || check.severity === severityFilter) &&
          (statusFilter === "all" || check.status === statusFilter),
      ),
    [quality, severityFilter, statusFilter],
  );

  const filteredDatasets = useMemo(() => {
    const query = datasetQuery.trim().toLocaleLowerCase("id-ID");
    return datasets.filter(
      (dataset) =>
        (healthFilter === "all" || dataset.health === healthFilter) &&
        (!query || `${dataset.name} ${dataset.code} ${dataset.layer}`.toLocaleLowerCase("id-ID").includes(query)),
    );
  }, [datasetQuery, datasets, healthFilter]);

  const healthSummary = useMemo(
    () => ({
      healthy: datasets.filter((dataset) => dataset.health === "healthy").length,
      warning: datasets.filter((dataset) => dataset.health === "warning").length,
      critical: datasets.filter((dataset) => dataset.health === "critical").length,
    }),
    [datasets],
  );

  const resolveIncident = async (incident: Incident) => {
    const note = resolutionNotes[incident.id]?.trim();
    if (!note) return;
    try {
      await fetchJson(`${apiBaseUrl}/api/v1/incidents/${incident.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "resolved", resolution_note: note }),
      });
      await loadOverview();
      setToast(`Insiden ${incident.check_code} ditandai selesai.`);
    } catch {
      setToast("Insiden belum dapat diperbarui. Coba lagi.");
    }
  };

  return (
    <section className="control-tower" id="control-tower" aria-labelledby="tower-title">
      <div className="tower-heading">
        <div>
          <p className="kicker">Pusat kualitas data</p>
          <h2 id="tower-title">Ketahui data yang siap Anda gunakan.</h2>
        </div>
        <p>
          Lihat keterbaruan, hasil pemeriksaan, dan kendala pada setiap sumber data dalam satu
          tampilan yang mudah dipahami.
        </p>
      </div>

      {state === "ready" && (
        <section className="health-overview" aria-label="Ringkasan kesehatan data">
          <article data-health="healthy" data-tilt data-reveal><span>Data siap</span><strong><AnimatedNumber value={healthSummary.healthy} initialFrom={0} /></strong><small>dapat digunakan</small></article>
          <article data-health="warning" data-tilt data-reveal><span>Perlu perhatian</span><strong><AnimatedNumber value={healthSummary.warning} initialFrom={0} /></strong><small>periksa kualitas</small></article>
          <article data-health="critical" data-tilt data-reveal><span>Belum dapat digunakan</span><strong><AnimatedNumber value={healthSummary.critical} initialFrom={0} /></strong><small>menunggu perbaikan</small></article>
          <article data-health="incidents" data-tilt data-reveal><span>Kendala aktif</span><strong><AnimatedNumber value={incidents.filter((item) => item.status === "open").length} initialFrom={0} /></strong><small>sedang ditindaklanjuti</small></article>
        </section>
      )}

      {state === "loading" && <WorkspaceSkeleton label="Memuat katalog data" />}
      {state === "error" && (
        <div className="tower-state tower-error" role="alert">
          <p>Control Tower belum dapat dijangkau.</p>
          <button type="button" onClick={() => { setState("loading"); void loadOverview(); }}>Coba lagi</button>
        </div>
      )}
      {state === "empty" && (
        <p className="tower-state">Belum ada data yang dapat ditampilkan saat ini.</p>
      )}

      {state === "ready" && (
        <div className="tower-shell">
          <aside className="dataset-catalog" aria-label="Daftar sumber data">
            <div className="panel-title">
              <span>Daftar data</span>
              <strong>{datasets.length}</strong>
            </div>
            <div className="catalog-toolbar">
              <label>
                <span className="sr-only">Cari data</span>
                <input
                  type="search"
                  placeholder="Cari nama data…"
                  value={datasetQuery}
                  onChange={(event) => setDatasetQuery(event.target.value)}
                />
              </label>
              <label>
                <span className="sr-only">Filter kesehatan</span>
                <select value={healthFilter} onChange={(event) => setHealthFilter(event.target.value as Health | "all")}>
                  <option value="all">Semua status</option>
                  <option value="healthy">Sehat</option>
                  <option value="warning">Perlu perhatian</option>
                  <option value="critical">Kritis</option>
                </select>
              </label>
            </div>
            <div className="dataset-list">
              {filteredDatasets.map((dataset) => (
                <button
                  className={`dataset-row ${selectedId === dataset.id ? "dataset-active" : ""}`}
                  data-tilt
                  key={dataset.id}
                  type="button"
                  onClick={() => {
                    setDetail(null);
                    setSelectedId(dataset.id);
                  }}
                  aria-pressed={selectedId === dataset.id}
                >
                  <span className={`health-pill health-${dataset.health}`}>
                    {healthLabels[dataset.health]}
                  </span>
                  <strong>{displayDatasetName(dataset.name)}</strong>
                  <span>Dikelola oleh {dataset.owner}</span>
                </button>
              ))}
              {!filteredDatasets.length && (
                <EmptyState
                  eyebrow="Tidak ditemukan"
                  title="Tidak ada data yang cocok"
                  description="Ubah kata pencarian atau tampilkan kembali semua status."
                />
              )}
            </div>
          </aside>

          <div className="tower-content">
            {detail ? (
              <>
                <section className="dataset-overview" aria-labelledby="dataset-title">
                  <div>
                    <p className="card-eyebrow">Ringkasan data</p>
                    <h3 id="dataset-title">{displayDatasetName(detail.name)}</h3>
                    <p className="version-note">Status saat ini: {healthLabels[detail.health]}</p>
                  </div>
                  <div className="metric-grid">
                    <div><span>Keterbaruan</span><strong>{freshnessLabels[detail.freshness.status]}</strong></div>
                    <div><span>Periode data</span><strong>{formatTime(detail.freshness.source_reference_at)}</strong></div>
                    <div><span>Terakhir diperbarui</span><strong>{formatTime(detail.freshness.retrieved_at)}</strong></div>
                    <div><span>Siap digunakan sejak</span><strong>{formatTime(detail.freshness.processed_at)}</strong></div>
                    <div><span>Temuan kualitas</span><strong>{detail.failed_check_count}</strong></div>
                    <div><span>Kendala aktif</span><strong>{detail.open_incident_count}</strong></div>
                  </div>
                </section>

                <WorkspaceTabs
                  label="Area Control Tower"
                  active={activeTab}
                  onChange={setActiveTab}
                  tabs={[
                    { id: "overview", label: "Ringkasan" },
                    { id: "quality", label: "Pemeriksaan", count: quality.filter((item) => item.status === "failed").length },
                    { id: "incidents", label: "Kendala", count: incidents.filter((item) => item.status === "open").length },
                  ]}
                />

                <div className="tower-grid" hidden={activeTab === "incidents"}>
                  <section className="tower-panel quality-panel" aria-labelledby="quality-title" hidden={activeTab !== "quality"}>
                    <div className="panel-title">
                      <span id="quality-title">Hasil pemeriksaan</span>
                      <strong>{filteredQuality.length}</strong>
                    </div>
                    <div className="filter-row">
                      <label>Tingkat perhatian
                        <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
                          <option value="all">Semua</option><option value="critical">Mendesak</option>
                          <option value="warning">Perlu perhatian</option><option value="info">Informasi</option>
                        </select>
                      </label>
                      <label>Status
                        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                          <option value="all">Semua</option><option value="failed">Perlu diperiksa</option>
                          <option value="passed">Lulus</option><option value="waived">Dikecualikan</option>
                        </select>
                      </label>
                    </div>
                    <div className="check-list">
                      {filteredQuality.slice(0, 12).map((check) => (
                        <article className="check-row" key={check.id}>
                          <span className={`check-status check-${check.status}`}>{checkStatusLabels[check.status]}</span>
                          <div><strong>{readableCheckName(check.check_code)}</strong><span>{check.severity === "critical" ? "Mendesak" : check.severity === "warning" ? "Perlu perhatian" : "Informasi"}</span></div>
                        </article>
                      ))}
                      {!filteredQuality.length && <p className="empty-copy">Tidak ada hasil pemeriksaan pada filter ini.</p>}
                    </div>
                  </section>

                  <section className="tower-panel tower-overview-panel" aria-labelledby="drift-title" hidden={activeTab !== "overview"}>
                    <div className="panel-title"><span id="drift-title">Konsistensi format</span><strong>{detail.schema_drift.length}</strong></div>
                    {detail.schema_drift.length
                      ? <p className="empty-copy">Ada {detail.schema_drift.length} perubahan format yang perlu diperiksa sebelum data digunakan.</p>
                      : <p className="empty-copy">Format data konsisten dengan pembaruan sebelumnya.</p>}
                  </section>
                </div>
              </>
            ) : <p className="tower-state">Memuat rincian data…</p>}
          </div>
        </div>
      )}

      {state === "ready" && activeTab === "incidents" && (
      <div className="operations-grid operations-focus">
        <section className="tower-panel" aria-labelledby="incident-title" hidden={activeTab !== "incidents"}>
          <div className="panel-title"><span id="incident-title">Kendala data</span><strong>{incidents.length}</strong></div>
          {incidents.map((incident) => (
            <article className="incident-row" key={incident.id}>
              <div><strong>{readableCheckName(incident.check_code)}</strong><span>{displayDatasetName(datasets.find((item) => item.code === incident.dataset_code)?.name ?? "Data terkait")} · {incident.status === "open" ? "Dalam penanganan" : "Selesai"}</span></div>
              {incident.status !== "resolved" && incident.status !== "ignored-with-reason" ? (
                <div className="resolution-form">
                  <label htmlFor={`note-${incident.id}`}>Catatan resolusi</label>
                  <input id={`note-${incident.id}`} value={resolutionNotes[incident.id] ?? ""} onChange={(event) => setResolutionNotes((current) => ({ ...current, [incident.id]: event.target.value }))} />
                  <button type="button" onClick={() => void resolveIncident(incident)}>Tandai selesai</button>
                </div>
              ) : <p>{incident.resolution_note}</p>}
            </article>
          ))}
          {!incidents.length && <p className="empty-copy">Tidak ada insiden tercatat.</p>}
        </section>
      </div>
      )}
      <WorkspaceToast message={toast} onDismiss={() => setToast(null)} />
    </section>
  );
}
