import { expect, resetSimulator, test } from "./fixtures";

test.beforeEach(async ({ request }) => {
  await resetSimulator(request);
});

test("09 injects and clears battery_low with zh-CN labels", async ({ page }, testInfo) => {
  await page.goto("/");
  await page.getByLabel("模拟故障注入").fill("battery_low");
  await page.getByRole("button", { name: "注入故障" }).click();
  await expect(page.locator(".fault-list span", { hasText: "电量过低" })).toBeVisible();
  await expect(page.locator(".fault-list span", { hasText: "battery_low" })).toBeVisible();
  if (testInfo.project.name === "chromium") await page.screenshot({ path: "test-results/zh-cn-fault-state.png", fullPage: true });
  await page.getByRole("button", { name: /清除 电量过低/ }).click();
  await expect(page.getByText("当前没有模拟故障")).toBeVisible();
});

test("10 clear all faults clears active fault", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("模拟故障注入").fill("battery_low");
  await page.getByRole("button", { name: "注入故障" }).click();
  await expect(page.locator(".fault-list span", { hasText: "battery_low" })).toBeVisible();
  await page.getByRole("button", { name: "清除全部故障" }).click();
  await expect(page.getByText("当前没有模拟故障")).toBeVisible();
});

test("13 timeline shows localized fault event", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("模拟故障注入").fill("battery_low");
  await page.getByRole("button", { name: "注入故障" }).click();
  const event = page.locator(".timeline-event", { hasText: "battery_low" });
  await expect(event).toBeVisible();
  await expect(event).toContainText("电量过低");
  await expect(event).toContainText("结果");
  await expect(event).toContainText("运行模式");
});
