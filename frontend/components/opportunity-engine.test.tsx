import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OpportunityEngine } from "./opportunity-engine";

function response(payload: unknown): Response {
  return { ok: true, json: async () => payload } as Response;
}

const indicators = [
  {
    code: "tpt",
    name: "Tingkat Pengangguran Terbuka",
    definition: "Persentase angkatan kerja yang menganggur.",
    unit: "Persen",
    favorable_direction: "lower",
    source_url: "https://www.bps.go.id/",
    reference_period_rule: "Agustus",
    quality_status: "healthy",
    dataset_version_id: "version-tpt",
    periods: [{ period: "2025-08-01", coverage_percent: 100 }],
  },
  {
    code: "poverty_rate",
    name: "Persentase Penduduk Miskin",
    definition: "Penduduk di bawah garis kemiskinan.",
    unit: "Persen",
    favorable_direction: "lower",
    source_url: "https://www.bps.go.id/",
    reference_period_rule: "Maret",
    quality_status: "healthy",
    dataset_version_id: "version-poverty",
    periods: [{ period: "2025-08-01", coverage_percent: 100 }],
  },
  {
    code: "hdi",
    name: "Indeks Pembangunan Manusia",
    definition: "Indeks komposit pembangunan manusia.",
    unit: "Poin",
    favorable_direction: "higher",
    source_url: "https://www.bps.go.id/",
    reference_period_rule: "Tahunan",
    quality_status: "healthy",
    dataset_version_id: "version-hdi",
    periods: [{ period: "2025-08-01", coverage_percent: 100 }],
  },
];

const regions = [
  { code: "1100", name: "ACEH" },
  { code: "1200", name: "SUMATERA UTARA" },
  { code: "1300", name: "SUMATERA BARAT" },
];

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.removeItem("nusa-intel-opportunity-scenario");
  window.history.replaceState(null, "", "/");
});

describe("OpportunityEngine", () => {
  it("shows reproducible ranking, comparison, sensitivity, and evidence", async () => {
    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/opportunity/indicators")) return response({ items: indicators });
      if (url.endsWith("/opportunity/regions")) return response({ items: regions });
      if (url.endsWith("/opportunity/compare")) {
        return response({
          year: 2025,
          normalization: "min_max",
          methodology_version: "opportunity-score-v1",
          regions: regions.map((region, index) => ({
            region_code: region.code,
            region_name: region.name,
            values: indicators.map((indicator) => ({
              indicator_code: indicator.code,
              raw_value: 10 + index,
              normalized_value: index / 2,
              unit: indicator.unit,
              reference_period: "2025-08-01",
              missing: false,
            })),
          })),
          trends: [
            {
              indicator_code: "hdi",
              region_code: "1100",
              region_name: "ACEH",
              period: "2025-08-01",
              value: 75,
              unit: "Poin",
            },
          ],
          distributions: Object.fromEntries(
            indicators.map((indicator) => [
              indicator.code,
              { count: 38, minimum: 1, median: 5, maximum: 10 },
            ]),
          ),
          dataset_versions: Object.fromEntries(
            indicators.map((indicator) => [
              indicator.code,
              {
                version_id: `version-${indicator.code}`,
                checksum: "checksum",
                analysis_reference_period: "2025-08-01",
              },
            ]),
          ),
          sources: {},
        });
      }
      if (url.endsWith("/opportunity/score")) {
        return response({
          methodology_version: "opportunity-score-v1",
          dataset_versions: {},
          results: regions.map((region, index) => ({
            region_code: region.code,
            region_name: region.name,
            coverage: index === 2 ? 0.67 : 1,
            eligible: index !== 2,
            score: index === 2 ? null : 80 - index * 10,
            rank: index === 2 ? null : index + 1,
            contributions: indicators.map((indicator) => ({
              indicator_code: indicator.code,
              raw_value: 10,
              normalized_value: 0.8,
              configured_weight: indicator.code === "tpt" ? 33.34 : 33.33,
              effective_weight: indicator.code === "tpt" ? 33.34 : 33.33,
              contribution: 26.67,
              direction: indicator.favorable_direction,
              missing: false,
            })),
          })),
        });
      }
      if (url.endsWith("/opportunity/sensitivity")) {
        return response({
          scenario_count: 6,
          perturbation: 0.1,
          disclaimer: "Sensitivity is not a confidence interval and does not imply causality.",
          stability: regions.map((region, index) => ({
            region_code: region.code,
            region_name: region.name,
            base_rank: index + 1,
            min_rank: index + 1,
            max_rank: index + 1,
            max_absolute_shift: 0,
            unchanged_percent: 100,
          })),
        });
      }
      return response({ dataset_versions: {}, configuration: {} });
    });

    render(<OpportunityEngine />);

    fireEvent.click(await screen.findByRole("button", { name: "Hitung skenario" }));
    expect(await screen.findByText("Kontribusi terlihat, coverage ditegakkan.")).toBeInTheDocument();
    expect(screen.getAllByText("ACEH").length).toBeGreaterThan(0);
    expect(screen.getByText("80")).toBeInTheDocument();
    expect(screen.getByText("Tidak diranking")).toBeInTheDocument();
    expect(screen.getByText("6 skenario")).toBeInTheDocument();
    expect(screen.getByText(/not a confidence interval/)).toBeInTheDocument();
    expect(screen.getByText(/reference 2025-08-01 · version version-hdi/)).toBeInTheDocument();
    expect(screen.getByText("Alternatif data tabel untuk distribusi")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /4Bobot/ }));
    fireEvent.change(screen.getByRole("slider", { name: /Atur cepat bobot Tingkat Pengangguran Terbuka/ }), {
      target: { value: "50" },
    });
    expect(screen.getByText(/Total bobot: 100%/)).toBeInTheDocument();
    await waitFor(
      () => expect(screen.getByText(/Ranking live diperbarui/)).toBeInTheDocument(),
      { timeout: 2000 },
    );
    expect(vi.mocked(global.fetch).mock.calls.filter(([input]) => String(input).endsWith("/opportunity/score"))).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "Salin skenario" }));
    await waitFor(() => expect(window.location.search).toContain("scenario="));
  });

  it("refuses to calculate when weights do not sum to 100 percent", async () => {
    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/opportunity/indicators")) return response({ items: indicators });
      if (url.endsWith("/opportunity/regions")) return response({ items: regions });
      return new Promise<Response>(() => undefined);
    });

    render(<OpportunityEngine />);
    const weightInputs = await screen.findAllByLabelText("Bobot (%)");
    fireEvent.change(weightInputs[0], { target: { value: "10" } });

    expect(screen.getByText(/Total bobot: 76,66%/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hitung skenario" })).toBeDisabled();
    expect(screen.getByText(/total bobot 100%/)).toBeInTheDocument();
  });
});
