import { describe, expect, it, vi } from "vitest";
import { createFixtureTransport, defaultInputs, hashText } from "./fixtureTransport";
import type { FixtureInputs } from "./fixtureTransport";
import { isObject, isRun } from "./contracts";

async function replaceResponse(inputs: FixtureInputs, id: string, value: unknown) {
  const entry = inputs.manifest.scenes.find((item) => item.sceneId === id);
  if (!entry) throw new Error("Test scene missing");
  const text = JSON.stringify(value);
  inputs.files = { ...inputs.files, [entry.response]: text };
  entry.responseSha256 = await hashText(text);
}

describe("immutable fixture transport", () => {
  it("loads all seven complete typed snapshots without a live request", async () => {
    const request = vi.fn();
    vi.stubGlobal("fetch", request);
    const transport = createFixtureTransport();
    expect(transport.choices).toHaveLength(7);
    for (const choice of transport.choices) {
      const scene = await transport.loadScene(choice.id);
      expect(scene.response.runId).toBe("RUN-UX-MOCK-CLAIMS-V2-R2");
      expect(scene.response.caseId).toBe("CASE-UX-MOCK-CLAIMS-V2-R2");
      expect(scene.response.artifactId).toContain("-MOCK-R2-");
      expect(scene.response.runMode).toBe("fixture");
      expect(scene.response.purpose).toBe("ux-mock");
      expect(scene.response.scenarioOrigin).toBe("fixture");
      expect(scene.response.continuityGraph.listEntries).toHaveLength(scene.response.continuityGraph.nodes.length);
    }
    expect(request).not.toHaveBeenCalled();
  });

  it("rejects the superseded revision rather than falling back to initial-v2", async () => {
    const inputs = structuredClone(defaultInputs);
    inputs.manifest.fixtureRevision = 1;
    await expect(createFixtureTransport(inputs).loadScene("FX-09")).rejects.toThrow("Only validated fixture revision R2");
  });

  it("preserves Unicode display copy with the accepted R2 checksum/reference data", async () => {
    const scene = await createFixtureTransport().loadScene("FX-09");
    expect(scene.response.stateChecksum).toBe("sha256:6eaa60fd8bb17928e5df2c0b7b4899b8b3cb51b565a008911a0dc2f12ecd849e");
    expect(scene.response.continuityGraph.nodes.some((node) => node.label.includes("—"))).toBe(true);
    expect(scene.response.scenario.scenarioHash).toBe(defaultInputs.manifest.scenario.scenarioHash);
  });

  it("uses the exact issued action and a canned whole-snapshot response", async () => {
    const transport = createFixtureTransport();
    const risk = await transport.loadScene("FX-09");
    const result = await transport.navigate(risk, "review-correction-example");
    expect(result.kind).toBe("scene");
    if (result.kind === "scene") {
      expect(result.scene.id).toBe("FX-10");
      expect(result.scene.response.operationsRisk.restoration.status).toBe("prepared");
    }
    await expect(transport.navigate(risk, "REVIEW-CORRECTION")).rejects.toThrow("Unknown action");
    await expect(transport.loadScene("FX-99")).rejects.toThrow("Unknown scene");
  });

  it("opens loaded evidence without advancing workflow", async () => {
    const transport = createFixtureTransport();
    const restored = await transport.loadScene("FX-12");
    expect(await transport.navigate(restored, "inspect-fixture-evidence")).toEqual({ kind: "inspect-records" });
  });

  it("rejects missing and hash-mismatched response bytes", async () => {
    const missing = structuredClone(defaultInputs);
    missing.files = {};
    await expect(createFixtureTransport(missing).loadScene("FX-09")).rejects.toThrow("Missing fixture data");
    const corrupt = structuredClone(defaultInputs);
    const entry = corrupt.manifest.scenes.find((item) => item.sceneId === "FX-09");
    if (!entry) throw new Error("Test scene missing");
    corrupt.files = { ...corrupt.files, [entry.response]: "{}" };
    await expect(createFixtureTransport(corrupt).loadScene("FX-09")).rejects.toThrow("integrity check failed");
  });

  it("rejects malformed canonical data even when a file hash is supplied", async () => {
    const inputs = structuredClone(defaultInputs);
    const scene = await createFixtureTransport().loadScene("FX-09");
    const malformed: Record<string, unknown> = { ...scene.response };
    delete malformed.operationsRisk;
    await replaceResponse(inputs, "FX-09", malformed);
    await expect(createFixtureTransport(inputs).loadScene("FX-09")).rejects.toThrow("frozen P01/P05/P06");
  });

  it("rejects live mode rather than switching transport", async () => {
    const inputs = structuredClone(defaultInputs);
    const run: unknown = JSON.parse(inputs.runText);
    if (!isRun(run)) throw new Error("Test run is invalid");
    run.runMode = "live";
    inputs.runText = JSON.stringify(run);
    inputs.manifest.runManifestSha256 = await hashText(inputs.runText);
    await expect(createFixtureTransport(inputs).loadScene("FX-09")).rejects.toThrow(/Fixture run|fixture\/ux-mock only/);
    const transport = createFixtureTransport();
    expect(Reflect.set(transport, "mode", "live")).toBe(false);
    expect(transport.mode).toBe("fixture");
    expect(Object.keys(transport)).not.toContain("setMode");
  });

  it("rejects network-enabled declarations before loading", async () => {
    const inputs = structuredClone(defaultInputs);
    inputs.actionMap.transport.networkAccess = true;
    await expect(createFixtureTransport(inputs).loadScene("FX-09")).rejects.toThrow("Unsafe transport declaration");
  });

  it("does not silently reinterpret the V2 snapshot as current V3", async () => {
    const inputs = structuredClone(defaultInputs);
    inputs.manifest.scenario.scenarioId = "DEMO-CASE-CLAIMS-V3";
    await expect(createFixtureTransport(inputs).loadScene("FX-09")).rejects.toThrow("versioned fixture handoff");
  });

  it("rejects a false verified label without its supplied verification record", async () => {
    const inputs = structuredClone(defaultInputs);
    const scene = await createFixtureTransport().loadScene("FX-10");
    scene.response.operationsRisk.restoration.status = "verified";
    scene.response.operationsRisk.restoration.verificationEvaluation = null;
    await replaceResponse(inputs, "FX-10", scene.response);
    await expect(createFixtureTransport(inputs).loadScene("FX-10")).rejects.toThrow("no matching fixture verification record");
  });

  it("rejects missing referenced records rather than rendering unsupported proof", async () => {
    const inputs = structuredClone(defaultInputs);
    const entry = inputs.manifest.scenes.find((item) => item.sceneId === "FX-09");
    if (!entry) throw new Error("Test scene missing");
    const raw: unknown = JSON.parse(inputs.files[entry.records] ?? "{}");
    if (!isObject(raw)) throw new Error("Test bundle invalid");
    raw.records = [];
    const text = JSON.stringify(raw);
    inputs.files = { ...inputs.files, [entry.records]: text };
    entry.recordsSha256 = await hashText(text);
    await expect(createFixtureTransport(inputs).loadScene("FX-09")).rejects.toThrow("referenced fixture record");
  });
});
