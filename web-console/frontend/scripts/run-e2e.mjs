import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const REPORT_DIR = "playwright-report";
const RESULTS_DIR = "test-results";
const RAW_REPORT = path.join(REPORT_DIR, ".raw-results.json");
const LEGACY_REPORT = path.join(REPORT_DIR, "results.json");
const SUMMARY_JSON = path.join(REPORT_DIR, "e2e-summary.json");
const SUMMARY_MD = path.join(REPORT_DIR, "e2e-summary.md");
const FAILURE_MD = path.join(REPORT_DIR, "e2e-failure-summary.md");

const MIN_UNIQUE_SCENARIOS = 20;
const MIN_EXECUTIONS = 40;
const MIN_SCREENSHOTS = 9;

const FORBIDDEN_ARTIFACT_PATTERNS = [
  /(^|\/)\.?raw-results\.json$/i,
  /(^|\/)results\.json$/i,
  /(^|\/)trace\.zip$/i,
  /\.har$/i,
  /\.webm$/i,
  /\.mp4$/i,
  /(^|\/)network/i,
  /(^|\/)request-body/i,
  /(^|\/)blob-report(\/|$)/i,
  /(^|\/)data(\/|$)/i,
  /(^|\/)index\.html$/i,
];

const SECRET_PATTERNS = [
  /confirmationId["']?\s*[:=]\s*["']?[^"',\s}]+/gi,
  /confirmation[_-]?id["']?\s*[:=]\s*["']?[^"',\s}]+/gi,
  /[A-Za-z0-9_-]*secret[A-Za-z0-9_-]*/gi,
  /sk-[A-Za-z0-9_-]+/gi,
  /Bearer\s+[A-Za-z0-9._-]+/gi,
  /https?:\/\/[^\s)]+/gi,
  /[A-Za-z]:\\[^\s"'<>]+/g,
];

function normalizePath(filePath) {
  return filePath.replaceAll("\\", "/");
}

function ensureReportDirs() {
  fs.mkdirSync(REPORT_DIR, { recursive: true });
  fs.mkdirSync(RESULTS_DIR, { recursive: true });
}

function listFiles(root) {
  if (!fs.existsSync(root)) return [];
  const output = [];
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) output.push(...listFiles(fullPath));
    else output.push(fullPath);
  }
  return output;
}

function removePathIfExists(targetPath) {
  if (!fs.existsSync(targetPath)) return;
  const stats = fs.lstatSync(targetPath);
  if (stats.isDirectory()) {
    fs.rmSync(targetPath, { recursive: true, force: true });
  } else {
    fs.unlinkSync(targetPath);
  }
}

function isForbiddenArtifact(filePath) {
  const normalized = normalizePath(filePath);
  return FORBIDDEN_ARTIFACT_PATTERNS.some((pattern) => pattern.test(normalized));
}

function isAllowedArtifact(filePath) {
  const normalized = normalizePath(filePath);
  return (
    /^test-results\/[^/]+\.png$/i.test(normalized) ||
    normalized === "playwright-report/e2e-summary.json" ||
    normalized === "playwright-report/e2e-summary.md" ||
    normalized === "playwright-report/e2e-failure-summary.md"
  );
}

function sanitizeText(value) {
  let output = String(value ?? "");
  for (const pattern of SECRET_PATTERNS) {
    output = output.replace(pattern, "[redacted]");
  }
  return output.replace(/[^\w .:/-]/g, "").slice(0, 120);
}

function classifyError(error) {
  const text = sanitizeText(error?.message ?? error?.error?.message ?? error?.value ?? error);
  if (/timeout|timedout/i.test(text)) return "timeout";
  if (/expect|assert/i.test(text)) return "assertion_failed";
  if (/parse|json/i.test(text)) return "invalid_report";
  if (/interrupted/i.test(text)) return "interrupted";
  return "test_failed";
}

function emptySummary() {
  return {
    uniqueScenarios: 0,
    executions: 0,
    projectExecutions: {},
    skipped: 0,
    failed: 0,
    interrupted: 0,
    unexpected: 0,
    forbiddenArtifacts: 0,
    screenshots: 0,
    screenshotFiles: [],
  };
}

function summarizeReport(report) {
  const summary = emptySummary();
  const projectExecutions = new Map();
  const uniqueScenarios = new Set();
  const failures = [];

  function visitSuite(suite) {
    for (const spec of suite.specs ?? []) {
      uniqueScenarios.add(spec.title);
      for (const test of spec.tests ?? []) {
        summary.executions += 1;
        const projectName = test.projectName ?? test.projectId ?? "unknown";
        projectExecutions.set(projectName, (projectExecutions.get(projectName) ?? 0) + 1);
        if (test.status === "skipped") summary.skipped += 1;
        for (const result of test.results ?? []) {
          if (result.status === "skipped") summary.skipped += 1;
          if (result.status === "failed" || result.status === "timedOut") summary.failed += 1;
          if (result.status === "interrupted") summary.interrupted += 1;
          if (result.status === "unexpected") summary.unexpected += 1;
          if (["failed", "timedOut", "interrupted", "unexpected"].includes(result.status)) {
            failures.push({
              scenario: sanitizeText(spec.title),
              project: sanitizeText(projectName),
              category: classifyError(result.error),
            });
          }
        }
      }
    }
    for (const child of suite.suites ?? []) visitSuite(child);
  }

  for (const suite of report.suites ?? []) visitSuite(suite);
  summary.uniqueScenarios = uniqueScenarios.size;
  summary.projectExecutions = Object.fromEntries([...projectExecutions.entries()].sort());
  return { summary, failures };
}

function refreshArtifactCounts(summary) {
  const screenshots = fs.existsSync(RESULTS_DIR)
    ? fs.readdirSync(RESULTS_DIR).filter((name) => name.endsWith(".png")).sort()
    : [];
  const allArtifacts = [...listFiles(RESULTS_DIR), ...listFiles(REPORT_DIR)];
  summary.forbiddenArtifacts = allArtifacts.filter(isForbiddenArtifact).length;
  summary.screenshots = screenshots.length;
  summary.screenshotFiles = screenshots;
}

function writeSummaries(summary, failures = []) {
  fs.writeFileSync(SUMMARY_JSON, `${JSON.stringify(summary, null, 2)}\n`);
  fs.writeFileSync(
    SUMMARY_MD,
    [
      "## Frontend E2E",
      "",
      `- Unique scenarios: ${summary.uniqueScenarios}`,
      `- Executions: ${summary.executions}`,
      `- Project executions: ${JSON.stringify(summary.projectExecutions)}`,
      `- Skipped: ${summary.skipped}`,
      `- Failed: ${summary.failed}`,
      `- Interrupted: ${summary.interrupted}`,
      `- Unexpected: ${summary.unexpected}`,
      `- Forbidden artifacts: ${summary.forbiddenArtifacts}`,
      `- Screenshots: ${summary.screenshots}`,
      "",
    ].join("\n"),
  );

  if (failures.length > 0) {
    const lines = ["## Frontend E2E Failure Summary", ""];
    for (const failure of failures) {
      lines.push(`- ${failure.scenario || "unknown"} [${failure.project || "unknown"}]: ${failure.category}`);
    }
    lines.push("");
    fs.writeFileSync(FAILURE_MD, lines.join("\n"));
  } else {
    removePathIfExists(FAILURE_MD);
  }
}

function removeForbiddenArtifacts() {
  for (const target of [
    RAW_REPORT,
    LEGACY_REPORT,
    path.join(REPORT_DIR, "index.html"),
    path.join(REPORT_DIR, "data"),
    "blob-report",
  ]) {
    removePathIfExists(target);
  }

  for (const root of [RESULTS_DIR, REPORT_DIR]) {
    for (const file of listFiles(root)) {
      if (!isAllowedArtifact(file)) removePathIfExists(file);
    }
  }
}

function validateSummary(summary) {
  const failures = [];
  if (summary.uniqueScenarios < MIN_UNIQUE_SCENARIOS) failures.push("unique_scenarios_below_threshold");
  if (summary.executions < MIN_EXECUTIONS) failures.push("executions_below_threshold");
  if (summary.skipped > 0) failures.push("skipped_tests_present");
  if (summary.failed > 0) failures.push("failed_tests_present");
  if (summary.interrupted > 0) failures.push("interrupted_tests_present");
  if (summary.unexpected > 0) failures.push("unexpected_tests_present");
  if (summary.forbiddenArtifacts > 0) failures.push("forbidden_artifacts_present");
  if (summary.screenshots < MIN_SCREENSHOTS) failures.push("screenshots_below_threshold");
  return failures;
}

function runPlaywright() {
  const cliPath = path.join("node_modules", "@playwright", "test", "cli.js");
  return spawnSync(process.execPath, [cliPath, "test", "--reporter=json"], {
    encoding: "utf8",
    maxBuffer: 1024 * 1024 * 50,
    stdio: ["ignore", "pipe", "pipe"],
  });
}

export function processE2eReport(rawJson, options = {}) {
  ensureReportDirs();
  if (rawJson !== undefined) fs.writeFileSync(RAW_REPORT, rawJson);

  let summary = emptySummary();
  let failures = [];
  let parseFailed = false;

  try {
    const report = JSON.parse(String(rawJson ?? ""));
    ({ summary, failures } = summarizeReport(report));
  } catch {
    parseFailed = true;
    failures = [{ scenario: "report", project: "runner", category: "invalid_report" }];
  } finally {
    removeForbiddenArtifacts();
  }

  refreshArtifactCounts(summary);
  writeSummaries(summary, failures);
  const validationFailures = validateSummary(summary);
  if (parseFailed) validationFailures.push("invalid_report");
  if (options.playwrightExitCode && options.playwrightExitCode !== 0) validationFailures.push("playwright_failed");
  return { summary, failures, validationFailures };
}

export function runE2e() {
  ensureReportDirs();
  const result = runPlaywright();
  const rawJson = result.stdout ?? "";
  const processed = processE2eReport(rawJson, { playwrightExitCode: result.status ?? 1 });
  console.log(JSON.stringify(processed.summary, null, 2));
  if (processed.validationFailures.length > 0) {
    console.error(`E2E validation failed: ${processed.validationFailures.join(", ")}`);
    return 1;
  }
  return 0;
}

const executedPath = process.argv[1] ? path.resolve(process.argv[1]) : "";
if (executedPath === fileURLToPath(import.meta.url)) {
  process.exitCode = runE2e();
}
