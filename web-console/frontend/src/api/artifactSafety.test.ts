import fs from "node:fs";
import { describe, expect, it } from "vitest";

describe("Playwright artifact safety", () => {
  it("keeps trace, video, and automatic screenshots disabled", () => {
    const config = fs.readFileSync("playwright.config.ts", "utf8");
    expect(config).toMatch(/trace:\s*["']off["']/);
    expect(config).toMatch(/video:\s*["']off["']/);
    expect(config).toMatch(/screenshot:\s*["']off["']/);
  });

  it("checks E2E artifacts for trace, HAR, video, and network dumps", () => {
    const script = fs.readFileSync("scripts/run-e2e.mjs", "utf8");
    expect(script).toContain("trace\\.zip");
    expect(script).toContain("\\.har");
    expect(script).toContain("\\.webm");
    expect(script).toContain("\\.mp4");
    expect(script).toContain("network");
    expect(script).toContain("request-body");
  });

  it("runs E2E through the cleanup runner instead of shell chaining", () => {
    const packageJson = JSON.parse(fs.readFileSync("package.json", "utf8")) as { scripts: Record<string, string> };
    expect(packageJson.scripts["test:e2e"]).toBe("node scripts/run-e2e.mjs");
  });
});
