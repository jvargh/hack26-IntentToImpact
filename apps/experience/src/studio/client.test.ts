import { afterEach, describe, expect, it, vi } from "vitest";
import { StudioClient, validateBuild, validateJob } from "./client";
import type { AnalysisRequest, BuildResult, ReviewFinding, StudioJob } from "./contracts";

const request: AnalysisRequest = {
  title: "Synthetic test", prompt: "A synthetic repair-booking service", documents: [], refinement: "",
  previousResultId: null, idempotencyKey: "synthetic-key-123", consentToModel: true,
};
const queued: StudioJob = { jobId: "job-test", status: "queued", events: [], result: null, error: null };
const dimensions: ReviewFinding["dimension"][] = ["business", "security", "reliability", "performance", "cost", "integration", "compliance", "operations", "delivery"];
const completed: StudioJob = {
  ...queued, status: "succeeded",
  result: {
    resultId: "result-test", inputHash: "test-hash", createdAt: "2026-09-13T00:00:00Z", origin: "live-model",
    sources: [{ id: "prompt", name: "User prompt" }],
    modelReceipts: [
      { role: "synthesis", model: "synthetic-test-model", responseId: "test-synthesis", durationMs: 1 },
      { role: "assurance", model: "synthetic-test-model", responseId: "test-assurance", durationMs: 1 },
    ],
    analysis: {
      title: "Synthetic result", summary: "Synthetic test only", businessProcess: ["Request repair", "Schedule repair"],
      requirements: [{ id: "r1", text: "Book repair", sourceIds: ["prompt"] }, { id: "r2", text: "Show status", sourceIds: ["prompt"] }],
      assumptions: [], questions: [], recommendedOptionId: "option-a", changeSummary: "Initial proposal",
      options: ["option-a", "option-b"].map((id) => ({
        id, name: id, rationale: "Synthetic alternative", tradeoffs: ["Needs actual validation"], costNotes: "No price estimate.",
        components: [
          { id: "client", kind: "client", label: "User", service: "Browser", responsibility: "Request", requirementIds: ["r1"] },
          { id: "app", kind: "appservice", label: "App", service: "App Service", responsibility: "Process", requirementIds: ["r2"] },
        ],
        connections: [{ id: "edge", source: "client", target: "app", label: "Request" }],
      })),
      review: dimensions.map((dimension) => ({ dimension, severity: "warning", finding: "Synthetic unverified concern", recommendation: "Validate", sourceIds: ["prompt"] })),
    },
  },
};
const build: BuildResult = {
  buildId: "build-test", resultId: "result-test", optionId: "option-a", status: "compiled",
  compilerVersion: "test-compiler", exitCode: 0, diagnostics: "",
  files: [{ path: "main.bicep", content: "// test only", sha256: "test" }],
  downloadUrl: "/api/studio/builds/build-test/download", limitations: ["No deployment performed"],
  deploymentStatus: "not-deployed",
};
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const session = () => json({ csrfToken: "synthetic-csrf-value-at-least-20" });
afterEach(() => vi.unstubAllGlobals());

describe("live studio transport", () => {
  it("bootstraps a same-origin session then sends actual input with CSRF and explicit model consent", async () => {
    const fetch = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(json(queued, 202));
    vi.stubGlobal("fetch", fetch);
    const client = new StudioClient();
    expect(await client.analyze(request)).toEqual(queued);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(fetch.mock.calls[0]?.[0]).toBe("/api/studio/session");
    const [path, init] = fetch.mock.calls[1]!;
    expect(path).toBe("/api/studio/analyses");
    expect(init).toMatchObject({
      method: "POST", credentials: "same-origin", redirect: "error",
      headers: { "X-Studio-Client": "1", "X-CSRF-Token": "synthetic-csrf-value-at-least-20" },
    });
    expect(JSON.parse(init.body)).toEqual(request);
  });

  it("rejects invalid consent/oversized documents before any network call", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    const client = new StudioClient();
    await expect(client.analyze({ ...request, prompt: "" })).rejects.toThrow("explicit consent");
    await expect(client.analyze({
      ...request, documents: [{ id: "a", name: "a", text: "x".repeat(100_000) }, { id: "b", name: "b", text: "x".repeat(100_000) }],
    })).rejects.toThrow("150,000");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("preserves meaningful API failure and never substitutes a sample result", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(
      json({ code: "model-unavailable", message: "Model access denied", retryable: false }, 503),
    ));
    await expect(new StudioClient().analyze(request)).rejects.toMatchObject({ code: "model-unavailable", message: "Model access denied" });
  });

  it("reports network failure and preserves AbortError cancellation semantics", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await expect(new StudioClient().health()).rejects.toThrow("no example result was substituted");
    const abort = new DOMException("Aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));
    await expect(new StudioClient().health()).rejects.toBe(abort);
  });

  it("rejects HTML and malformed JSON from an unavailable API", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>frontend fallback</html>")));
    await expect(new StudioClient().health()).rejects.toThrow("unreadable JSON");
  });

  it("distinguishes service readiness from completed model inference", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(json({ ready: false, model: "gpt-5.2", message: "Credential unavailable" })));
    expect((await new StudioClient().health()).ready).toBe(false);
  });

  it("bootstraps before protected health and does not share a caller's cancellation", async () => {
    let finish: ((response: Response) => void) | undefined;
    const fetch = vi.fn().mockImplementationOnce(() => new Promise<Response>((resolve) => { finish = resolve; }))
      .mockResolvedValueOnce(json({ ready: true, model: "test-model", message: "Configured only" }));
    vi.stubGlobal("fetch", fetch);
    const client = new StudioClient();
    const cancelled = new AbortController();
    const first = client.health(cancelled.signal).catch((error: unknown) => error);
    cancelled.abort();
    const second = client.health();
    finish!(session());
    expect(await first).toMatchObject({ name: "AbortError" });
    expect((await second).ready).toBe(true);
    expect(fetch.mock.calls.map((call) => call[0])).toEqual(["/api/studio/session", "/api/studio/health"]);
  });

  it("polls with the existing session and refuses unsafe job IDs", async () => {
    const fetch = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(json(queued)).mockResolvedValueOnce(json(completed));
    vi.stubGlobal("fetch", fetch);
    const client = new StudioClient();
    await client.analyze(request);
    expect((await client.job("job-test")).status).toBe("succeeded");
    expect(fetch.mock.calls.filter((call) => call[0] === "/api/studio/session")).toHaveLength(1);
    await expect(client.job("../secrets")).rejects.toThrow("Invalid analysis job");
  });

  it("validates graph, requirements, source, recommendation and assurance consistency", () => {
    expect(validateJob(completed)).toEqual(completed);
    expect(() => validateJob({ ...queued, status: "succeeded" })).toThrow("inconsistent");
    const bad = structuredClone(completed);
    bad.result!.analysis.options[0]!.connections[0]!.target = "missing";
    expect(() => validateJob(bad)).toThrow("unresolved");
    const source = structuredClone(completed);
    source.result!.analysis.review[0]!.sourceIds = ["invented"];
    expect(() => validateJob(source)).toThrow("unavailable source");
    const review = structuredClone(completed);
    review.result!.analysis.review[0]!.dimension = "delivery";
    expect(() => validateJob(review)).toThrow("inconsistent");
    const receipts = structuredClone(completed);
    receipts.result!.modelReceipts[1]!.role = "synthesis";
    expect(() => validateJob(receipts)).toThrow("inconsistent");
  });

  it("requires real compilation shape and a local exact-match download path", () => {
    expect(validateBuild(build)).toEqual(build);
    expect(() => validateBuild({ ...build, exitCode: 1 })).toThrow("compilation evidence");
    expect(() => validateBuild({ ...build, compilerVersion: null })).toThrow("compilation evidence");
    expect(() => validateBuild({ ...build, downloadUrl: "https://external.example/package.zip" })).toThrow("compilation evidence");
    expect(() => validateBuild({ ...build, status: "failed" })).toThrow("unsuccessful");
  });

  it("binds build receipts to the exact selected result and option", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(json(build)));
    await expect(new StudioClient().build({
      resultId: "another-result", optionId: "option-a", confirmGeneration: true, idempotencyKey: "test-build-key",
    })).rejects.toThrow("different architecture");
  });

  it("fetches only a validated ZIP over the authorized same-origin session", async () => {
    const fetch = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(new Response("zip-test-content", { headers: { "Content-Type": "application/zip" } }));
    vi.stubGlobal("fetch", fetch);
    const blob = await new StudioClient().download(build);
    expect(blob.size).toBeGreaterThan(0);
    expect(fetch.mock.calls[1]?.[0]).toBe(build.downloadUrl);
    await expect(new StudioClient().download({ ...build, status: "failed", downloadUrl: null })).rejects.toThrow("compiled package");
  });

  it("loads authenticated history and restores only the requested saved identity", async () => {
    const summary = {
      jobId: "job-test", title: "Saved", status: "succeeded", createdAt: "2026-09-13T00:00:00Z",
      updatedAt: "2026-09-13T00:00:01Z", documentCount: 0, resultId: "result-test",
      previousResultId: null, compiledPackageCount: 0, error: null,
    };
    const inputs = { title: request.title, prompt: request.prompt, documents: [], refinement: "", previousResultId: null };
    const saved = { scope: "workspace", summary, inputs, job: completed, builds: [] };
    const fetch = vi.fn().mockResolvedValueOnce(session())
      .mockResolvedValueOnce(json({ scope: "workspace", runs: [summary] }))
      .mockResolvedValueOnce(json(saved))
      .mockResolvedValueOnce(json({ ...saved, summary: { ...summary, status: "failed" } }));
    vi.stubGlobal("fetch", fetch);
    const client = new StudioClient();
    expect((await client.history()).runs).toHaveLength(1);
    expect((await client.historyRun("job-test")).job.result?.resultId).toBe("result-test");
    await expect(client.historyRun("job-test")).rejects.toThrow("requested identity");
    expect(fetch.mock.calls.every((call) => call[1].method === undefined)).toBe(true);
  });

  it("rejects unsafe history IDs and invalid archive content without fake recovery", async () => {
    const fetch = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(new Response("not a ZIP"));
    vi.stubGlobal("fetch", fetch);
    const client = new StudioClient();
    await expect(client.historyRun("../owner")).rejects.toThrow("Invalid saved run ID");
    await expect(client.historyBuild("job-test", "../zip")).rejects.toThrow("Invalid saved package ID");
    expect(fetch).not.toHaveBeenCalled();
    await expect(client.downloadRun("job-test")).rejects.toThrow("not a ZIP archive");
  });
});
