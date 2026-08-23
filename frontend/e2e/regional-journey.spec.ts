import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

const indicators = [
  ["tpt", "Tingkat Pengangguran Terbuka", "Persen", "2024-08-01"],
  ["poverty_rate", "Persentase Penduduk Miskin", "Persen", "2024-03-01"],
  ["hdi", "Indeks Pembangunan Manusia", "Poin", "2024-12-01"],
].map(([code, name, unit, period]) => ({
  code,
  name,
  definition: `${name} menurut publikasi BPS.`,
  unit,
  favorable_direction: code === "hdi" ? "higher" : "lower",
  source_url: "https://www.bps.go.id/",
  reference_period_rule: period,
  quality_status: "healthy",
  dataset_version_id: `version-${code}`,
  periods: [{ period, coverage_percent: 100 }],
}));

const provinceCodes = [
  "1100", "1200", "1300", "1400", "1500", "1600", "1700", "1800", "1900", "2100",
  "3100", "3200", "3300", "3400", "3500", "3600", "5100", "5200", "5300", "6100",
  "6200", "6300", "6400", "6500", "7100", "7200", "7300", "7400", "7500", "7600",
  "8100", "8200", "9100", "9200", "9400", "9500", "9600", "9700",
];
const regions = provinceCodes.map((code, index) => ({
  code,
  name: index === 0 ? "ACEH" : index === 1 ? "SUMATERA UTARA" : `PROVINSI ${index + 1}`,
}));

const source = { name: "Badan Pusat Statistik", url: "https://www.bps.go.id/", attribution: "BPS" };
const version = (code: string) => ({
  version_id: `version-${code}`,
  checksum: `checksum-${code}`,
  analysis_reference_period: indicators.find((item) => item.code === code)?.periods[0].period,
});

const analyticsReport = {
  report_type: "regional-analytics-report",
  generated_at: "2026-08-11T00:00:00Z",
  methodology_version: "regional-analytics-v1",
  target_region: { region_code: "1100", region_name: "ACEH" },
  similarity: {
    feature_set_version: "fixture-feature-set-v1",
    preprocessing_version: "zscore-complete-case-v1",
    selected_features: indicators.map((item) => ({
      indicator_code: item.code,
      indicator_name: item.name,
      coverage: 1,
      unit: item.unit,
    })),
    excluded_features: [],
    excluded_regions: [],
    results: [
      {
        region_code: "1200",
        region_name: "SUMATERA UTARA",
        distance: 0.125,
        drivers: [
          {
            indicator_code: "hdi",
            indicator_name: "Indeks Pembangunan Manusia",
            target_value: 75,
            candidate_value: 74,
            distance_share: 0.6,
            unit: "Poin",
          },
        ],
      },
    ],
  },
  clustering: {
    publishable: true,
    chosen_k: 2,
    validation_message: "Validation thresholds pass.",
    candidate_evidence: [
      { k: 2, silhouette: 0.41, stability: 0.92, minimum_cluster_size: 12 },
      { k: 3, silhouette: 0.32, stability: 0.81, minimum_cluster_size: 8 },
    ],
    assignments: regions.map((region, index) => ({
      region_code: region.code,
      region_name: region.name,
      cluster_id: (index % 2) + 1,
    })),
    clusters: [
      { cluster_id: 1, description: "hdi relatif lebih tinggi dibanding rata-rata feature set.", regions: regions.slice(0, 19) },
      { cluster_id: 2, description: "tpt relatif lebih rendah dibanding rata-rata feature set.", regions: regions.slice(19) },
    ],
  },
  map: {
    indicator_code: "tpt",
    indicator_name: "Tingkat Pengangguran Terbuka",
    unit: "Persen",
    disclaimer: "Tile positions are schematic and are not official administrative boundaries.",
    values: regions.map((region, index) => ({
      region_code: region.code,
      region_name: region.name,
      value: index === 37 ? null : 3 + index / 10,
    })),
  },
  citations: indicators.map((item) => ({
    indicator_code: item.code,
    indicator_name: item.name,
    unit: item.unit,
    source,
    reference_period: item.periods[0].period,
    dataset_version: version(item.code),
  })),
  limitations: [
    "Similarity describes standardized profiles, not causality.",
    "The map is schematic and is not an authoritative boundary map.",
  ],
};

const regionDetail = {
  region_code: "1100",
  region_name: "ACEH",
  year: 2024,
  indicators: indicators.map((item, index) => ({
    indicator_code: item.code,
    indicator_name: item.name,
    definition: item.definition,
    value: 5 + index * 10,
    missing: false,
    unit: item.unit,
    reference_period: item.periods[0].period,
    source,
    dataset_version: version(item.code),
  })),
};

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function mockApi(page: Page) {
  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/v1/health") {
      return fulfillJson(route, { status: "healthy", dependencies: { database: { status: "ready" } } });
    }
    if (url.pathname === "/api/v1/opportunity/indicators") {
      return fulfillJson(route, { items: indicators, count: indicators.length });
    }
    if (url.pathname === "/api/v1/opportunity/regions") {
      return fulfillJson(route, { items: regions, count: regions.length });
    }
    if (url.pathname === "/api/v1/opportunity/analytics/report") {
      return fulfillJson(route, analyticsReport);
    }
    if (url.pathname === "/api/v1/opportunity/regions/1100") {
      return fulfillJson(route, regionDetail);
    }
    if (url.pathname === "/api/v1/datasets" || url.pathname === "/api/v1/pipeline-runs" || url.pathname === "/api/v1/incidents") {
      return fulfillJson(route, { items: [], count: 0 });
    }
    return fulfillJson(route, { detail: "Not part of the deterministic E2E fixture." }, 503);
  });
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("regional report is usable, responsive, and has no serious accessibility violations", async ({ page }) => {
  await page.goto("/regional-analytics");
  await expect(page.getByRole("heading", { name: /Temukan wilayah dengan kondisi/ })).toBeVisible();
  await page.getByRole("button", { name: "Jalankan analisis" }).click();

  await expect(page.getByText("Wilayah dibandingkan")).toBeVisible();
  await expect(page.locator(".province-tile")).toHaveCount(38);
  await expect(page.getByRole("button", { name: "ACEH, 3 Persen" })).toBeVisible();
  await expect(page.locator(".map-disclaimer")).toContainText("bukan batas wilayah administratif resmi");

  await page.getByText("Alternatif tabel aksesibel (38 provinsi)").click();
  await expect(page.getByRole("table", { name: "Nilai yang sama dengan peta tile." })).toBeVisible();
  await expect(page.getByRole("table", { name: "Nilai yang sama dengan peta tile." }).getByRole("row")).toHaveCount(39);

  const viewport = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: window.innerWidth }));
  expect(viewport.body).toBeLessThanOrEqual(viewport.viewport);

  const tileMap = await page.locator(".tile-map").evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
  }));
  expect(tileMap.scrollWidth).toBeLessThanOrEqual(tileMap.clientWidth);

  const accessibility = await new AxeBuilder({ page }).include("#regional-analytics").analyze();
  expect(accessibility.violations.filter((item) => ["serious", "critical"].includes(item.impact ?? ""))).toEqual([]);
});

test("regional report links to a source-aware regional detail page", async ({ page }) => {
  await page.goto("/regional-analytics");
  await page.getByRole("button", { name: "Jalankan analisis" }).click();
  await page.getByRole("tab", { name: /Wilayah serupa/ }).click();
  await page.getByRole("link", { name: "Buka detail ACEH" }).click();

  await expect(page).toHaveURL(/\/regions\/1100\?year=2024$/);
  await expect(page.getByRole("heading", { level: 1, name: "ACEH" })).toBeVisible();
  await expect(page.getByText("Periode referensi").first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Badan Pusat Statistik" }).first()).toHaveAttribute("href", "https://www.bps.go.id/");
});
