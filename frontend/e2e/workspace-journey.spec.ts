import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const pageErrors = new WeakMap<Page, string[]>();
test.beforeEach(({ page }) => {
  const errors: string[] = [];
  pageErrors.set(page, errors);
  page.on("pageerror", (error) => errors.push(error.message));
});
test.afterEach(({ page }) => { expect(pageErrors.get(page)).toEqual([]); });

// Deterministic test data only. Production never falls back to these values.
const regions = [{ code: "1100", name: "ACEH" }, { code: "1200", name: "SUMATERA UTARA" }, { code: "1300", name: "SUMATERA BARAT" }];
const indicators = [
  { code: "tpt", name: "Tingkat Pengangguran Terbuka", unit: "Persen", favorable_direction: "lower" },
  { code: "poverty_rate", name: "Persentase Penduduk Miskin", unit: "Persen", favorable_direction: "lower" },
  { code: "hdi", name: "Indeks Pembangunan Manusia", unit: "Poin", favorable_direction: "higher" },
].map((item) => ({ ...item, definition: `Definisi indikator uji ${item.code}.`, source_url: "https://www.bps.go.id/", reference_period_rule: "Tahunan", quality_status: "healthy", dataset_version_id: `fixture-${item.code}`, periods: [{ period: "2024-08-01", coverage_percent: 100 }, { period: "2025-08-01", coverage_percent: 100 }] }));

async function checkPage(page: Page, name: string) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const axe = await new AxeBuilder({ page }).analyze();
  expect(axe.violations.filter((item) => ["serious", "critical"].includes(item.impact ?? ""))).toEqual([]);
  await page.getByRole("heading", { level: 1 }).click();
  await page.screenshot({ path: `../artifacts/ui-review/${name}-${page.viewportSize()?.width}.png`, fullPage: true });
}

for (const theme of ["day", "night"]) {
  test(`scenario controls keep all results synchronized in ${theme} mode`, async ({ page }) => {
    await page.addInitScript((value) => { localStorage.setItem("nusa-intel-theme", value); window.print = () => { document.documentElement.dataset.printRequested = "true"; }; }, theme);
    const calls: string[] = [];
    await page.route("http://localhost:8000/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      const body = route.request().postDataJSON();
      calls.push(path);
      let result: unknown = {};
      if (path.endsWith("/indicators")) result = { items: indicators };
      if (path.endsWith("/regions")) result = { items: regions };
      if (path.endsWith("/compare")) result = {
        year: body.year, normalization: body.normalization, methodology_version: "fixture",
        regions: regions.map((region, index) => ({ region_code: region.code, region_name: region.name, values: indicators.map((item) => ({ indicator_code: item.code, raw_value: index + 10, normalized_value: index / 2, unit: item.unit, reference_period: `${body.year}-08-01`, missing: false })) })),
        trends: [{ indicator_code: "tpt", region_code: "1100", region_name: "ACEH", period: `${body.year}-08-01`, value: 10, unit: "Persen" }],
        distributions: Object.fromEntries(indicators.map((item) => [item.code, { count: 3, minimum: 10, median: 11, maximum: 12 }])), dataset_versions: {}, sources: {},
      };
      if (path.endsWith("/score")) result = { methodology_version: "fixture", dataset_versions: {}, results: regions.map((region, index) => ({ region_code: region.code, region_name: region.name, coverage: 1, eligible: true, score: 80 - index * 10, rank: index + 1, contributions: indicators.map((item) => ({ indicator_code: item.code, raw_value: index + 10, normalized_value: .8, configured_weight: 33.33, effective_weight: 33.33, contribution: 26.67, direction: item.favorable_direction, missing: false })) })) };
      if (path.endsWith("/sensitivity")) result = { scenario_count: 6, perturbation: body.perturbation, disclaimer: "Test fixture", stability: regions.map((region, index) => ({ region_code: region.code, region_name: region.name, base_rank: index + 1, min_rank: index + 1, max_rank: index + 2, max_absolute_shift: 1, unchanged_percent: 80 })) };
      if (path.endsWith("/export")) result = { configuration: body, dataset_versions: {} };
      await route.fulfill({ status: 200, json: result });
    });
    await page.goto("/opportunity");
    await page.getByRole("checkbox", { name: "SUMATERA BARAT" }).uncheck();
    await page.getByRole("checkbox", { name: "SUMATERA BARAT" }).check();
    await page.getByRole("button", { name: "Lanjut", exact: true }).click();
    await page.getByRole("checkbox", { name: /Indeks Pembangunan Manusia/ }).uncheck();
    await page.getByRole("checkbox", { name: /Indeks Pembangunan Manusia/ }).check();
    await page.getByRole("button", { name: "Lanjut", exact: true }).click();
    await page.getByRole("combobox", { name: "Cara menyetarakan nilai" }).selectOption("percentile");
    await page.getByRole("combobox", { name: "Cara menyetarakan nilai" }).selectOption("min_max");
    await page.getByRole("button", { name: "Lanjut", exact: true }).click();
    await page.getByRole("button", { name: "Pertumbuhan", exact: true }).click();
    await expect(page.getByText("Indikator untuk preset ini belum tersedia.")).toBeVisible();
    await page.getByRole("button", { name: "Tenaga kerja", exact: true }).click();
    await page.getByRole("button", { name: "Pemerataan", exact: true }).click();
    await page.getByRole("spinbutton", { name: "Bobot (%)" }).first().fill("39");
    await expect(page.getByRole("button", { name: "Hitung skenario" })).toBeDisabled();
    await page.getByRole("spinbutton", { name: "Bobot (%)" }).first().fill("40");
    await page.getByRole("button", { name: "Hitung skenario" }).click();
    await expect(page.getByRole("heading", { name: "Peringkat berdasarkan bobot Anda" })).toBeVisible();
    await page.getByRole("button", { name: "Tutup notifikasi" }).click();
    await checkPage(page, `opportunity-${theme}`);
    for (const tab of ["Perbandingan", "Tren", "Ketahanan hasil", "Tentang hasil", "Peringkat"]) {
      await page.getByRole("tab", { name: new RegExp(`^${tab}`) }).click();
      await expect(page.getByRole("tabpanel")).toBeVisible();
    }
    await page.getByRole("tab", { name: /^Peringkat/ }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: /^Perbandingan/ })).toHaveAttribute("aria-selected", "true");
    await page.getByRole("slider", { name: /Atur cepat bobot Indeks/ }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByText("Seluruh hasil telah menyesuaikan pilihan terbaru")).toBeVisible();
    expect(calls.filter((path) => path.endsWith("/compare"))).toHaveLength(2);
    expect(calls.filter((path) => path.endsWith("/sensitivity"))).toHaveLength(2);
    await page.getByRole("button", { name: /3Periode|3 Periode/ }).click();
    await page.getByLabel("Tahun perbandingan").selectOption("2024");
    await expect(page.getByText("Konfigurasi berubah", { exact: true })).toBeHidden();
    await page.getByRole("tab", { name: /^Tren/ }).click();
    await expect(page.getByRole("cell", { name: "2024-08-01" })).toBeVisible();
    await page.getByRole("button", { name: "Salin skenario" }).click();
    await expect(page).toHaveURL(/scenario=/);
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Unduh hasil" }).click();
    expect((await download).suggestedFilename()).toBe("nusa-intel-scenario-2024.json");
    await page.getByRole("button", { name: "Cetak laporan" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-print-requested", "true");
    await page.emulateMedia({ media: "print" });
    await expect(page.locator(".ranking-panel")).toBeVisible();
    await expect(page.locator(".sensitivity-panel")).toBeVisible();
  });

  test(`quality catalog retries detail and resolves an incident in ${theme} mode`, async ({ page }) => {
    await page.addInitScript((value) => localStorage.setItem("nusa-intel-theme", value), theme);
    let detailRequests = 0;
    let resolved = false;
    const dataset = { id: "dataset-1", code: "tpt", name: "Tingkat Pengangguran Terbuka", layer: "silver", owner: "BPS", health: "warning", freshness: { status: "fresh", source_reference_at: "2025-08-01T00:00:00Z", retrieved_at: "2026-08-11T01:00:00Z", processed_at: "2026-08-11T01:00:03Z" }, latest_version_status: "published", last_known_good_version_id: "fixture", open_incident_count: 1, failed_check_count: 1 };
    await page.route("http://localhost:8000/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (route.request().method() === "PATCH") { resolved = true; return route.fulfill({ json: {} }); }
      if (path.endsWith("/datasets/dataset-1")) {
        detailRequests++;
        if (detailRequests === 1) return route.fulfill({ status: 503, json: {} });
        return route.fulfill({ json: { ...dataset, contract: null, schema_drift: [] } });
      }
      if (path.endsWith("/quality")) return route.fulfill({ json: { items: [{ id: "check-1", check_code: "missing_values", severity: "warning", status: "failed", created_at: "2026-08-11T00:00:00Z" }] } });
      if (path.endsWith("/incidents")) return route.fulfill({ json: { items: [{ id: "incident-1", dataset_code: "tpt", check_code: "missing_values", status: resolved ? "resolved" : "open", title: "Data kosong", resolution_note: resolved ? "Sumber diperiksa kembali." : null }] } });
      return route.fulfill({ json: { items: [dataset] } });
    });
    await page.goto("/control-tower");
    await page.getByRole("button", { name: "Muat ulang rincian" }).click();
    await expect(page.getByText("Status saat ini: Perlu perhatian")).toBeVisible();
    await page.locator(".dataset-row").click();
    await expect(page.getByText("Status saat ini: Perlu perhatian")).toBeVisible();
    expect(detailRequests).toBe(2);
    await page.getByLabel("Cari data").fill("tidak cocok");
    await expect(page.getByText("Tidak ada data yang cocok")).toBeVisible();
    await page.getByLabel("Cari data").fill("");
    await page.getByLabel("Filter kesehatan").selectOption("healthy");
    await expect(page.getByText("Tidak ada data yang cocok")).toBeVisible();
    await page.getByLabel("Filter kesehatan").selectOption("all");
    await page.getByRole("tab", { name: /Pemeriksaan/ }).click();
    await checkPage(page, `quality-${theme}`);
    await page.getByRole("combobox", { name: "Status", exact: true }).selectOption("passed");
    await expect(page.getByText("Tidak ada hasil pemeriksaan pada filter ini.")).toBeVisible();
    await page.getByRole("combobox", { name: "Status", exact: true }).selectOption("all");
    await page.getByRole("combobox", { name: "Tingkat perhatian", exact: true }).selectOption("critical");
    await expect(page.getByText("Tidak ada hasil pemeriksaan pada filter ini.")).toBeVisible();
    await page.getByRole("tab", { name: /Kendala/ }).click();
    await expect(page.getByRole("button", { name: "Tandai selesai" })).toBeDisabled();
    await page.getByLabel("Catatan resolusi").fill("Sumber diperiksa kembali.");
    await page.getByRole("button", { name: "Tandai selesai" }).click();
    await expect(page.getByText("Sumber diperiksa kembali.")).toBeVisible();
    expect(resolved).toBe(true);
  });
}

test("blocked local storage still allows theme changes and an honest offline retry", async ({ page }) => {
  await page.addInitScript(() => { Object.defineProperty(window, "localStorage", { get() { throw new Error("Storage blocked"); } }); });
  let checks = 0;
  await page.route("**/api/v1/health", async (route) => { checks++; await route.fulfill({ status: 503, json: { status: "healthy" } }); });
  await page.goto("/");
  await expect(page.getByText("Layanan sedang tidak tersedia")).toBeVisible();
  await page.getByRole("button", { name: "Periksa ulang" }).click();
  await expect.poll(() => checks).toBe(2);
  await page.getByRole("button", { name: "Tutup panduan" }).click();
  await expect(page.getByRole("heading", { name: "Sebelum membandingkan data" })).toBeHidden();
  if ((page.viewportSize()?.width ?? 0) < 800) await page.getByRole("button", { name: "Menu", exact: true }).click();
  await page.getByRole("button", { name: "Tema gelap" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "night");
});
