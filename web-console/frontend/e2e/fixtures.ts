import { test as base, expect } from "@playwright/test";

export const test = base.extend({
  page: async ({ page }, runFixture) => {
    page.on("request", (request) => {
      const url = new URL(request.url());
      const loopback = url.hostname === "127.0.0.1" || url.hostname === "localhost";
      expect(loopback, `non-loopback request blocked: ${url.origin}`).toBe(true);
    });
    await runFixture(page);
  },
});

export { expect };

export async function resetSimulator(request: Parameters<typeof base>[0]["request"]) {
  await request.post("http://127.0.0.1:4173/api/simulator/reset", { data: {} });
}

export async function hasHorizontalOverflow(page: { evaluate: <T>(fn: () => T) => Promise<T> }) {
  return page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
}
