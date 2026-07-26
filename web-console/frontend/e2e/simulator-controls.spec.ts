import { expect, test } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:4173/api/simulator/reset", { data: {} });
});

test("injects and clears battery_low", async ({ page }, testInfo) => {
  await page.goto("/");
  await page.getByLabel(/fault injection/i).fill("battery_low");
  await page.getByRole("button", { name: /inject/i }).click();
  await expect(page.locator(".fault-list span", { hasText: "battery_low" })).toBeVisible();
  if (testInfo.project.name === "chromium") {
    await page.screenshot({ path: "test-results/fault-state.png", fullPage: true });
  }
  await page.getByRole("button", { name: /clear battery_low/i }).click();
  await expect(page.getByText("No simulator faults")).toBeVisible();
});

test("mobile has no horizontal overflow", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
  if (testInfo.project.name === "mobile") {
    await page.screenshot({ path: "test-results/mobile-dashboard.png", fullPage: true });
  }
});
