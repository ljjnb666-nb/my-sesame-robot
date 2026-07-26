import { expect, resetSimulator, test } from "./fixtures";

test.beforeEach(async ({ request }) => {
  await resetSimulator(request);
});

test("09 injects and clears battery_low", async ({ page }, testInfo) => {
  await page.goto("/");
  await page.getByLabel(/fault injection/i).fill("battery_low");
  await page.getByRole("button", { name: /inject/i }).click();
  await expect(page.locator(".fault-list span", { hasText: "battery_low" })).toBeVisible();
  if (testInfo.project.name === "chromium") await page.screenshot({ path: "test-results/fault-state.png", fullPage: true });
  await page.getByRole("button", { name: /clear battery_low/i }).click();
  await expect(page.getByText("No simulator faults")).toBeVisible();
});

test("10 clear all faults clears active fault", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/fault injection/i).fill("battery_low");
  await page.getByRole("button", { name: /inject/i }).click();
  await expect(page.locator(".fault-list span", { hasText: "battery_low" })).toBeVisible();
  await page.getByRole("button", { name: /clear all faults/i }).click();
  await expect(page.getByText("No simulator faults")).toBeVisible();
});

test("13 timeline shows fault event", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/fault injection/i).fill("battery_low");
  await page.getByRole("button", { name: /inject/i }).click();
  await expect(page.locator(".timeline-event", { hasText: "battery_low" })).toBeVisible();
});
