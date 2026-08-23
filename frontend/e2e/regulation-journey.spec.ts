import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

const version = {
  id: "00000000-0000-0000-0000-000000000001",
  manifest_version: "2026-08-16.1",
  retrieved_at: "2026-08-16T00:00:00Z",
  parser_status: "parsed",
  section_count: 76,
  published: true,
};

const regulation = {
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

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function mockRegulationApi(page: Page) {
  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/v1/regulations") {
      return fulfillJson(route, { items: [regulation], count: 1 });
    }
    if (url.pathname === "/api/v1/regulations/uu-27-2022/versions") {
      return fulfillJson(route, { items: [version], count: 1 });
    }
    if (url.pathname === "/api/v1/regulations/answer") {
      return fulfillJson(route, {
        answerable: true,
        answer: "- Subjek Data Pribadi berhak memperoleh akses dan salinan. [C1]",
        confidence: "high",
        evidence_coverage: 1,
        refusal_reason: null,
        citations: [{
          citation_id: "C1",
          section_ids: ["section-access"],
          document_id: regulation.document_id,
          document_version_id: version.id,
          document_title: regulation.title,
          document_status: regulation.status,
          heading: "Pasal 7",
          quote: "Subjek Data Pribadi berhak memperoleh akses dan salinan.",
          source_url: regulation.source_page_url,
          source_anchor: "page:4:line:10",
          status_checked_at: regulation.status_checked_at,
        }],
        disclaimer: "Bukan nasihat hukum.",
        pipeline_version: "evidence-extractive-id-v1",
        provenance: {
          corpus_version: version.manifest_version,
          index_version: "index-v1",
          retrieved_evidence_count: 1,
        },
      });
    }
    if (url.pathname === "/api/v1/regulations/uu-27-2022/sections/section-access/context") {
      return fulfillJson(route, {
        selected_section_id: "section-access",
        document_title: regulation.title,
        document_status: regulation.status,
        status_checked_at: regulation.status_checked_at,
        source_url: regulation.source_page_url,
        sections: [{
          section_id: "section-access",
          heading: "Pasal 7",
          text: "Subjek Data Pribadi berhak memperoleh akses dan salinan.",
          source_anchor: "page:4:line:10",
        }],
      });
    }
    return fulfillJson(route, { detail: "Not part of the deterministic RegulasiLens fixture." }, 503);
  });
}

test.beforeEach(async ({ page }) => {
  await mockRegulationApi(page);
});

test("grounded answer remains usable without horizontal overflow", async ({ page }) => {
  await page.goto("/regulations");
  await expect(page.getByRole("heading", { name: /Pahami regulasi langsung/ })).toBeVisible();
  await expect(page.getByText(/UU 27\/2022/)).toBeVisible();

  await page.getByRole("button", { name: "Cari jawaban" }).click();
  await expect(page.getByText("SUMBER TERSEDIA", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: /Sumber/ }).click();
  await expect(page.getByText(/\[C1\] Pasal 7/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Dokumen resmi" })).toHaveAttribute(
    "href",
    regulation.source_page_url,
  );

  const contextButton = page.getByRole("button", { name: "Buka konteks" });
  await contextButton.dispatchEvent("click");
  await expect(page.getByRole("heading", { name: regulation.title })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("page:4:line:10")).toBeVisible();

  const dimensions = await page.evaluate(() => {
    const shell = document.querySelector<HTMLElement>("#regulasilens");
    return {
      viewport: document.documentElement.clientWidth,
      page: document.documentElement.scrollWidth,
      shell: shell?.getBoundingClientRect().width ?? 0,
    };
  });
  expect(dimensions.page).toBeLessThanOrEqual(dimensions.viewport);
  expect(dimensions.shell).toBeGreaterThan(0);

  const accessibility = await new AxeBuilder({ page }).include("#regulasilens").analyze();
  expect(accessibility.violations.filter((item) => ["serious", "critical"].includes(item.impact ?? ""))).toEqual([]);
});
