import { mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";
import { spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { app, repo, fromRepo, sha256 } from "./check-inputs.mjs";

const startedAt = new Date().toISOString();
const verificationId = startedAt.replace(/[-:.]/g, "") + "-" + randomUUID().slice(0, 8);
const npmCli = process.env.npm_execpath;
if (!npmCli) throw new Error("Run this through npm run verify.");
const target = fromRepo(`.intent-to-impact\\spikes\\STUDIO-LIVE-UI\\${verificationId}`);
mkdirSync(target, { recursive: true });
const commands = [];
for (const script of ["check:studio", "typecheck", "test", "build"]) {
  const result = spawnSync(process.execPath, [npmCli, "run", script], {
    cwd: app, encoding: "utf8", env: { ...process.env, CI: "true", NO_COLOR: "1" },
  });
  const stdout = result.stdout ?? "";
  const stderr = (result.stderr ?? "") + (result.error ? String(result.error) : "");
  const exitCode = result.status ?? 1;
  const log = join(target, `${script}.txt`);
  writeFileSync(log, `Command: npm run ${script}\nExit code: ${exitCode}\n\n${stdout}\n${stderr}`);
  commands.push({ command: `npm run ${script}`, exitCode, log: relative(repo, log), sha256: sha256(log) });
  process.stdout.write(stdout);
  process.stderr.write(stderr);
  if (exitCode !== 0) break;
}
function files(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    if (["node_modules", "dist", "coverage", ".git"].includes(entry.name)) return [];
    const path = join(directory, entry.name);
    return entry.isDirectory() ? files(path) : [path];
  });
}
const success = commands.length === 4 && commands.every((command) => command.exitCode === 0);
const receipt = {
  schemaVersion: "1.0.0", taskId: "STUDIO-LIVE-UI-001",
  status: success ? "frontend-build-and-tests-passed" : "validation-failed",
  startedAt, completedAt: new Date().toISOString(),
  commands, sourceFiles: files(app).sort().map((path) => ({ path: relative(repo, path), sha256: sha256(path) })),
  evidenceOrigin: "live-local",
  userFacingScope: ["prompt/document intake", "live job transport", "generated architecture canvas", "source-backed assurance", "compiled package transport"],
  liveInferenceTestedByThisRunner: false, humanUxApproval: "pending", cloudEffects: false,
  browserTesting: "separately recorded; this runner uses DOM tests and local build only",
  limitations: [
    "Successful tests do not constitute live model, compiler or provider proof; record actual end-to-end calls separately.",
    "Generated architectures and assurance remain model proposals, not approved or verified infrastructure.",
    "Text/Markdown document support; PDF/Word extraction remains separate.",
    "No compliance certification, actual price estimate, Azure deployment or runtime proof.",
  ],
};
const receiptPath = join(target, "receipt.json");
writeFileSync(receiptPath, JSON.stringify(receipt, null, 2) + "\n");
console.log(`Live studio frontend verification ${success ? "passed" : "failed"}: ${relative(repo, receiptPath)}`);
process.exitCode = success ? 0 : 1;
