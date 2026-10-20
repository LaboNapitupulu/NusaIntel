import { expect, test, type Page, type Route } from "@playwright/test";

async function fulfillJson(route: Route, body: unknown) {
  await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

async function mockShellApi(page: Page) {
  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/v1/health") {
      return fulfillJson(route, {
        status: "healthy",
        dependencies: { database: { status: "ready" } },
      });
    }
    return fulfillJson(route, { items: [], count: 0 });
  });
}

test.beforeEach(async ({ page }) => {
  await mockShellApi(page);
});

test("legacy hashes remain on the landing page until a workspace is chosen", async ({ page }) => {
  await page.goto("/#control-tower");

  await expect(page).toHaveURL(/\/#control-tower$/);
  await expect(
    page.getByRole("heading", { name: /Pahami wilayah/ }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Kualitas data", exact: true })).toHaveCount(0);
});

test("workspace directory, theme and mobile menu work without overflow", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /Pahami wilayah/ }),
  ).toBeVisible();
  await expect(page.locator(".module-card")).toHaveCount(4);

  const viewport = page.viewportSize();
  if (viewport && viewport.width <= 860) {
    await page.getByRole("button", { name: "Menu", exact: true }).click();
  }

  const themeToggle = page.getByRole("button", { name: "Tema gelap" });
  await expect(themeToggle).toBeVisible();
  await expect(themeToggle).toHaveText(/Terang/);
  await themeToggle.click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "night");
  await expect(themeToggle).toHaveText(/Gelap/);
  await expect(themeToggle).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".brand-cube,.data-cube")).toHaveCount(0);
  if (viewport && viewport.width <= 800) {
    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Menu", exact: true })).toBeFocused();
    await page.getByRole("button", { name: "Menu", exact: true }).click();
  }

  await page.getByRole("link", { name: "Kualitas data", exact: true }).click();
  await expect(page).toHaveURL(/\/control-tower$/);
  await expect(page.getByRole("heading", { name: "Kualitas data", exact: true })).toBeVisible();

  const dimensions = await page.evaluate(() => ({
    page: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
  }));
  expect(dimensions.page).toBeLessThanOrEqual(dimensions.viewport);
});
