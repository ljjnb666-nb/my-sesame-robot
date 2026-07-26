import { expect, hasHorizontalOverflow, resetSimulator, test } from "./fixtures";

test.beforeEach(async ({ request }) => {
  await resetSimulator(request);
});

test("01 startup shows API online", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByText("API ONLINE")).toBeVisible();
  if (testInfo.project.name === "chromium") await page.screenshot({ path: "test-results/desktop-dashboard.png", fullPage: true });
});

test("02 query battery shows robot battery", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/AI/).fill("battery");
  await page.getByRole("button", { name: /send/i }).click();
  await expect(page.locator(".battery-box strong")).toHaveText("80%");
});

test("03 wave updates chat or timeline", async ({ page }) => {
  await page.goto("/");
  const chatResponse = page.waitForResponse((response) => response.url().endsWith("/api/chat") && response.request().method() === "POST");
  await page.getByLabel(/AI/).fill("wave");
  await page.getByRole("button", { name: /send/i }).click();
  const body = await chatResponse.then((response) => response.json() as Promise<{ status?: string; action?: string | null; message?: string }>);
  expect(body.status).toBe("ok");
  expect(body.action).toBe("wave");
});

test("04 walk opens confirmation dialog", async ({ page }, testInfo) => {
  await page.goto("/");
  await page.getByLabel(/AI/).fill("walk forward");
  await page.getByRole("button", { name: /send/i }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("Fingerprint")).toBeVisible();
  if (testInfo.project.name === "chromium") await page.screenshot({ path: "test-results/confirmation-dialog.png", fullPage: true });
});

test("05 confirming walk shows runtime result", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/AI/).fill("walk forward");
  await page.getByRole("button", { name: /send/i }).click();
  await page.getByRole("button", { name: /confirm action/i }).click();
  await expect(page.getByRole("status")).toContainText(/accepted|ok/);
});

test("06 Enter does not execute confirmation", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/AI/).fill("walk forward");
  await page.getByRole("button", { name: /send/i }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("07 Escape after confirm submit does not cancel in-flight result", async ({ page }, testInfo) => {
  const backgroundWrites: string[] = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/simulator/reset") || url.includes("/api/session/reset") || url.includes("/api/simulator/faults")) {
      backgroundWrites.push(`${request.method()} ${url}`);
    }
  });
  await page.route("**/api/chat", async (route) => {
    const data = route.request().postDataJSON() as { confirmationId?: string | null };
    if (data.confirmationId) {
      await new Promise((resolve) => setTimeout(resolve, 350));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ok", action: "walk_forward", message: "done", structured: { runtime: { confirmation: { state: "accepted" } } } }),
      });
      return;
    }
    await route.fallback();
  });
  await page.goto("/");
  await page.getByLabel(/AI/).fill("walk forward");
  await page.getByRole("button", { name: /send/i }).click();
  await page.getByRole("button", { name: /confirm action/i }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("button", { name: /confirm action/i })).toBeDisabled();
  await expect(page.getByRole("button", { name: /cancel/i })).toBeDisabled();
  await expect.poll(() => page.evaluate(() => {
    const dialog = document.querySelector('[role="dialog"]');
    return Boolean(dialog?.contains(document.activeElement));
  })).toBe(true);
  if (testInfo.project.name === "chromium") await page.screenshot({ path: "test-results/confirmation-submitting.png", fullPage: true });
  for (let index = 0; index < 4; index += 1) {
    await page.keyboard.press("Tab");
    await expect.poll(() => page.evaluate(() => {
      const dialog = document.querySelector('[role="dialog"]');
      return Boolean(dialog?.contains(document.activeElement));
    })).toBe(true);
  }
  await page.keyboard.press("Shift+Tab");
  await expect.poll(() => page.evaluate(() => {
    const dialog = document.querySelector('[role="dialog"]');
    return Boolean(dialog?.contains(document.activeElement));
  })).toBe(true);
  await page.keyboard.press("Space");
  expect(backgroundWrites).toEqual([]);
  await expect(page.getByText("walk forward").first()).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("status")).toContainText(/accepted|done/);
  expect(backgroundWrites).toEqual([]);
});

test("08 cancel confirmation does not execute action", async ({ page }) => {
  let chatRequestCount = 0;
  let confirmationRequestObserved = false;
  page.on("request", (request) => {
    if (request.url().endsWith("/api/chat")) {
      chatRequestCount += 1;
      const data = request.postDataJSON() as { confirmationId?: string | null };
      confirmationRequestObserved = confirmationRequestObserved || Boolean(data.confirmationId);
    }
  });
  await page.goto("/");
  await page.getByLabel(/AI/).fill("walk forward");
  await page.getByRole("button", { name: /send/i }).click();
  await page.getByRole("button", { name: /cancel/i }).click();
  await expect(page.locator(".status-field", { hasText: "COMMAND" })).toContainText(/none|unknown/);
  expect(chatRequestCount).toBe(1);
  expect(confirmationRequestObserved).toBe(false);
});

test("11 UI reset simulator sends strict empty body and clears faults", async ({ page }) => {
  const resetBodies: string[] = [];
  page.on("dialog", (dialog) => dialog.accept());
  page.on("request", (request) => {
    if (request.url().endsWith("/api/simulator/reset")) {
      resetBodies.push(request.postData() ?? "");
    }
  });
  await page.goto("/");
  await page.getByLabel(/fault injection/i).fill("battery_low");
  await page.getByRole("button", { name: /inject/i }).click();
  await expect(page.locator(".fault-list span", { hasText: "battery_low" })).toBeVisible();
  const resetResponse = page.waitForResponse((response) => response.url().endsWith("/api/simulator/reset") && response.request().method() === "POST");
  await page.getByRole("button", { name: /reset simulator/i }).click();
  const body = await resetResponse.then((response) => response.json() as Promise<{ generation?: number; state?: { faults?: string[] } }>);
  await expect(page.getByText("No simulator faults")).toBeVisible();
  expect(resetBodies).toContain("{}");
  expect(typeof body.generation).toBe("number");
  expect(body.state?.faults ?? []).toEqual([]);
});

test("12 session reset clears chat and keeps simulator fault", async ({ page }) => {
  page.on("dialog", (dialog) => dialog.accept());
  await page.goto("/");
  await page.getByLabel(/fault injection/i).fill("battery_low");
  await page.getByRole("button", { name: /inject/i }).click();
  await expect(page.locator(".fault-list span", { hasText: "battery_low" })).toBeVisible();
  await page.getByLabel(/AI/).fill("battery");
  await page.getByRole("button", { name: /send/i }).click();
  await page.getByRole("button", { name: /reset session/i }).click();
  await expect(page.getByText(/runtimeConfirmationsRevoked=false/)).toBeVisible();
  await expect(page.locator(".fault-list span", { hasText: "battery_low" })).toBeVisible();
});

test("14 API unavailable shows offline and disables controls", async ({ page }, testInfo) => {
  await page.route("**/api/health", (route) => route.abort());
  await page.goto("/");
  await expect(page.getByText("API OFFLINE").first()).toBeVisible();
  await expect(page.getByRole("button", { name: /send/i })).toBeDisabled();
  await expect(page.getByRole("button", { name: /inject/i })).toBeDisabled();
  if (testInfo.project.name === "chromium") await page.screenshot({ path: "test-results/offline-state.png", fullPage: true });
});

test("15 non-simulator health blocks actions", async ({ page }, testInfo) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "ok", version: "x", runtimeMode: "real", simulatorOnly: false, provider: "mock" }) }),
  );
  await page.goto("/");
  await expect(page.getByText("API BLOCKED").first()).toBeVisible();
  await expect(page.getByRole("button", { name: /send/i })).toBeDisabled();
  if (testInfo.project.name === "chromium") await page.screenshot({ path: "test-results/blocked-state.png", fullPage: true });
});

test("16 confirmation id is not persisted to DOM URL storage or console", async ({ page }) => {
  const consoleMessages: string[] = [];
  page.on("console", (message) => consoleMessages.push(message.text()));
  const confirmationIdPromise = page.waitForResponse((response) => response.url().endsWith("/api/chat")).then(async (response) => {
      const body = await response.json().catch(() => null) as { confirmationId?: string } | null;
      return body?.confirmationId ?? "";
  });
  await page.goto("/");
  await page.getByLabel(/AI/).fill("walk forward");
  await page.getByRole("button", { name: /send/i }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  const fullId = await confirmationIdPromise;
  expect(Boolean(fullId)).toBe(true);
  const leakObserved = await page.evaluate((id) => (
    document.body.innerText.includes(id) ||
    document.documentElement.outerHTML.includes(id) ||
    location.href.includes(id) ||
    JSON.stringify(localStorage).includes(id) ||
    JSON.stringify(sessionStorage).includes(id)
  ), fullId);
  const consoleLeakObserved = consoleMessages.some((text) => text.includes(fullId));
  expect(leakObserved).toBe(false);
  expect(consoleLeakObserved).toBe(false);
});

test("17 mobile 390x844 has no horizontal overflow", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  expect(await hasHorizontalOverflow(page)).toBe(false);
  if (testInfo.project.name === "mobile") await page.screenshot({ path: "test-results/mobile-dashboard.png", fullPage: true });
});

test("18 laptop 1280x800 layout has no overflow", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");
  expect(await hasHorizontalOverflow(page)).toBe(false);
  if (testInfo.project.name === "chromium") await page.screenshot({ path: "test-results/laptop-1280-dashboard.png", fullPage: true });
});

test("19 tablet 1024x768 layout is usable", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.goto("/");
  await expect(page.getByText("ROBOT OVERVIEW")).toBeVisible();
  expect(await hasHorizontalOverflow(page)).toBe(false);
  if (testInfo.project.name === "chromium") await page.screenshot({ path: "test-results/tablet-1024-dashboard.png", fullPage: true });
});

test("20 stale confirmation error is displayed", async ({ page }) => {
  await page.route("**/api/chat", async (route) => {
    const data = route.request().postDataJSON() as { confirmationId?: string | null };
    if (data.confirmationId) {
      await route.fulfill({ status: 400, contentType: "application/json", body: JSON.stringify({ error: { code: "stale_confirmation", message: "stale confirmation" } }) });
      return;
    }
    await route.fallback();
  });
  await page.goto("/");
  await page.getByLabel(/AI/).fill("walk forward");
  await page.getByRole("button", { name: /send/i }).click();
  await page.getByRole("button", { name: /confirm action/i }).click();
  await expect(page.getByText("stale confirmation")).toBeVisible();
});

test("21 backend reset during pending confirmation does not report stale action success", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/AI/).fill("walk forward");
  await page.getByRole("button", { name: /send/i }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await resetSimulator(page.request);
  await page.getByRole("button", { name: /confirm action/i }).click();
  await expect(page.getByText(/stale|未收到最终结果|confirmation/i).first()).toBeVisible();
  await expect(page.locator(".status-field", { hasText: "COMMAND" })).toContainText(/none|unknown/);
  await expect(page.getByRole("status")).not.toContainText(/accepted/);
});
