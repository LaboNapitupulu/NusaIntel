"use client";

import { useEffect, useState } from "react";

type Status = "loading" | "healthy" | "degraded" | "offline";

interface HealthPayload {
  status: "healthy" | "degraded";
  dependencies: {
    database: { status: "ready" | "unavailable" };
  };
}

const labels: Record<Status, string> = {
  loading: "Memeriksa kesiapan layanan",
  healthy: "Semua fitur siap digunakan",
  degraded: "Sebagian fitur belum siap",
  offline: "Layanan sedang tidak tersedia",
};

async function fetchHealth(apiBaseUrl: string): Promise<Status> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    const payload = (await response.json()) as HealthPayload;
    return payload.status === "healthy" ? "healthy" : "degraded";
  } catch {
    return "offline";
  }
}

export function SystemStatus() {
  const [status, setStatus] = useState<Status>("loading");
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  const checkHealth = () => {
    setStatus("loading");
    void fetchHealth(apiBaseUrl).then(setStatus);
  };

  useEffect(() => {
    let active = true;
    void fetchHealth(apiBaseUrl).then((nextStatus) => {
      if (active) setStatus(nextStatus);
    });
    return () => {
      active = false;
    };
  }, [apiBaseUrl]);

  return (
    <aside className="status-panel" data-tilt data-reveal aria-live="polite">
      <div className="status-heading">
        <span className={`status-dot status-${status}`} aria-hidden="true" />
        <span>{labels[status]}</span>
      </div>
      <p>
        Anda dapat mulai menjelajahi data, membandingkan wilayah, dan mencari regulasi.
      </p>
      {(status === "degraded" || status === "offline") && (
        <button type="button" onClick={checkHealth}>
          Periksa ulang
        </button>
      )}
    </aside>
  );
}
