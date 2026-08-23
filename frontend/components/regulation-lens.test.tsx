import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RegulationLens } from "./regulation-lens";

function response(payload: unknown): Response {
  return { ok: true, json: async () => payload } as Response;
}

const version = {
  id: "00000000-0000-0000-0000-000000000001",
  manifest_version: "2026-08-16.1",
  retrieved_at: "2026-08-16T00:00:00Z",
  parser_status: "parsed",
  section_count: 76,
  published: true,
};

const document = {
  document_id: "uu-27-2022",
  document_type: "UU",
  number: "27",
  year: 2022,
  title: "Pelindungan Data Pribadi",
  status: "in_force",
  status_checked_at: "2026-08-16",
  source_page_url: "https://peraturan.bpk.go.id/uu-27-2022",
  latest_version: version,
};

const groundedAnswer = {
  answerable: true,
  answer: "- Subjek Data Pribadi berhak memperoleh akses dan salinan. [C1]",
  confidence: "high",
  evidence_coverage: 1,
  refusal_reason: null,
  citations: [{
    citation_id: "C1",
    section_ids: ["section-access"],
    document_id: "uu-27-2022",
    document_version_id: version.id,
    document_title: "Pelindungan Data Pribadi",
    document_status: "in_force",
    heading: "Pasal 7",
    quote: "Subjek Data Pribadi berhak memperoleh akses dan salinan.",
    source_url: "https://peraturan.bpk.go.id/uu-27-2022",
    source_anchor: "page:4:line:10",
    status_checked_at: "2026-08-16",
  }],
  disclaimer: "Bukan nasihat hukum.",
  pipeline_version: "evidence-extractive-id-v1",
  provenance: {
    corpus_version: "2026-08-16.1",
    index_version: "index-v1",
    retrieved_evidence_count: 1,
  },
};

afterEach(() => vi.restoreAllMocks());

describe("RegulationLens", () => {
  it("renders grounded citations and opens surrounding context", async () => {
    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/regulations")) return response({ items: [document] });
      if (url.endsWith("/versions")) return response({ items: [version] });
      if (url.endsWith("/answer")) return response(groundedAnswer);
      return response({
        selected_section_id: "section-access",
        document_title: "Pelindungan Data Pribadi",
        document_status: "in_force",
        status_checked_at: "2026-08-16",
        source_url: document.source_page_url,
        sections: [{
          section_id: "section-access",
          heading: "Pasal 7",
          text: "Subjek Data Pribadi berhak memperoleh akses dan salinan.",
          source_anchor: "page:4:line:10",
        }],
      });
    });

    render(<RegulationLens />);
    expect(await screen.findByText(/UU 27\/2022/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Jawab dengan bukti" }));

    expect(await screen.findByText("ANSWERABLE")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /Evidence/ }));
    expect(screen.getByText(/\[C1\] Pasal 7/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dokumen resmi" })).toHaveAttribute(
      "href",
      document.source_page_url,
    );

    fireEvent.click(screen.getByRole("button", { name: "Buka konteks" }));
    expect(await screen.findByRole("heading", { name: "Pelindungan Data Pribadi" })).toBeInTheDocument();
    expect(screen.getByText("page:4:line:10")).toBeInTheDocument();
  });

  it("shows a refusal without fabricated citations", async () => {
    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/regulations")) return response({ items: [document] });
      if (url.endsWith("/versions")) return response({ items: [version] });
      return response({
        ...groundedAnswer,
        answerable: false,
        answer: "Saya belum dapat menjawab berdasarkan corpus yang tersedia.",
        confidence: "low",
        evidence_coverage: 0,
        refusal_reason: "Pertanyaan berada di luar corpus.",
        citations: [],
      });
    });

    render(<RegulationLens />);
    await screen.findByText(/UU 27\/2022/);
    fireEvent.click(screen.getByRole("button", { name: "Jawab dengan bukti" }));

    expect(await screen.findByText("REFUSED")).toBeInTheDocument();
    expect(screen.getByText("Pertanyaan berada di luar corpus.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Dokumen resmi" })).not.toBeInTheDocument();
  });
});
