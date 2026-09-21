import manifest from "../../../../fixtures/experience/initial-v2-r2/manifest.json";
import actionMap from "../../../../fixtures/experience/initial-v2-r2/action-map.json";
import runText from "../../../../fixtures/experience/initial-v2-r2/run-manifest.json?raw";
import type { ArtifactLink, ExperienceOverview } from "@contracts/projections";
import { isArtifactLink, isFixtureRecord, isObject, isOverview, isRun } from "./contracts";
import type { FixtureRecord } from "./contracts";

export const HISTORICAL_NOTICE = "V2 public-endpoint examples are not current NSP proof.";
export const SCENARIO_HASH = "sha256:a140b136272f077c82dcd1d38e8e2c13b0aa7aea192be2a80112ccc744213e9a";
const titles: Readonly<Record<string, string>> = {
  "FX-01": "01 · Promise — unconfirmed",
  "FX-09": "02 · At risk — HTTPS disabled",
  "FX-10": "03 · Correction — prepared",
  "FX-11": "04 · Restoration — pending",
  "FX-12": "05 · Restoration — fixture verified",
  "FX-11:missing-evidence": "06 · Evidence — missing",
  "FX-09:stale-evidence": "07 · Evidence — stale",
};
const modules = import.meta.glob<string>(
  "../../../../fixtures/experience/initial-v2-r2/scenes/*/*.json",
  { query: "?raw", import: "default", eager: true },
);
const bundledFiles: Record<string, string> = {};
for (const [path, text] of Object.entries(modules)) {
  const relative = path.split("/initial-v2-r2/")[1];
  if (!relative) throw new Error("Invalid bundled fixture path.");
  bundledFiles[relative.replaceAll("/", "\\")] = text;
}

export interface FixtureInputs {
  manifest: typeof manifest;
  actionMap: typeof actionMap;
  runText: string;
  files: Readonly<Record<string, string>>;
}
export const defaultInputs: FixtureInputs = { manifest, actionMap, runText, files: bundledFiles };

export interface SceneChoice { id: string; label: string }
export interface LoadedScene {
  id: string;
  primaryActionId: string;
  response: ExperienceOverview;
  records: readonly FixtureRecord[];
}
export type NavigationResult = { kind: "scene"; scene: LoadedScene } | { kind: "inspect-records" };
export interface FixtureTransport {
  readonly mode: "fixture";
  readonly choices: readonly SceneChoice[];
  readonly initialSceneId: string;
  loadScene(id: string): Promise<LoadedScene>;
  navigate(scene: LoadedScene, actionId: string): Promise<NavigationResult>;
}

export class FixtureError extends Error {}
function requireFixture(condition: boolean, message: string): asserts condition {
  if (!condition) throw new FixtureError(message);
}
export async function hashText(text: string): Promise<string> {
  requireFixture(Boolean(globalThis.crypto?.subtle), "Secure local browser context is required for fixture integrity.");
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return "sha256:" + Array.from(new Uint8Array(bytes), (byte) => byte.toString(16).padStart(2, "0")).join("");
}
async function parseFile(text: string | undefined, checksum: string, label: string): Promise<unknown> {
  requireFixture(typeof text === "string", `Missing fixture data: ${label}. No live fallback is available.`);
  requireFixture(await hashText(text) === checksum, `Fixture integrity check failed: ${label}.`);
  try { return JSON.parse(text); } catch { throw new FixtureError(`Malformed fixture JSON: ${label}.`); }
}

function* objects(value: unknown): Generator<Record<string, unknown>> {
  if (isObject(value)) {
    yield value;
    for (const child of Object.values(value)) yield* objects(child);
  } else if (Array.isArray(value)) {
    for (const child of value) yield* objects(child);
  }
}

function assertMock(value: unknown): void {
  for (const object of objects(value)) {
    if ("runMode" in object) {
      requireFixture(object.runMode === "fixture" && object.purpose === "ux-mock", "Unsafe run mode: this preview is fixture/ux-mock only.");
    }
    if ("origin" in object) requireFixture(object.origin === "fixture", "Unsafe evidence origin in fixture data.");
    if ("scenarioOrigin" in object) requireFixture(object.scenarioOrigin === "fixture", "Unsafe projection origin.");
    if (object.artifactType === "evidence-reference") {
      requireFixture(object.eligibility === "ineligible", "Fixture evidence cannot be eligible for live proof.");
    }
    if (object.artifactType === "sandbox-operation-receipt") {
      requireFixture(typeof object.providerOperationId === "string" && object.providerOperationId.startsWith("fixture-"),
        "A fixture cannot claim an actual provider operation.");
    }
    if ("scenarioId" in object) {
      requireFixture(object.scenarioId === "DEMO-CASE-CLAIMS-V2" && object.scenarioVersion === "2.0.0"
        && object.scenarioHash === SCENARIO_HASH, "Unexpected scenario. Request a versioned fixture handoff; V2 cannot become current NSP proof.");
    }
  }
}

export function createFixtureTransport(inputs: FixtureInputs = defaultInputs): FixtureTransport {
  const choices = inputs.manifest.scenes.map((entry) => ({ id: entry.sceneId, label: titles[entry.sceneId] ?? entry.sceneId }));

  function assertArchive(): void {
    const transport = inputs.actionMap.transport;
    requireFixture(inputs.manifest.fixtureRevision === 2,
      "Only validated fixture revision R2 is loadable. Original initial-v2 is historical evidence, not valid preview data.");
    requireFixture(inputs.manifest.runMode === "fixture" && inputs.manifest.purpose === "ux-mock"
      && inputs.manifest.liveProofEligible === false && inputs.manifest.fullFxCatalogComplete === false,
    "Unsafe fixture manifest. Mode cannot switch to live.");
    requireFixture(transport.kind === "in-memory-fixture" && transport.networkAccess === false
      && transport.liveEndpoints.length === 0 && transport.immutableRunMode === true && transport.executesWorkflow === false,
    "Unsafe transport declaration. Only local authored snapshots are permitted.");
    assertMock(inputs.manifest.scenario);
    assertMock(inputs.actionMap.scenario);
    requireFixture(new Set(choices.map((choice) => choice.id)).size === choices.length, "Duplicate fixture scene.");
  }

  async function loadScene(id: string): Promise<LoadedScene> {
    assertArchive();
    const entry = inputs.manifest.scenes.find((scene) => scene.sceneId === id);
    requireFixture(Boolean(entry), `Unknown scene: ${id}. Select an authored snapshot.`);
    if (!entry) throw new FixtureError("Missing scene.");
    const rawRun = await parseFile(inputs.runText, inputs.manifest.runManifestSha256, "run context");
    requireFixture(isRun(rawRun), "Fixture run does not match the generated contract.");
    assertMock(rawRun);
    const [response, bundle] = await Promise.all([
      parseFile(inputs.files[entry.response], entry.responseSha256, entry.response),
      parseFile(inputs.files[entry.records], entry.recordsSha256, entry.records),
    ]);
    requireFixture(isOverview(response), "Projection data does not match frozen P01/P05/P06. Preview stopped.");
    requireFixture(isObject(bundle) && Array.isArray(bundle.records) && Array.isArray(bundle.externalReferences),
      "Missing referenced fixture records.");
    const records: FixtureRecord[] = [];
    for (const value of bundle.records) {
      requireFixture(isFixtureRecord(value), "A referenced fixture record does not match its generated contract.");
      records.push(value);
    }
    const externals: ArtifactLink[] = [];
    for (const value of bundle.externalReferences) {
      requireFixture(isArtifactLink(value) && ["D10", "D11", "D12"].includes(value.contractId), "Unsafe external fixture reference.");
      externals.push(value);
    }
    assertMock([response, records, externals]);
    const recordIndex = new Map(records.map((record) => [record.artifactId, record]));
    requireFixture(recordIndex.size === records.length, "Duplicate referenced record.");
    for (const record of [response, ...records]) {
      requireFixture(record.runId === rawRun.runId && record.caseId === rawRun.caseId
        && JSON.stringify(record.scope) === JSON.stringify(rawRun.scope), "Fixture/run context mismatch.");
      for (const object of objects(record)) {
        if (isArtifactLink(object)) {
          const target = recordIndex.get(object.artifact.artifactId);
          requireFixture(target ? target.stateChecksum === object.artifact.checksum
            : externals.some((external) => JSON.stringify(external) === JSON.stringify(object)),
          "Missing or mismatched referenced fixture record.");
        }
      }
    }
    for (const embedded of [response.operationsRisk, response.continuityGraph]) {
      requireFixture(recordIndex.get(embedded.artifactId)?.stateChecksum === embedded.stateChecksum,
        "Embedded projection disagrees with loaded records.");
    }
    const graph = response.continuityGraph;
    const nodeIds = new Set(graph.nodes.map((node) => node.nodeId));
    requireFixture(nodeIds.size === graph.nodes.length && graph.listEntries.length === graph.nodes.length,
      "Graph/list node mismatch.");
    for (const edge of graph.edges) {
      requireFixture(nodeIds.has(edge.fromNodeId) && nodeIds.has(edge.toNodeId), "Missing graph endpoint.");
    }
    for (const node of graph.nodes) {
      const list = graph.listEntries.find((item) => item.nodeId === node.nodeId);
      const incident = graph.edges.filter((edge) => edge.fromNodeId === node.nodeId || edge.toNodeId === node.nodeId);
      requireFixture(Boolean(list) && list?.relatedEdgeIds.length === incident.length
        && incident.every((edge) => list?.relatedEdgeIds.includes(edge.edgeId)), "Graph/list edge mismatch.");
      if (node.source.kind === "artifact") {
        requireFixture(recordIndex.has(node.source.reference.artifact.artifactId), "Opaque references cannot become graph proof.");
      }
    }
    const restoration = response.operationsRisk.restoration;
    if (restoration.status === "verified") {
      const proof = restoration.verificationEvaluation
        ? recordIndex.get(restoration.verificationEvaluation.artifact.artifactId) : undefined;
      requireFixture(proof?.artifactType === "promise-evaluation" && proof.phase === "runtime"
        && proof.status === "verified" && proof.evidence.length > 0, "Verified presentation has no matching fixture verification record.");
    }
    requireFixture(response.allowedActions.some((action) => action.actionId === entry.primaryActionId),
      "Primary action is not issued by this snapshot.");
    const seen = new Set<string>();
    for (const action of response.allowedActions) {
      requireFixture(action.capability === "read-case" && /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/.test(action.actionId)
        && !seen.has(action.actionId), "Unsafe or duplicate fixture action.");
      seen.add(action.actionId);
      const matches = inputs.actionMap.transitions.filter((item) => item.fromSceneId === id && item.actionId === action.actionId);
      requireFixture(matches.length === 1 && matches[0]?.executesWorkflow === false
        && choices.some((choice) => choice.id === matches[0]?.toSceneId)
        && ["load-authored-snapshot", "inspect-records"].includes(matches[0]?.effect ?? ""),
      "Action has no safe, exact canned response.");
    }
    return { id, primaryActionId: entry.primaryActionId, response, records };
  }

  return Object.freeze({
    mode: "fixture",
    choices: Object.freeze(choices),
    initialSceneId: inputs.manifest.initialSceneId,
    loadScene,
    async navigate(scene: LoadedScene, actionId: string): Promise<NavigationResult> {
      assertArchive();
      requireFixture(scene.response.allowedActions.some((action) => action.actionId === actionId),
        `Unknown action: ${actionId}. No workflow action was executed.`);
      const transition = inputs.actionMap.transitions.find((item) => item.fromSceneId === scene.id && item.actionId === actionId);
      requireFixture(Boolean(transition) && transition?.executesWorkflow === false, "Missing safe canned transition.");
      if (!transition) throw new FixtureError("Missing transition.");
      if (transition.effect === "inspect-records") return { kind: "inspect-records" };
      requireFixture(transition.effect === "load-authored-snapshot", "Unsupported fixture effect.");
      return { kind: "scene", scene: await loadScene(transition.toSceneId) };
    },
  });
}
