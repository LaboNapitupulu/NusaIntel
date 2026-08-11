"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Health = "healthy" | "warning" | "critical" | "unknown";
type LoadState = "loading" | "ready" | "empty" | "error";

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

interface PipelineRun {
  id: string;
  dataset_code: string | null;
  status: string;
  started_at: string;
  finished_at: string | null;
  error_category: string | null;
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

interface LineagePayload {
  nodes: Array<{
    version_id: string;
    dataset_code: string;
    layer: string;
    status: string;
  }>;
  edges: Array<{
    id: string;
    upstream_version_id: string;
    downstream_version_id: string;
    transformation_version: string;
  }>;
}

const healthLabels: Record<Health, string> = {
  healthy: "Sehat",
  warning: "Perlu perhatian",
  critical: "Kritis",
  unknown: "Belum ada data",
};

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
    fetchJson<{ items: PipelineRun[] }>(`${apiBaseUrl}/api/v1/pipeline-runs?limit=12`),
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
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [lineage, setLineage] = useState<LineagePayload>({ nodes: [], edges: [] });
  const [severityFilter, setSeverityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [resolutionNotes, setResolutionNotes] = useState<Record<string, string>>({});

  const loadOverview = useCallback(async () => {
    try {
      const [datasetPayload, runPayload, incidentPayload] = await fetchOverview(apiBaseUrl);
      setDatasets(datasetPayload.items);
      setRuns(runPayload.items);
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
      .then(([datasetPayload, runPayload, incidentPayload]) => {
        if (!active) return;
        setDatasets(datasetPayload.items);
        setRuns(runPayload.items);
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
      fetchJson<LineagePayload>(`${apiBaseUrl}/api/v1/lineage/${selectedId}`),
    ])
      .then(([nextDetail, qualityPayload, lineagePayload]) => {
        if (!active) return;
        setDetail(nextDetail);
        setQuality(qualityPayload.items);
        setLineage(lineagePayload);
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

  const resolveIncident = async (incident: Incident) => {
    const note = resolutionNotes[incident.id]?.trim();
    if (!note) return;
    await fetchJson(`${apiBaseUrl}/api/v1/incidents/${incident.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "resolved", resolution_note: note }),
    });
    await loadOverview();
  };

  return (
    <section className="control-tower" id="control-tower" aria-labelledby="tower-title">
      <div className="tower-heading">
        <div>
          <p className="kicker">Release 0.2 / Control Tower Lite</p>
          <h2 id="tower-title">Keadaan data, tanpa area abu-abu.</h2>
        </div>
        <p>
          Kontrak, freshness, pemeriksaan, lineage, dan insiden berada dalam satu jejak audit.
          Kegagalan kritis menghentikan publish tanpa menghapus versi terakhir yang baik.
        </p>
      </div>

      {state === "loading" && <p className="tower-state" role="status">Memuat katalog data…</p>}
      {state === "error" && (
        <div className="tower-state tower-error" role="alert">
          <p>Control Tower belum dapat dijangkau.</p>
          <button type="button" onClick={() => { setState("loading"); void loadOverview(); }}>Coba lagi</button>
        </div>
      )}
      {state === "empty" && (
        <p className="tower-state">Belum ada dataset. Jalankan pipeline BPS untuk mengisi katalog.</p>
      )}

      {state === "ready" && (
        <div className="tower-shell">
          <aside className="dataset-catalog" aria-label="Katalog dataset">
            <div className="panel-title">
              <span>Dataset catalog</span>
              <strong>{datasets.length}</strong>
            </div>
            <div className="dataset-list">
              {datasets.map((dataset) => (
                <button
                  className={`dataset-row ${selectedId === dataset.id ? "dataset-active" : ""}`}
                  key={dataset.id}
                  type="button"
                  onClick={() => setSelectedId(dataset.id)}
                  aria-pressed={selectedId === dataset.id}
                >
                  <span className={`health-pill health-${dataset.health}`}>
                    {healthLabels[dataset.health]}
                  </span>
                  <strong>{dataset.name}</strong>
                  <span>{dataset.layer} · {dataset.owner}</span>
                </button>
              ))}
            </div>
          </aside>

          <div className="tower-content">
            {detail ? (
              <>
                <section className="dataset-overview" aria-labelledby="dataset-title">
                  <div>
                    <p className="card-eyebrow">{detail.layer} / {detail.code}</p>
                    <h3 id="dataset-title">{detail.name}</h3>
                    <p className="version-note">
                      Last-known-good: {detail.last_known_good_version_id?.slice(0, 8) ?? "belum ada"}
                    </p>
                  </div>
                  <div className="metric-grid">
                    <div><span>Freshness</span><strong>{detail.freshness.status}</strong></div>
                    <div><span>Reference period</span><strong>{formatTime(detail.freshness.source_reference_at)}</strong></div>
                    <div><span>Retrieved</span><strong>{formatTime(detail.freshness.retrieved_at)}</strong></div>
                    <div><span>Processed</span><strong>{formatTime(detail.freshness.processed_at)}</strong></div>
                    <div><span>Contract</span><strong>v{detail.contract?.version ?? "–"}</strong></div>
                    <div><span>Open incidents</span><strong>{detail.open_incident_count}</strong></div>
                  </div>
                </section>

                <div className="tower-grid">
                  <section className="tower-panel quality-panel" aria-labelledby="quality-title">
                    <div className="panel-title">
                      <span id="quality-title">Quality checks</span>
                      <strong>{filteredQuality.length}</strong>
                    </div>
                    <div className="filter-row">
                      <label>Severity
                        <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
                          <option value="all">Semua</option><option value="critical">Critical</option>
                          <option value="warning">Warning</option><option value="info">Info</option>
                        </select>
                      </label>
                      <label>Status
                        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                          <option value="all">Semua</option><option value="failed">Failed</option>
                          <option value="passed">Passed</option><option value="waived">Waived</option>
                        </select>
                      </label>
                    </div>
                    <div className="check-list">
                      {filteredQuality.slice(0, 12).map((check) => (
                        <article className="check-row" key={check.id}>
                          <span className={`check-status check-${check.status}`}>{check.status}</span>
                          <div><strong>{check.check_code}</strong><span>{check.severity} · contract v{check.contract_version ?? "–"}</span></div>
                        </article>
                      ))}
                      {!filteredQuality.length && <p className="empty-copy">Tidak ada check pada filter ini.</p>}
                    </div>
                  </section>

                  <section className="tower-panel" aria-labelledby="drift-title">
                    <div className="panel-title"><span id="drift-title">Schema drift</span><strong>{detail.schema_drift.length}</strong></div>
                    {detail.schema_drift.length ? detail.schema_drift.slice(0, 8).map((drift) => (
                      <article className="event-row" key={drift.id}><strong>{drift.column_name}</strong><span>{drift.change_type}</span></article>
                    )) : <p className="empty-copy">Tidak ada perubahan schema terdeteksi.</p>}
                  </section>

                  <section className="tower-panel" aria-labelledby="lineage-title">
                    <div className="panel-title"><span id="lineage-title">Lineage</span><strong>{lineage.edges.length}</strong></div>
                    <ol className="lineage-list">
                      {lineage.nodes.map((node) => (
                        <li key={node.version_id}><span>{node.layer}</span><strong>{node.dataset_code}</strong><small>{node.status}</small></li>
                      ))}
                    </ol>
                    {!lineage.nodes.length && <p className="empty-copy">Lineage belum tersedia untuk versi ini.</p>}
                  </section>
                </div>
              </>
            ) : <p className="tower-state">Memuat detail dataset…</p>}
          </div>
        </div>
      )}

      <div className="operations-grid">
        <section className="tower-panel" aria-labelledby="runs-title">
          <div className="panel-title"><span id="runs-title">Pipeline runs</span><strong>{runs.length}</strong></div>
          {runs.map((run) => (
            <article className="event-row" key={run.id}>
              <div><strong>{run.dataset_code ?? "unassigned"}</strong><span>{formatTime(run.started_at)}</span></div>
              <span className={`check-status check-${run.status}`}>{run.status}</span>
            </article>
          ))}
          {!runs.length && <p className="empty-copy">Belum ada histori pipeline.</p>}
        </section>

        <section className="tower-panel" aria-labelledby="incident-title">
          <div className="panel-title"><span id="incident-title">Incidents</span><strong>{incidents.length}</strong></div>
          {incidents.map((incident) => (
            <article className="incident-row" key={incident.id}>
              <div><strong>{incident.title}</strong><span>{incident.dataset_code} · {incident.status}</span></div>
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
    </section>
  );
}
