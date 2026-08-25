import { expect, test, type Page, type Route } from "@playwright/test";

type Theme = "day" | "night";

async function fulfillJson(route: Route, body: unknown) {
  await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

async function mockEmptyProductApi(page: Page) {
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

async function openWithTheme(page: Page, path: string, theme: Theme) {
  await page.addInitScript((selectedTheme) => {
    window.localStorage.setItem("nusa-intel-theme", selectedTheme);
  }, theme);
  await page.goto(path);
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
  await expect(page.locator("html")).toHaveAttribute("data-route-motion", "settled");
  await expect(page.locator("main, section").first()).toBeVisible();
  await page.waitForTimeout(80);
}

const screenshotOptions = {
  animations: "disabled" as const,
  caret: "hide" as const,
  maxDiffPixelRatio: 0.025,
  scale: "css" as const,
};

test.beforeEach(async ({ page }) => {
  await mockEmptyProductApi(page);
});

for (const theme of ["day", "night"] as const) {
  test(`landing page ${theme} theme remains visually stable`, async ({ page }) => {
    await openWithTheme(page, "/", theme);
    await expect(page).toHaveScreenshot(`landing-${theme}.png`, {
      ...screenshotOptions,
      fullPage: true,
    });
  });
}

const productRoutes = [
  ["control-tower", "/control-tower"],
  ["opportunity", "/opportunity"],
  ["regional-analytics", "/regional-analytics"],
  ["regulations", "/regulations"],
] as const;

for (const [name, path] of productRoutes) {
  test(`${name} shell remains readable in both themes`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "Desktop shell baseline only.");
    for (const theme of ["day", "night"] as const) {
      await openWithTheme(page, path, theme);
      await expect(page).toHaveScreenshot(`${name}-${theme}.png`, {
        ...screenshotOptions,
        fullPage: true,
      });
    }
  });
}
