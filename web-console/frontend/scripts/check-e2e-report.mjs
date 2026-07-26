import fs from "node:fs";
import path from "node:path";

const reportPath = "playwright-report/results.json";
const report = JSON.parse(fs.readFileSync(reportPath, "utf8"));
const playwrightConfig = fs.readFileSync("playwright.config.ts", "utf8");

if (!/trace:\s*["']off["']/.test(playwrightConfig)) {
  console.error("Playwright trace must remain off for confirmation tests.");
  process.exit(1);
}

let skipped = 0;
let failed = 0;
let interrupted = 0;
let unexpected = 0;
let executions = 0;
const projectExecutions = new Map();
const uniqueScenarios = new Set();

function visitSuite(suite) {
  for (const spec of suite.specs ?? []) {
    uniqueScenarios.add(spec.title);
    for (const test of spec.tests ?? []) {
      executions += 1;
      const projectName = test.projectName ?? test.projectId ?? "unknown";
      projectExecutions.set(projectName, (projectExecutions.get(projectName) ?? 0) + 1);
      if (test.status === "skipped") skipped += 1;
      for (const result of test.results ?? []) {
        if (result.status === "skipped") skipped += 1;
        if (result.status === "failed" || result.status === "timedOut") failed += 1;
        if (result.status === "interrupted") interrupted += 1;
        if (result.status === "unexpected") unexpected += 1;
      }
    }
  }
  for (const child of suite.suites ?? []) visitSuite(child);
}

for (const suite of report.suites ?? []) visitSuite(suite);

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

const artifactFiles = [...listFiles("test-results"), ...listFiles("playwright-report")];
const forbiddenArtifacts = artifactFiles.filter((file) => {
  const normalized = file.replaceAll("\\", "/").toLowerCase();
  return (
    normalized.endsWith("trace.zip") ||
    normalized.endsWith(".har") ||
    normalized.endsWith(".webm") ||
    normalized.endsWith(".mp4") ||
    normalized.includes("network") ||
    normalized.includes("request-body")
  );
});

const screenshotFiles = fs.existsSync("test-results")
  ? fs.readdirSync("test-results").filter((name) => name.endsWith(".png")).sort()
  : [];
const summary = {
  uniqueScenarios: uniqueScenarios.size,
  executions,
  projectExecutions: Object.fromEntries([...projectExecutions.entries()].sort()),
  skipped,
  failed,
  interrupted,
  unexpected,
  forbiddenArtifacts,
  screenshots: screenshotFiles.length,
  screenshotFiles,
};
console.log(JSON.stringify(summary, null, 2));

fs.writeFileSync("playwright-report/e2e-summary.json", `${JSON.stringify(summary, null, 2)}\n`);
fs.writeFileSync(
  "playwright-report/e2e-summary.md",
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
    `- Forbidden artifacts: ${summary.forbiddenArtifacts.length}`,
    `- Screenshots: ${summary.screenshots}`,
    "",
  ].join("\n"),
);

if (
  summary.uniqueScenarios < 20 ||
  summary.executions < 40 ||
  skipped > 0 ||
  failed > 0 ||
  interrupted > 0 ||
  unexpected > 0 ||
  summary.forbiddenArtifacts.length > 0 ||
  summary.screenshots < 9
) {
  process.exit(1);
}
