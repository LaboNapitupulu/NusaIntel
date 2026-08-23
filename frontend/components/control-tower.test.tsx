import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ControlTower } from "./control-tower";

function response(payload: unknown): Response {
  return { ok: true, json: async () => payload } as Response;
}

const dataset = {
  id: "dataset-1",
  code: "tpt_silver",
  name: "Tingkat Pengangguran Terbuka normalized",
  layer: "silver",
  owner: "Data Engineering",
  health: "critical",
  freshness: {
    status: "fresh",
    source_reference_at: "2025-08-01T00:00:00Z",
    retrieved_at: "2026-08-11T01:00:00Z",
    processed_at: "2026-08-11T01:00:03Z",
  },
  latest_version_status: "rejected",
  last_known_good_version_id: "good-version-1234",
  open_incident_count: 1,
  failed_check_count: 1,
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ControlTower", () => {
  it("explains data quality in plain language", async () => {
    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/datasets/dataset-1/quality")) {
        return response({
          items: [
            {
              id: "check-1",
              check_code: "numeric_values_valid",
              severity: "critical",
              status: "failed",
              contract_version: 2,
              observed: { invalid_count: 1 },
              created_at: "2026-08-11T01:00:03Z",
            },
          ],
        });
      }
      if (url.endsWith("/datasets/dataset-1")) {
        return response({
          ...dataset,
          contract: { version: 2, checksum: "checksum" },
          schema_drift: [],
        });
      }
      if (url.includes("/incidents")) {
        return response({
          items: [
            {
              id: "incident-1",
              dataset_code: "tpt_silver",
              check_code: "numeric_values_valid",
              status: "open",
              title: "Critical quality failure: numeric_values_valid",
              resolution_note: null,
              created_at: "2026-08-11T01:00:03Z",
            },
          ],
        });
      }
      return response({ items: [dataset] });
    });

    render(<ControlTower />);

    expect(screen.getByRole("status")).toHaveTextContent("Memuat katalog data");
    expect(await screen.findByText("Tingkat Pengangguran Terbuka")).toBeInTheDocument();
    expect(await screen.findByText("Numeric values valid")).toBeInTheDocument();
    expect(screen.getByText("Status saat ini: Kritis")).toBeInTheDocument();
    expect(screen.getByText("Periode data")).toBeInTheDocument();
    expect(screen.getByText("Keterbaruan")).toBeInTheDocument();
    expect(screen.queryByText(/Last-known-good/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /Pemeriksaan/ }));

    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "passed" } });
    expect(screen.getByText("Tidak ada hasil pemeriksaan pada filter ini.")).toBeInTheDocument();
  });

  it("offers retry when the API is unavailable", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("offline"));

    render(<ControlTower />);

    expect(await screen.findByRole("alert")).toHaveTextContent("belum dapat dijangkau");
    fireEvent.click(screen.getByRole("button", { name: "Coba lagi" }));

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(4));
  });
});
