import fs from "node:fs";
import { processE2eReport } from "./run-e2e.mjs";

const reportPath = "playwright-report/results.json";
const rawJson = fs.existsSync(reportPath) ? fs.readFileSync(reportPath, "utf8") : "";
const processed = processE2eReport(rawJson, { playwrightExitCode: rawJson ? 0 : 1 });

console.log(JSON.stringify(processed.summary, null, 2));
if (processed.validationFailures.length > 0) {
  console.error(`E2E validation failed: ${processed.validationFailures.join(", ")}`);
  process.exit(1);
}
