import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
// @ts-expect-error Vitest executes the ESM runner directly; no TS declaration is needed at runtime.
import { processE2eReport } from "../../scripts/run-e2e.mjs";

const originalCwd = process.cwd();
let tempDir = "";

function failedReportWithSecret() {
  return JSON.stringify({
    suites: [
      {
        specs: [
          {
            title: "secret failure scenario",
            tests: [
              {
                projectName: "chromium",
                status: "unexpected",
                results: [
                  {
                    status: "failed",
                    error: { message: 'assert failed confirmationId: "full-secret-runtime-id"' },
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  });
}

beforeEach(() => {
  tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "sesame-e2e-runner-"));
  process.chdir(tempDir);
});

afterEach(() => {
  process.chdir(originalCwd);
  fs.rmSync(tempDir, { recursive: true, force: true });
});

describe("E2E cleanup runner", () => {
  it("removes raw failed JSON and keeps confirmation IDs out of safe summaries", () => {
    const processed = processE2eReport(failedReportWithSecret(), { playwrightExitCode: 1 });

    expect(processed.validationFailures.length).toBeGreaterThan(0);
    expect(fs.existsSync("playwright-report/.raw-results.json")).toBe(false);
    expect(fs.existsSync("playwright-report/results.json")).toBe(false);

    const summary = fs.readFileSync("playwright-report/e2e-summary.json", "utf8");
    const failure = fs.readFileSync("playwright-report/e2e-failure-summary.md", "utf8");
    expect(summary).not.toContain("full-secret-runtime-id");
    expect(failure).not.toContain("full-secret-runtime-id");
    expect(failure).toContain("assertion_failed");
  });

  it("removes raw content and emits only a safe failure summary when JSON is invalid", () => {
    const processed = processE2eReport('{ "confirmationId": "full-secret-runtime-id"', { playwrightExitCode: 1 });

    expect(processed.validationFailures).toContain("invalid_report");
    expect(fs.existsSync("playwright-report/.raw-results.json")).toBe(false);
    expect(fs.readFileSync("playwright-report/e2e-failure-summary.md", "utf8")).not.toContain("full-secret-runtime-id");
  });

  it("deletes forbidden artifacts before producing the uploadable summary", () => {
    fs.mkdirSync("playwright-report", { recursive: true });
    fs.writeFileSync("playwright-report/trace.zip", "secret trace");
    fs.writeFileSync("playwright-report/network-dump.txt", "secret network");
    fs.writeFileSync("playwright-report/request-body.txt", "secret body");

    const processed = processE2eReport(failedReportWithSecret(), { playwrightExitCode: 1 });

    expect(processed.summary.forbiddenArtifacts).toBe(0);
    expect(fs.existsSync("playwright-report/trace.zip")).toBe(false);
    expect(fs.existsSync("playwright-report/network-dump.txt")).toBe(false);
    expect(fs.existsSync("playwright-report/request-body.txt")).toBe(false);
  });
});
