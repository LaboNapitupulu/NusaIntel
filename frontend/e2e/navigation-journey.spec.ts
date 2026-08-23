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
    page.getByRole("heading", { name: "Dari data publik menjadi keputusan yang bisa dibuktikan." }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Keadaan data, tanpa area abu-abu." })).toHaveCount(0);
});

test("launchpad exposes 3D workspace navigation without overflow", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Dari data publik menjadi keputusan yang bisa dibuktikan." }),
  ).toBeVisible();
  await expect(page.locator(".module-card")).toHaveCount(4);

  const cubeTransform = await page.locator(".data-cube").evaluate(
    (element) => window.getComputedStyle(element).transform,
  );
  expect(cubeTransform).not.toBe("none");

  const viewport = page.viewportSize();
  if (viewport && viewport.width <= 860) {
    await page.getByRole("button", { name: "Buka navigasi" }).click();
  }

  await page.getByRole("link", { name: "Control Tower", exact: true }).click();
  await expect(page).toHaveURL(/\/control-tower$/);
  await expect(page.getByRole("heading", { name: "Keadaan data, tanpa area abu-abu." })).toBeVisible();

  const dimensions = await page.evaluate(() => ({
    page: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
  }));
  expect(dimensions.page).toBeLessThanOrEqual(dimensions.viewport);
});
