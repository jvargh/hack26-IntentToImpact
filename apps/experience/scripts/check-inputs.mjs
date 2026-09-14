import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

export const app = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const repo = resolve(app, "..", "..");
export const fromRepo = (path) => resolve(repo, ...path.split(/[\\/]/));
export const sha256 = (file) => "sha256:" + createHash("sha256").update(readFileSync(file)).digest("hex");
export const fixtureRoot = "fixtures\\experience\\initial-v2-r2";
export const fixtureAcceptance = ".intent-to-impact\\spikes\\MOCK-01-01\\R2\\20260913T014015Z-d3614a83\\evidence-receipt.json";
const read = (path) => JSON.parse(readFileSync(path, "utf8"));
const assert = (condition, message) => { if (!condition) throw new Error(message); };

export function checkInputs() {
  const bundle = fromRepo(fixtureRoot);
  const manifestPath = resolve(bundle, "manifest.json");
  const manifest = read(manifestPath);
  const acceptancePath = fromRepo(fixtureAcceptance);
  const acceptance = read(acceptancePath);
  assert(acceptance.fixtureRevision === 2 && acceptance.exitCode === 0,
    "R2 fixture validation receipt is missing or unsuccessful.");
  const approvedManifest = acceptance.artifacts.find((item) =>
    item.path.replaceAll("/", "\\") === `${fixtureRoot}\\manifest.json`);
  assert(approvedManifest && sha256(manifestPath) === approvedManifest.sha256,
    "Fixture manifest differs from its accepted evidence. Request a versioned handoff; do not edit it.");
  assert(manifest.fixtureRevision === 2 && manifest.scenario.scenarioId === "DEMO-CASE-CLAIMS-V2"
    && manifest.scenario.scenarioHash === "sha256:a140b136272f077c82dcd1d38e8e2c13b0aa7aea192be2a80112ccc744213e9a"
    && manifest.runMode === "fixture" && manifest.purpose === "ux-mock" && !manifest.liveProofEligible,
  "Only the accepted historical V2 fixture context is permitted.");
  const checked = [
    { path: manifestPath, sha256: sha256(manifestPath) },
    { path: acceptancePath, sha256: sha256(acceptancePath) },
  ];
  function check(relative, expected) {
    const path = resolve(bundle, ...relative.split(/[\\/]/));
    assert(path.startsWith(bundle + sep), "Unsafe fixture path.");
    assert(sha256(path) === expected, `Frozen fixture drift: ${relative}`);
    checked.push({ path, sha256: expected });
  }
  check(manifest.runManifest, manifest.runManifestSha256);
  check(manifest.actionMap, manifest.actionMapSha256);
  for (const scene of manifest.scenes) {
    check(scene.response, scene.responseSha256);
    check(scene.records, scene.recordsSha256);
  }
  for (const input of manifest.inputFiles.filter((item) => item.path.replaceAll("/", "\\").startsWith("contracts\\schemas\\"))) {
    const path = fromRepo(input.path);
    assert(sha256(path) === input.sha256, `Frozen V2 schema changed: ${input.path}. Request handoff.`);
    checked.push({ path, sha256: input.sha256 });
  }
  const tokenPath = fromRepo("design\\tokens\\tokens.v2-manifest.json");
  const tokens = read(tokenPath);
  checked.push({ path: tokenPath, sha256: sha256(tokenPath) });
  for (const source of [tokens.valueSource, tokens.css]) {
    const path = fromRepo(source.path);
    const expected = source.sha256.startsWith("sha256:") ? source.sha256 : "sha256:" + source.sha256;
    assert(sha256(path) === expected, `Shared token source changed: ${source.path}`);
    checked.push({ path, sha256: expected });
  }
  for (const type of ["core", "risk", "projections"]) {
    const path = fromRepo(`contracts\\generated\\1.0.0\\typescript\\${type}.d.ts`);
    checked.push({ path, sha256: sha256(path) });
  }
  return checked;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  console.log(`${checkInputs().length} R2 handoff/fixture/schema/type/token inputs verified; historical V2 only.`);
}
