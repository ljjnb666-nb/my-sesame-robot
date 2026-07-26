import { expect, test } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:4173/api/simulator/reset", { data: {} });
});

test("dashboard starts online and can query battery", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByText("API ONLINE")).toBeVisible();
  await page.getByLabel("AI 指令").fill("battery");
  await page.getByRole("button", { name: /send/i }).click();
  await expect(page.locator(".battery-box strong")).toHaveText("80%");
  if (testInfo.project.name === "chromium") {
    await page.screenshot({ path: "test-results/desktop-dashboard.png", fullPage: true });
  }
});

test("walk shows confirmation and hides confirmation id", async ({ page }, testInfo) => {
  await page.goto("/");
  await page.getByLabel("AI 指令").fill("walk forward");
  await page.getByRole("button", { name: /send/i }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("Fingerprint")).toBeVisible();
  const body = await page.textContent("body");
  expect(body).not.toMatch(/[a-f0-9]{32,}/i);
  if (testInfo.project.name === "chromium") {
    await page.screenshot({ path: "test-results/confirmation-dialog.png", fullPage: true });
  }
});
