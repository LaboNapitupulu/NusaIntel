import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RegionalAnalytics } from "./regional-analytics";

function response(payload: unknown): Response {
  return { ok: true, json: async () => payload } as Response;
}

const indicators = [
  { code: "tpt", name: "Tingkat Pengangguran Terbuka", unit: "Persen", periods: [{ period: "2024-08-01", coverage_percent: 100 }] },
  { code: "poverty_rate", name: "Persentase Penduduk Miskin", unit: "Persen", periods: [{ period: "2024-03-01", coverage_percent: 100 }] },
  { code: "hdi", name: "Indeks Pembangunan Manusia", unit: "Poin", periods: [{ period: "2024-12-01", coverage_percent: 100 }] },
];

const codes = [
  "1100", "1200", "1300", "1400", "1500", "1600", "1700", "1800", "1900", "2100",
  "3100", "3200", "3300", "3400", "3500", "3600", "5100", "5200", "5300", "6100",
  "6200", "6300", "6400", "6500", "7100", "7200", "7300", "7400", "7500", "7600",
  "8100", "8200", "9100", "9200", "9400", "9500", "9600", "9700",
];
const regions = codes.map((code, index) => ({ code, name: index === 0 ? "ACEH" : `PROVINSI ${index + 1}` }));

const report = {
  generated_at: "2026-08-11T00:00:00Z",
  methodology_version: "regional-analytics-v1",
  target_region: { region_code: "1100", region_name: "ACEH" },
  similarity: {
    feature_set_version: "feature-set-123",
    preprocessing_version: "zscore-complete-case-v1",
    selected_features: indicators.map((item) => ({ ...item, indicator_code: item.code, indicator_name: item.name, coverage: 1 })),
    excluded_features: [],
    excluded_regions: [],
    results: [{
      region_code: "1200", region_name: "PROVINSI 2", distance: 0.125,
      drivers: [{ indicator_code: "hdi", indicator_name: "Indeks Pembangunan Manusia", target_value: 75, candidate_value: 74, distance_share: 0.6, unit: "Poin" }],
    }],
  },
  clustering: {
    publishable: true,
    chosen_k: 2,
    validation_message: "published",
    candidate_evidence: [{ k: 2, silhouette: 0.41, stability: 0.92, minimum_cluster_size: 12 }],
    assignments: regions.map((region, index) => ({ region_code: region.code, region_name: region.name, cluster_id: index % 2 })),
    clusters: [{ cluster_id: 0, description: "Relatif lebih tinggi pada HDI.", regions: regions.slice(0, 19) }],
  },
  map: {
    indicator_code: "tpt", indicator_name: "Tingkat Pengangguran Terbuka", unit: "Persen",
    disclaimer: "Tile positions are schematic and are not official administrative boundaries.",
    values: regions.map((region, index) => ({ region_code: region.code, region_name: region.name, value: index === 37 ? null : index + 1 })),
  },
  citations: indicators.map((item) => ({
    indicator_code: item.code, indicator_name: item.name, unit: item.unit,
    source: { name: "BPS", url: "https://www.bps.go.id/", attribution: "BPS" },
    reference_period: "2024-08-01", dataset_version: { version_id: `version-${item.code}` },
  })),
  limitations: ["Similarity describes profiles, not causality.", "Cluster descriptions are neutral."],
};

afterEach(() => vi.restoreAllMocks());

describe("RegionalAnalytics", () => {
  it("renders a reproducible, accessible map and evidence report", async () => {
    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/opportunity/indicators")) return response({ items: indicators });
      if (url.endsWith("/opportunity/regions")) return response({ items: regions });
      return response(report);
    });

    render(<RegionalAnalytics />);
    fireEvent.click(await screen.findByRole("button", { name: "Jalankan analisis" }));

    expect(await screen.findByText("feature-set-123")).toBeInTheDocument();
    expect(screen.getByText(/not official administrative boundaries/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ACEH, 1 Persen" })).toHaveAttribute("data-band", "0");
    expect(screen.getByRole("button", { name: "PROVINSI 38, Tidak tersedia Persen" })).toHaveAttribute("data-band", "-1");
    expect(screen.getByText("Alternatif tabel aksesibel (38 provinsi)")).toBeInTheDocument();
    const table = screen.getByText("Nilai yang sama dengan peta tile.").closest("table");
    expect(table).not.toBeNull();
    expect(within(table!).getAllByRole("row")).toHaveLength(39);
    fireEvent.click(screen.getByRole("tab", { name: /Similarity/ }));
    expect(screen.getAllByRole("link", { name: /PROVINSI 2/ })[0]).toHaveAttribute("href", "/regions/1200?year=2024");
    fireEvent.click(screen.getByRole("tab", { name: /Cluster/ }));
    expect(screen.getByText("Evidence seluruh kandidat k.")).toBeInTheDocument();
    expect(screen.getByText(/Relatif lebih tinggi pada HDI/)).toBeInTheDocument();
    expect(screen.queryByText(/terbaik|terburuk|tertinggal/i)).not.toBeInTheDocument();

  });

  it("does not expose memberships when validation is weak", async () => {
    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/opportunity/indicators")) return response({ items: indicators });
      if (url.endsWith("/opportunity/regions")) return response({ items: regions });
      return response({
        ...report,
        clustering: {
          ...report.clustering,
          publishable: false,
          chosen_k: null,
          validation_message: "withheld: weak silhouette or stability",
          assignments: [],
          clusters: [],
        },
      });
    });

    render(<RegionalAnalytics />);
    fireEvent.click(await screen.findByRole("button", { name: "Jalankan analisis" }));
    fireEvent.click(await screen.findByRole("tab", { name: /Cluster/ }));
    expect(await screen.findByText(/Keanggotaan cluster tidak ditampilkan/)).toBeInTheDocument();
    expect(screen.queryByText("Cluster 0")).not.toBeInTheDocument();
  });
});
