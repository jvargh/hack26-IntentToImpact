import type { AnalysisRequest, BuildRequest, BuildResult, StudioJob, StudioResult, RunHistory, SavedRun } from "./contracts";
import { jobShape, buildShape, inputShape, requestBuildShape, historyShape, savedRunShape } from "./validators.js";

const safeId = /^[A-Za-z0-9_-]{1,80}$/;

export class StudioClientError extends Error {
  constructor(message: string, public readonly code = "request-failed", public readonly retryable = false) {
    super(message);
    this.name = "StudioClientError";
  }
}

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validateResult(result: StudioResult) {
  const analysis = result.analysis;
  const sources = new Set(result.sources.map((source) => source.id));
  const requirements = new Set(analysis.requirements.map((requirement) => requirement.id));
  const options = new Set(analysis.options.map((option) => option.id));
  if (sources.size !== result.sources.length || requirements.size !== analysis.requirements.length
    || options.size !== analysis.options.length || !options.has(analysis.recommendedOptionId)
    || new Set(analysis.review.map((finding) => finding.dimension)).size !== 9
    || new Set(result.modelReceipts.map((receipt) => receipt.role)).size !== 2) {
    throw new StudioClientError("The model result has inconsistent sources, alternatives or review records.", "invalid-result");
  }
  for (const item of [...analysis.requirements, ...analysis.review]) {
    if (item.sourceIds.some((id) => !sources.has(id))) throw new StudioClientError("A result cites an unavailable source.", "invalid-result");
  }
  for (const option of analysis.options) {
    const nodes = new Set(option.components.map((component) => component.id));
    if (nodes.size !== option.components.length || new Set(option.connections.map((edge) => edge.id)).size !== option.connections.length
      || option.connections.some((edge) => !nodes.has(edge.source) || !nodes.has(edge.target))
      || option.components.some((node) => node.requirementIds.some((id) => !requirements.has(id))
        || (node.externalDependency && !sources.has(node.externalDependency.sourceId)))) {
      throw new StudioClientError("The generated topology has unresolved component or requirement links.", "invalid-result");
    }
  }
}

export function validateJob(value: unknown): StudioJob {
  if (!jobShape(value)) throw new StudioClientError("The analysis service returned an invalid job response.", "invalid-response");
  if (!safeId.test(value.jobId)
    || (value.status === "succeeded" && (!value.result || value.error))
    || (value.status === "failed" && (!value.error || value.result))
    || (["queued", "running"].includes(value.status) && (value.result || value.error))) {
    throw new StudioClientError("The analysis status is inconsistent with its result.", "invalid-response");
  }
  if (value.result) validateResult(value.result);
  return value;
}

export function validateBuild(value: unknown): BuildResult {
  if (!buildShape(value) || !safeId.test(value.buildId)) {
    throw new StudioClientError("The build service returned an invalid package response.", "invalid-response");
  }
  const expected = `/api/studio/builds/${value.buildId}/download`;
  if (value.status === "compiled") {
    if (value.exitCode !== 0 || !value.compilerVersion || value.downloadUrl !== expected
      || !value.files.some((file) => file.path === "main.bicep")) {
      throw new StudioClientError("A successful package must include actual compilation evidence.", "invalid-response");
    }
  } else if (value.downloadUrl !== null) {
    throw new StudioClientError("An unsuccessful build cannot offer a completed package.", "invalid-response");
  }
  return value;
}

export class StudioClient {
  private csrf: string | null = null;
  private session: Promise<void> | null = null;

  private async request(path: string, init: RequestInit = {}): Promise<Response> {
    let response: Response;
    try {
      response = await fetch(path, {
        ...init, credentials: "same-origin", cache: "no-store", redirect: "error",
        headers: { "X-Studio-Client": "1", ...init.headers },
      });
    } catch (error) {
      if (object(error) && error.name === "AbortError") throw error;
      throw new StudioClientError("The live design service is unreachable. Your inputs have been kept; no example result was substituted.", "service-unavailable", true);
    }
    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => null);
      if (response.status === 401) this.csrf = null;
      throw new StudioClientError(
        object(payload) && typeof payload.message === "string" ? payload.message : `The service returned HTTP ${response.status}.`,
        object(payload) && typeof payload.code === "string" ? payload.code : "http-error",
        object(payload) && payload.retryable === true,
      );
    }
    return response;
  }

  private async json(path: string, init: RequestInit = {}): Promise<unknown> {
    const response = await this.request(path, init);
    try { return await response.json(); }
    catch { throw new StudioClientError("The live service returned unreadable JSON.", "invalid-response"); }
  }

  private async ensureSession(signal?: AbortSignal) {
    signal?.throwIfAborted();
    if (this.csrf) return;
    if (!this.session) {
      this.session = (async () => {
        const controller = new AbortController();
        const timer = window.setTimeout(() => controller.abort(), 15_000);
        try {
          const value = await this.json("/api/studio/session", { signal: controller.signal });
          if (!object(value) || typeof value.csrfToken !== "string" || value.csrfToken.length < 20) {
            throw new StudioClientError("The local session could not be established.", "invalid-session");
          }
          this.csrf = value.csrfToken;
        } catch (error) {
          if (controller.signal.aborted) throw new StudioClientError("The local session request timed out. Retry connecting.", "session-timeout", true);
          throw error;
        } finally {
          window.clearTimeout(timer);
        }
      })().finally(() => { this.session = null; });
    }
    await this.session;
    signal?.throwIfAborted();
  }

  async health(signal?: AbortSignal): Promise<{ ready: boolean; model: string; message: string; mode?: "live" | "simulated" }> {
    await this.ensureSession(signal);
    const value = await this.json("/api/studio/health", { signal });
    if (!object(value) || typeof value.ready !== "boolean" || typeof value.model !== "string" || typeof value.message !== "string") {
      throw new StudioClientError("The health response was invalid.", "invalid-response");
    }
    if (value.mode !== undefined && value.mode !== "live" && value.mode !== "simulated") {
      throw new StudioClientError("The service returned an unknown execution mode.", "invalid-response");
    }
    return { ready: value.ready, model: value.model, message: value.message, ...(value.mode ? { mode: value.mode } : {}) };
  }

  async analyze(input: AnalysisRequest, signal?: AbortSignal): Promise<StudioJob> {
    if (!inputShape(input)) throw new StudioClientError("Provide a business prompt, bounded documents and explicit consent to send them to Foundry.", "invalid-input");
    if (input.documents.reduce((sum, document) => sum + document.text.length, 0) > 150_000) {
      throw new StudioClientError("Keep combined document text within 150,000 characters.", "invalid-input");
    }
    await this.ensureSession(signal);
    return validateJob(await this.json("/api/studio/analyses", {
      method: "POST", signal, headers: { "Content-Type": "application/json", "X-CSRF-Token": this.csrf! },
      body: JSON.stringify(input),
    }));
  }

  async job(id: string, signal?: AbortSignal): Promise<StudioJob> {
    if (!safeId.test(id)) throw new StudioClientError("Invalid analysis job ID.", "invalid-input");
    await this.ensureSession(signal);
    return validateJob(await this.json(`/api/studio/jobs/${id}`, { signal }));
  }

  async history(signal?: AbortSignal): Promise<RunHistory> {
    await this.ensureSession(signal);
    const value = await this.json("/api/studio/history", { signal });
    if (!historyShape(value) || value.runs.some((run) => !safeId.test(run.jobId))) {
      throw new StudioClientError("The saved run list is invalid.", "invalid-response");
    }
    return value;
  }

  async historyRun(id: string, signal?: AbortSignal): Promise<SavedRun> {
    if (!safeId.test(id)) throw new StudioClientError("Invalid saved run ID.", "invalid-input");
    await this.ensureSession(signal);
    const value = await this.json(`/api/studio/history/${id}`, { signal });
    if (!savedRunShape(value) || value.job.jobId !== id || value.summary.jobId !== id
      || value.summary.status !== value.job.status || value.summary.resultId !== (value.job.result?.resultId ?? null)
      || value.summary.previousResultId !== value.inputs.previousResultId) {
      throw new StudioClientError("The saved run did not match its requested identity.", "invalid-response");
    }
    validateJob(value.job);
    if (value.builds.some((build) => !safeId.test(build.buildId) || build.resultId !== value.job.result?.resultId)) {
      throw new StudioClientError("A saved package does not belong to this run.", "invalid-response");
    }
    return value;
  }

  async historyBuild(jobId: string, buildId: string, signal?: AbortSignal): Promise<BuildResult> {
    if (!safeId.test(jobId) || !safeId.test(buildId)) throw new StudioClientError("Invalid saved package ID.", "invalid-input");
    await this.ensureSession(signal);
    const value = validateBuild(await this.json(`/api/studio/history/${jobId}/builds/${buildId}`, { signal }));
    if (value.buildId !== buildId) throw new StudioClientError("The saved package ID did not match.", "invalid-response");
    return value;
  }

  async downloadRun(jobId: string, signal?: AbortSignal): Promise<Blob> {
    if (!safeId.test(jobId)) throw new StudioClientError("Invalid saved run ID.", "invalid-input");
    await this.ensureSession(signal);
    const response = await this.request(`/api/studio/history/${jobId}/download`, { signal });
    if (!response.headers.get("content-type")?.includes("application/zip")) {
      throw new StudioClientError("The run record was not a ZIP archive.", "invalid-response");
    }
    return response.blob();
  }

  async build(input: BuildRequest, signal?: AbortSignal): Promise<BuildResult> {
    if (!requestBuildShape(input)) throw new StudioClientError("Select the current result and explicitly confirm package generation.", "invalid-input");
    await this.ensureSession(signal);
    const result = validateBuild(await this.json("/api/studio/builds", {
      method: "POST", signal, headers: { "Content-Type": "application/json", "X-CSRF-Token": this.csrf! },
      body: JSON.stringify(input),
    }));
    if (result.resultId !== input.resultId || result.optionId !== input.optionId) {
      throw new StudioClientError("The build receipt belongs to a different architecture selection.", "invalid-response");
    }
    return result;
  }

  async download(build: BuildResult, signal?: AbortSignal): Promise<Blob> {
    const validated = validateBuild(build);
    if (validated.status !== "compiled" || !validated.downloadUrl) throw new StudioClientError("Only a compiled package can be downloaded.", "build-incomplete");
    await this.ensureSession(signal);
    const response = await this.request(validated.downloadUrl, { signal });
    if (!response.headers.get("content-type")?.includes("application/zip")) {
      throw new StudioClientError("The download was not a deployment archive.", "invalid-response");
    }
    return response.blob();
  }
}
