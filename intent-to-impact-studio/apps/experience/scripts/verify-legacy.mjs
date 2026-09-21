import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";
import { spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { app, repo, checkInputs, fromRepo, sha256, fixtureRoot, fixtureAcceptance } from "./check-inputs.mjs";

const startedAt = new Date().toISOString();
const verificationId = startedAt.replace(/[-:.]/g, "") + "-" + randomUUID().slice(0, 8);
const npmCli = process.env.npm_execpath;
if (!npmCli) throw new Error("Run this through npm run verify.");
const targets = ["UI-01-01", "UI-04-01"].map((taskId) => ({
  taskId, path: fromRepo(`.intent-to-impact\\spikes\\${taskId}\\R2\\${verificationId}`),
}));
for (const target of targets) mkdirSync(target.path, { recursive: true });
const commands = [];
for (const script of ["typecheck", "test", "build"]) {
  const args = [npmCli, "run", script];
  const result = spawnSync(process.execPath, args, {
    cwd: app, encoding: "utf8",
    env: { ...process.env, CI: "true", NO_COLOR: "1" },
  });
  const stdout = result.stdout ?? "";
  const stderr = (result.stderr ?? "") + (result.error ? String(result.error) : "");
  const exitCode = result.status ?? 1;
  const output = `Command: npm run ${script}\nExit code: ${exitCode}\n\nSTDOUT\n${stdout}\nSTDERR\n${stderr}`;
  process.stdout.write(stdout);
  process.stderr.write(stderr);
  for (const target of targets) writeFileSync(join(target.path, `${script}.txt`), output);
  commands.push({ command: `npm run ${script}`, executable: process.execPath, args, exitCode, log: `${script}.txt` });
  if (exitCode !== 0) break;
}
const success = commands.length === 3 && commands.every((command) => command.exitCode === 0);
function files(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    if (["node_modules", "dist", "coverage", ".git"].includes(entry.name)) return [];
    const path = join(directory, entry.name);
    return entry.isDirectory() ? files(path) : [path];
  });
}
const sourceHashes = files(app).sort().map((path) => ({ path: relative(repo, path), sha256: sha256(path) }));
const buildHashes = success ? files(join(app, "dist")).sort().map((path) => ({
  path: relative(repo, path), sha256: sha256(path),
})) : [];
const consumedInputs = success ? checkInputs().map((input) => ({ path: relative(repo, input.path), sha256: input.sha256 })) : [];
for (const target of targets) {
  const testPath = join(target.path, "test.txt");
  const testOutput = commands.some((command) => command.command === "npm run test") && existsSync(testPath)
    ? readFileSync(testPath, "utf8") : "";
  const count = testOutput.match(/Tests\s+(\d+)\s+passed/);
  const receipt = {
    schemaVersion: "1.0.0", taskId: target.taskId, parentPlanId: target.taskId.slice(0, 5),
    phase: "mock-first-initial-preview", deliveryClass: "P0-HERO", owner: "C-ui",
    reviewer: "implementation-orchestrator",
    status: success ? "runnable-early-preview-tests-and-build-passed" : "validation-failed",
    fullLiveTaskAcceptance: false, humanVisualApproval: "pending", humanGate: "GATE-UX01-pending",
    fixtureScenario: "DEMO-CASE-CLAIMS-V2", fixtureRevision: 2, fixtureRoot, fixtureAcceptance,
    currentDirection: "LOCAL-09: NSP Enforced, zero external access rules; V3 handoff pending",
    historicalNotice: "V2 public-endpoint examples are not current NSP proof.",
    runMode: "fixture", purpose: "ux-mock", liveProofEligible: false,
    startedAt, completedAt: new Date().toISOString(), testsPassed: count ? Number(count[1]) : null,
    validationEvidenceOrigin: "live-local", contentEvidenceOrigin: "fixture/ux-mock",
    commands: commands.map((command) => ({
      ...command, log: relative(repo, join(target.path, command.log)),
      logSha256: sha256(join(target.path, command.log)),
    })),
    artifacts: sourceHashes, buildArtifacts: buildHashes, consumedInputs,
    browserReview: "not-run; parent will start server and review",
    serverStartedByThisTask: false, screenshots: [],
    limits: [
      "Seven historical snapshots only, not all 18 interactions or the full FX catalog.",
      "No live API, model, cloud operation, workflow action, mode toggle or current NSP proof.",
      "Generated canonical types and local schema guards are consumed unchanged; no duplicate handwritten canonical model.",
      "Component tests use jsdom; no rendered browser screenshot, measured layout/zoom audit or human aesthetic approval is claimed.",
      "Full current V3 contracts/fixtures and later live API integration require separate accepted handoffs.",
    ],
    parentRunCommands: [
      "cd apps\\experience", "npm ci", "npm run verify",
      "npm run dev -- --port 5173 --strictPort",
      "Open http://127.0.0.1:5173/?view=legacy-risk&scene=FX-09",
    ],
  };
  writeFileSync(join(target.path, "evidence-receipt.json"), JSON.stringify(receipt, null, 2) + "\n");
  console.log(`Receipt: ${relative(repo, join(target.path, "evidence-receipt.json"))}`);
}
console.log(`Early preview verification ${success ? "passed" : "failed"}. No server or browser review started.`);
process.exitCode = success ? 0 : 1;
