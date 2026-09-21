import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { StudioApp } from "./StudioApp";
import { StudioClient, validateJob } from "./client";
import type { AnalysisRequest, BuildRequest, BuildResult, ReviewFinding, StudioJob, StudioResult, RunHistory, SavedRun } from "./contracts";

const dimensions: ReviewFinding["dimension"][] = ["business", "security", "reliability", "performance", "cost", "integration", "compliance", "operations", "delivery"];
function result(id = "result-one", prompt = "Support process", sourceIds = ["prompt"]): StudioResult {
  return {
    resultId: id, inputHash: `hash-${id}`, createdAt: "2026-09-13T12:00:00Z", origin: "live-model",
    sources: sourceIds.map((sourceId) => ({ id: sourceId, name: sourceId === "prompt" ? "Original prompt" : "process.md" })),
    modelReceipts: [{ role: "synthesis", model: "test-model", responseId: "response-one", durationMs: 120 }, { role: "assurance", model: "test-model", responseId: "response-two", durationMs: 150 }],
    analysis: {
      title: prompt, summary: `Architecture for ${prompt}`, businessProcess: ["Receive request", "Complete request"],
      requirements: [{ id: "r1", text: `${prompt} must be reliable`, sourceIds }, { id: "r2", text: "Retain status", sourceIds: ["prompt"] }],
      assumptions: ["Workload not measured"], questions: [{ id: "q1", question: "Who owns operations?", why: "An accountable owner is needed." }],
      options: [
        { id: "first", name: "Modular service", rationale: "Keep related responsibilities together.", tradeoffs: ["Shared scaling boundary"], costNotes: "Cost is not priced.", components: [
          { id: "api", label: "Request API", kind: "appservice", service: "Azure App Service", responsibility: "Accept requests.", requirementIds: ["r1"] },
          { id: "data", label: "Status store", kind: "storage", service: "Azure Storage", responsibility: "Retain status.", requirementIds: ["r2"] },
        ], connections: [{ id: "e1", source: "api", target: "data", label: "Persist status" }] },
        { id: "second", name: "Event-driven service", rationale: "Separate asynchronous work.", tradeoffs: ["More operational components"], costNotes: "Usage-based; not a quote.", components: [
          { id: "worker", label: "Queue worker", kind: "functions", service: "Azure Functions", responsibility: "Process queued events.", requirementIds: ["r1"] },
          { id: "queue", label: "Request queue", kind: "servicebus", service: "Azure Service Bus", responsibility: "Buffer requests.", requirementIds: ["r1"] },
          { id: "erp", label: "Existing ERP", kind: "external", service: "Existing system", responsibility: "Retain records.", requirementIds: ["r2"] },
        ], connections: [{ id: "e2", source: "queue", target: "worker", label: "Deliver request" }, { id: "e3", source: "worker", target: "erp", label: "Update record" }] },
      ],
      recommendedOptionId: "first", review: dimensions.map((dimension) => ({ dimension, severity: dimension === "reliability" ? "warning" : "info", finding: `${dimension} assessment`, recommendation: `Review ${dimension} with owners.`, sourceIds: ["prompt"] })),
      changeSummary: `${id} changed requirements and service boundaries.`,
    },
  };
}
function succeeded(value = result()): StudioJob { return { jobId: "job-one", status: "succeeded", events: [{ sequence: 1, stage: "complete", message: "Validated model response", at: "2026-09-13T12:00:00Z" }], result: value, error: null }; }
function blockedResult(): StudioResult {
  const value = result();
  value.analysis.review = value.analysis.review.map((finding) => finding.dimension === "security" ? {
    ...finding, severity: "blocker",
    finding: "The provider is not proven to obtain a same-tenant Entra token.",
    recommendation: "Design a controlled adapter and document signature validation, idempotency and replay protection.",
  } : finding);
  return value;
}
function securityFinding(): ReviewFinding {
  const finding = blockedResult().analysis.review.find((item) => item.dimension === "security");
  if (!finding) throw new Error("The test fixture must include a security finding.");
  return finding;
}
function approvedJob(input: AnalysisRequest, severity: ReviewFinding["severity"] = "warning"): StudioJob {
  if (!input.designChange || !input.previousResultId) throw new Error("Expected a contextual revision request.");
  const updated = result("result-two", "Revised support process", ["prompt", "refinement"]);
  updated.analysis.review = updated.analysis.review.map((finding) => finding.dimension === "security"
    ? { ...finding, severity, finding: "Adapter implementation and callback authentication still need verification.", sourceIds: ["refinement"] } : finding);
  return { ...succeeded(updated), jobId: "job-two", changeApproval: {
    baseResultId: input.previousResultId, baseResultHash: "a".repeat(64), optionId: input.designChange.optionId,
    finding: input.designChange.finding, intent: input.designChange.intent, instruction: input.refinement,
    refinement: `Server-bound finding and option context.\n${input.refinement}`, approvedAt: "2026-09-13T12:01:00Z",
    actor: "demo-human", scope: "design-revision-only",
  } };
}
function pending(status: "queued" | "running"): StudioJob { return { jobId: "job-one", status, events: [{ sequence: 1, stage: status === "queued" ? "intake" : "synthesis", message: status === "queued" ? "Request queued" : "Calling synthesis model", at: "2026-09-13T12:00:00Z" }], result: null, error: null }; }
function packageResult(status: BuildResult["status"] = "compiled"): BuildResult {
  return { buildId: "build-one", resultId: "result-one", optionId: "first", status, compilerVersion: status === "blocked" ? null : "Bicep CLI 0.41.2", exitCode: status === "compiled" ? 0 : status === "blocked" ? null : 1, diagnostics: status === "compiled" ? "Compilation completed." : "Compiler rejected unsupported configuration.", files: [{ path: "main.bicep", content: "targetScope = 'resourceGroup'\nparam location string", sha256: "a".repeat(64) }], downloadUrl: status === "compiled" ? "/api/studio/builds/build-one/download" : null, limitations: ["Existing ERP must be configured separately."], deploymentStatus: "not-deployed" };
}
function savedRun(): SavedRun {
  return {
    scope: "workspace",
    summary: { jobId: "job-one", title: "Saved support design", status: "succeeded", createdAt: "2026-09-13T12:00:00Z",
      updatedAt: "2026-09-13T12:01:00Z", documentCount: 0, resultId: "result-one",
      previousResultId: null, compiledPackageCount: 0, error: null },
    inputs: { title: "Saved support design", prompt: promptText, documents: [], refinement: "", previousResultId: null },
    job: succeeded(), builds: [],
  };
}
class TestClient extends StudioClient {
  health = vi.fn(async (_signal?: AbortSignal) => ({ ready: true, model: "test-model", message: "Configuration ready; no inference performed." }));
  analyze = vi.fn(async (_input: AnalysisRequest, _signal?: AbortSignal): Promise<StudioJob> => succeeded());
  job = vi.fn(async (_id: string, _signal?: AbortSignal): Promise<StudioJob> => succeeded());
  build = vi.fn(async (_input: BuildRequest, _signal?: AbortSignal): Promise<BuildResult> => packageResult());
  download = vi.fn(async (_build: BuildResult, _signal?: AbortSignal): Promise<Blob> => new Blob(["test archive"], { type: "application/zip" }));
  history = vi.fn(async (_signal?: AbortSignal): Promise<RunHistory> => ({ scope: "workspace", runs: [savedRun().summary] }));
  historyRun = vi.fn(async (_id: string, _signal?: AbortSignal): Promise<SavedRun> => savedRun());
  historyBuild = vi.fn(async (_job: string, _build: string, _signal?: AbortSignal): Promise<BuildResult> => packageResult());
  downloadRun = vi.fn(async (_job: string, _signal?: AbortSignal): Promise<Blob> => new Blob(["history archive"], { type: "application/zip" }));
}
function submittedChange(client: TestClient): AnalysisRequest {
  const input = client.analyze.mock.calls[1]?.[0];
  if (!input) throw new Error("Expected an explicit revision request after initial generation.");
  return input;
}
const promptText = "Improve our support request process and keep an audit trail.";
function enterPrompt(text = promptText) { fireEvent.change(screen.getByRole("textbox", { name: "What should this system do?" }), { target: { value: text } }); }
function consent() { fireEvent.click(screen.getByRole("checkbox", { name: /I consent to send/ })); }
async function generate() {
  enterPrompt(); consent(); fireEvent.click(screen.getByRole("button", { name: "Generate architecture" }));
  await screen.findByText("LIVE MODEL RESULT");
}
function uploadedFile() {
  const text = "Exact document: support owns the human handoff.";
  const file = new File([text], "process.md", { type: "text/markdown" });
  Object.defineProperty(file, "arrayBuffer", { value: async () => new TextEncoder().encode(text).buffer });
  return file;
}
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("ACA judge simulation", () => {
  function simulatorClient() {
    const client = new TestClient();
    const health = { ready: true, model: "judge-simulator", message: "Example simulation only.", mode: "simulated" as const };
    client.health.mockResolvedValue(health);
    const value = result("result-simulation");
    value.origin = "simulated";
    value.modelReceipts = value.modelReceipts.map((receipt) => ({
      ...receipt, model: "judge-simulator", responseId: `sim_${receipt.role}`, origin: "simulated",
    }));
    client.analyze.mockResolvedValue(succeeded(value));
    return client;
  }

  it("runs Load Example then Generate without paid-model consent and labels the result honestly", async () => {
    const client = simulatorClient();
    render(<StudioApp client={client} />);
    await screen.findByText("JUDGE DEMO / SIMULATED AI");
    expect(screen.getByRole("note")).toHaveTextContent("AI calls are simulated for judging purposes to demonstrate the overall functionality without incurring model costs.");
    expect(screen.getByRole("note")).toHaveTextContent("No requests are sent to Foundry.");
    expect(screen.queryByRole("checkbox", { name: /I consent to send/ })).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "What should this system do?" })).toHaveAttribute("readonly");
    expect(screen.getByRole("button", { name: /Attach process documents/ })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /Load example inputs/ }));
    fireEvent.click(screen.getByRole("button", { name: "Generate architecture" }));
    expect(await screen.findByText("SIMULATED EXAMPLE", { exact: true })).toBeVisible();
    expect(screen.queryByText("LIVE MODEL RESULT")).not.toBeInTheDocument();
    expect(screen.getByText(/Simulated example returned/)).toBeVisible();
    expect(client.analyze).toHaveBeenCalledTimes(1);
    expect(client.analyze).toHaveBeenCalledWith(expect.objectContaining({ documents: expect.arrayContaining([
      expect.objectContaining({ id: "example-process" }),
    ]) }), expect.any(AbortSignal));
  });

  it("labels the assurance and change panels as scripted, not independent inference", async () => {
    render(<StudioApp client={simulatorClient()} />);
    await screen.findByText("JUDGE DEMO / SIMULATED AI");
    fireEvent.click(screen.getByRole("button", { name: /Load example inputs/ }));
    fireEvent.click(screen.getByRole("button", { name: "Generate architecture" }));
    await screen.findByText("SIMULATED EXAMPLE", { exact: true });
    fireEvent.click(screen.getByRole("tab", { name: /Assurance/ }));
    expect(screen.getByText("SCRIPTED REVIEW / 09 LENSES")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Review Business fit: info" }));
    fireEvent.click(screen.getByRole("button", { name: "Request recommended change" }));
    const dialog = within(screen.getByRole("dialog", { name: "Approve a design change" }));
    expect(dialog.getByRole("checkbox", { name: /scripted demonstration revision/ })).not.toBeChecked();
    expect(dialog.getByText(/Judge simulation: no model charges/)).toBeVisible();
    expect(dialog.queryByText(/Two model calls may incur charges/)).not.toBeInTheDocument();
  });

  it("rejects simulated output mislabeled with live receipt provenance", () => {
    const value = result();
    value.origin = "simulated";
    expect(() => validateJob(succeeded(value))).toThrow("invalid job response");
  });
});

describe("contextual design changes", () => {
  async function setup() {
    const client = new TestClient();
    client.analyze.mockResolvedValueOnce(succeeded(blockedResult()));
    render(<StudioApp client={client} />);
    await generate();
    fireEvent.click(screen.getByRole("tab", { name: /Assurance/ }));
    fireEvent.click(screen.getByRole("button", { name: "Review Security: blocker" }));
    return client;
  }
  function openChange() {
    fireEvent.click(screen.getByRole("button", { name: "Request recommended change" }));
    return within(screen.getByRole("dialog", { name: "Approve a design change" }));
  }
  function approve(dialog: ReturnType<typeof within>) {
    fireEvent.click(dialog.getByRole("checkbox", { name: /I approve this revision request/ }));
    fireEvent.click(dialog.getByRole("button", { name: "Approve & regenerate" }));
  }

  it("prefills the recommendation without inference and cancels without an approval", async () => {
    const client = await setup();
    const dialog = openChange();
    expect(dialog.getByRole("textbox", { name: "Design change instruction" })).toHaveValue(securityFinding().recommendation);
    expect(dialog.getByRole("button", { name: "Approve & regenerate" })).toBeDisabled();
    expect(dialog.getByText(/not a risk waiver/)).toBeVisible();
    expect(client.analyze).toHaveBeenCalledTimes(1);
    fireEvent.click(dialog.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(client.analyze).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Review Security: blocker" })).toBeVisible();
  });

  it("requires fresh consent after editing and sends the exact parent, alternative and finding", async () => {
    const client = await setup();
    fireEvent.click(screen.getByRole("button", { name: /Event-driven service/ }));
    const dialog = openChange();
    fireEvent.click(dialog.getByRole("checkbox", { name: /I approve this revision request/ }));
    const instruction = "Add a controlled callback adapter with signature verification; keep implementation as an explicit prerequisite.";
    fireEvent.change(dialog.getByRole("textbox", { name: "Design change instruction" }), { target: { value: instruction } });
    expect(dialog.getByRole("checkbox")).not.toBeChecked();
    expect(dialog.getByRole("button", { name: "Approve & regenerate" })).toBeDisabled();
    client.analyze.mockImplementationOnce(async (input) => approvedJob(input));
    approve(dialog);
    await screen.findByText("Latest AI review: warning");
    expect(client.analyze).toHaveBeenLastCalledWith(expect.objectContaining({
      previousResultId: "result-one", refinement: instruction, prompt: promptText,
      designChange: { optionId: "second", finding: securityFinding(), intent: "recommendation", confirmRevision: true },
    }), expect.any(AbortSignal));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Assurance/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("button", { name: /Event-driven service/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("textbox", { name: "Refine this architecture" })).toHaveValue(`Server-bound finding and option context.\n${instruction}`);
    expect(screen.getByRole("button", { name: "Review Security: warning" })).toBeVisible();
    expect(client.build).not.toHaveBeenCalled();
    client.build.mockImplementationOnce(async (input) => ({ ...packageResult(), resultId: input.resultId, optionId: input.optionId }));
    fireEvent.click(screen.getByRole("tab", { name: "Build" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /I confirm package generation only/ }));
    fireEvent.click(screen.getByRole("button", { name: "Generate deployment package" }));
    await waitFor(() => expect(client.build).toHaveBeenCalledWith(expect.objectContaining({ resultId: "result-two", optionId: "second" }), expect.any(AbortSignal)));
    expect(await screen.findByRole("button", { name: "Download compiled ZIP" })).toBeEnabled();
  });

  it("lets a user challenge with evidence but does not clear a remaining blocker", async () => {
    const client = await setup();
    fireEvent.click(screen.getByRole("button", { name: "Challenge finding" }));
    const dialog = within(screen.getByRole("dialog", { name: "Challenge this finding" }));
    expect(dialog.getByRole("textbox")).toHaveValue("");
    fireEvent.change(dialog.getByRole("textbox"), { target: { value: "The provider cannot use Entra; propose an adapter without weakening inbound authentication." } });
    client.analyze.mockImplementationOnce(async (input) => approvedJob(input, "blocker"));
    approve(dialog);
    expect(await screen.findByText("Blocker remains in revised design")).toBeVisible();
    expect(submittedChange(client).designChange?.intent).toBe("challenge");
    expect(screen.getByRole("button", { name: "Review Security: blocker" })).toBeVisible();
  });

  it.each(["prompt", "alternative"] as const)("rejects an open approval when the %s changes", async (changed) => {
    const client = await setup();
    const dialog = openChange();
    fireEvent.click(dialog.getByRole("checkbox"));
    if (changed === "prompt") enterPrompt("Changed business process with a different owner.");
    else fireEvent.click(screen.getByRole("button", { name: /Event-driven service/ }));
    expect(dialog.getByRole("button", { name: "Approve & regenerate" })).toBeDisabled();
    expect(dialog.getByRole("alert")).toHaveTextContent("working design or input changed");
    fireEvent.submit(dialog.getByRole("button", { name: "Approve & regenerate" }).closest("form")!);
    expect(client.analyze).toHaveBeenCalledTimes(1);
  });

  it("disables contextual actions for a stale result before opening any approval", async () => {
    const client = await setup();
    enterPrompt("Our process has changed; analyze these new requirements.");
    expect(screen.getByRole("button", { name: "Request recommended change" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Challenge finding" })).toBeDisabled();
    expect(client.analyze).toHaveBeenCalledTimes(1);
  });

  it("keeps failed revision approval and original blocker without a silent retry", async () => {
    const client = await setup();
    client.analyze.mockImplementationOnce(async (input) => ({
      ...approvedJob(input), status: "failed", result: null,
      error: { code: "model_failed", message: "Independent assurance failed", retryable: false },
    }));
    const dialog = openChange();
    approve(dialog);
    expect(await dialog.findByRole("alert")).toHaveTextContent("Independent assurance failed");
    expect(screen.getByText("Revision failed; original unchanged")).toBeVisible();
    expect(screen.getByRole("button", { name: "Review Security: blocker" })).toBeVisible();
    expect(dialog.getByRole("button", { name: "Approve & regenerate" })).toBeEnabled();
    expect(client.analyze).toHaveBeenCalledTimes(2);
    expect(client.build).not.toHaveBeenCalled();
  });

  it("rejects a missing or mismatched server approval instead of treating it as applied", async () => {
    const client = await setup();
    client.analyze.mockResolvedValueOnce(succeeded(result("result-wrong")));
    const dialog = openChange();
    approve(dialog);
    expect(await dialog.findByRole("alert")).toHaveTextContent("did not return an approval bound to this exact change");
    expect(screen.getByRole("button", { name: "Review Security: blocker" })).toBeVisible();
    expect(client.build).not.toHaveBeenCalled();
  });

  it("keeps the original blocker while pending, prevents duplicate submits, and preserves edits made during inference", async () => {
    const client = await setup();
    let resolveRevision!: (job: StudioJob) => void;
    client.analyze.mockImplementationOnce(() => new Promise((resolve) => { resolveRevision = resolve; }));
    const dialog = openChange();
    approve(dialog);
    expect(dialog.getByRole("button", { name: "Regenerating..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Review Security: blocker" })).toBeVisible();
    fireEvent.submit(dialog.getByRole("button", { name: "Regenerating..." }).closest("form")!);
    expect(client.analyze).toHaveBeenCalledTimes(2);
    enterPrompt("New unsent working input written while the prior revision is running.");
    const approved = approvedJob(submittedChange(client));
    await act(async () => { resolveRevision(approved); });
    expect(await screen.findByText("Latest AI review: warning")).toBeVisible();
    expect(screen.getByRole("textbox", { name: "What should this system do?" })).toHaveValue("New unsent working input written while the prior revision is running.");
    expect(screen.getByText("PREVIOUS RESULT · NOT CURRENT")).toBeVisible();
    expect(screen.getByRole("button", { name: "Request recommended change" })).toBeDisabled();
    expect(client.build).not.toHaveBeenCalled();
  });

  it("restores the decision and before/after review from history without a new call", async () => {
    const client = new TestClient();
    const saved = savedRun();
    saved.job = approvedJob({ ...saved.inputs, previousResultId: "result-one", refinement: "Add the controlled callback adapter.",
      idempotencyKey: "saved-test-approval", consentToModel: true,
      designChange: { optionId: "first", finding: securityFinding(), intent: "recommendation", confirmRevision: true } });
    saved.summary = { ...saved.summary, jobId: "job-two", resultId: "result-two", previousResultId: "result-one" };
    saved.inputs = { ...saved.inputs, previousResultId: "result-one", refinement: saved.job.changeApproval!.refinement };
    client.history.mockResolvedValue({ scope: "workspace", runs: [saved.summary] });
    client.historyRun.mockResolvedValue(saved);
    render(<StudioApp client={client} />);
    fireEvent.click(screen.getByRole("button", { name: "Run history" }));
    fireEvent.click(await screen.findByRole("button", { name: "Open this run" }));
    expect(await screen.findByText("SAVED MODEL RESULT")).toBeVisible();
    fireEvent.click(screen.getByText("View change & decision record"));
    expect(screen.getByText("Add the controlled callback adapter.")).toBeVisible();
    expect(screen.getByText("demo-human · local demo identity")).toBeVisible();
    expect(client.analyze).not.toHaveBeenCalled();
    expect(client.build).not.toHaveBeenCalled();
  });

  it("traps dialog focus and returns to the finding action on Escape", async () => {
    await setup();
    const user = userEvent.setup();
    const trigger = screen.getByRole("button", { name: "Request recommended change" });
    trigger.focus(); fireEvent.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Approve a design change" });
    expect(within(dialog).getByRole("button", { name: "Close design change" })).toHaveFocus();
    await user.tab({ shift: true });
    expect(within(dialog).getByRole("button", { name: "Cancel" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});

describe("live architecture studio", () => {
  it("offers only live workspace controls, without the retired draft-mode link", () => {
    render(<StudioApp client={new TestClient()} />);
    expect(screen.queryByRole("link", { name: /Draft mode/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run history" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Prompt" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Inspector" })).toBeVisible();
  });

  it("expands the canvas and restores the previous side-panel visibility without another model call", async () => {
    const client = new TestClient();
    const { container } = render(<StudioApp client={client} />);
    await generate();
    fireEvent.click(screen.getByRole("button", { name: "Prompt" }));
    fireEvent.click(screen.getByRole("button", { name: "Expand" }));
    expect(container.firstElementChild).toHaveClass("st-prompt-collapsed", "st-inspector-collapsed");
    fireEvent.click(screen.getByRole("button", { name: "Restore panels" }));
    expect(container.firstElementChild).toHaveClass("st-prompt-collapsed");
    expect(container.firstElementChild).not.toHaveClass("st-inspector-collapsed");
    expect(client.analyze).toHaveBeenCalledTimes(1);
    expect(client.build).not.toHaveBeenCalled();
  });

  it("opens earlier workspace runs without new inference and restores their inputs", async () => {
    const client = new TestClient();
    render(<StudioApp client={client} />);
    fireEvent.click(screen.getByRole("button", { name: "Run history" }));
    expect(await screen.findByText(/Shared local workspace/)).toBeVisible();
    const open = await screen.findByRole("button", { name: "Open this run" });
    fireEvent.click(open);
    expect(await screen.findByText("SAVED MODEL RESULT")).toBeVisible();
    expect(screen.getByRole("textbox", { name: "What should this system do?" })).toHaveValue(promptText);
    expect(screen.getByRole("checkbox", { name: /I consent to send/ })).not.toBeChecked();
    expect(client.analyze).not.toHaveBeenCalled();
    expect(client.build).not.toHaveBeenCalled();
  });

  it("confirms before replacing current input with a saved run and restores a saved package", async () => {
    const client = new TestClient();
    const saved = savedRun();
    saved.builds = [packageResult()];
    client.historyRun.mockResolvedValue(saved);
    render(<StudioApp client={client} />);
    enterPrompt("Keep these unsaved changes until I confirm");
    fireEvent.click(screen.getByRole("button", { name: "Run history" }));
    fireEvent.click(await screen.findByRole("button", { name: "Open this run" }));
    expect(screen.getByText("Replace the current working view?")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByRole("textbox", { name: "What should this system do?" })).toHaveValue("Keep these unsaved changes until I confirm");
    fireEvent.click(screen.getByRole("button", { name: "Open this run" }));
    fireEvent.click(screen.getByRole("button", { name: "Open saved run" }));
    await screen.findByText("Saved run and package restored. No new inference, compilation or deployment ran.");
    fireEvent.click(screen.getByRole("tab", { name: "Build" }));
    expect(screen.getByRole("button", { name: "Download compiled ZIP" })).toBeVisible();
    expect(client.historyBuild).toHaveBeenCalledWith("job-one", "build-one", expect.any(AbortSignal));
    expect(client.build).not.toHaveBeenCalled();
  });

  it("restores a failed refinement without pretending it succeeded or automatically retrying", async () => {
    const client = new TestClient();
    const saved = savedRun();
    saved.job = { jobId: "job-one", status: "failed", events: [], result: null,
      error: { code: "model-failed", message: "Recorded provider error", retryable: true } };
    saved.summary = { ...saved.summary, status: "failed", resultId: null, previousResultId: "result-parent", error: saved.job.error };
    saved.inputs = { ...saved.inputs, refinement: "Improve retry behavior", previousResultId: "result-parent" };
    client.history.mockResolvedValue({ scope: "workspace", runs: [saved.summary] });
    client.historyRun.mockResolvedValue(saved);
    render(<StudioApp client={client} />);
    fireEvent.click(screen.getByRole("button", { name: "Run history" }));
    fireEvent.click(await screen.findByRole("button", { name: "Open this run" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Saved run failed: Recorded provider error");
    expect(screen.queryByText("SAVED MODEL RESULT")).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Refine this architecture" })).toHaveValue("Improve retry behavior");
    expect(client.analyze).not.toHaveBeenCalled();
    consent();
    fireEvent.click(screen.getByRole("button", { name: "Refine architecture" }));
    await screen.findByText("LIVE MODEL RESULT");
    expect(client.analyze).toHaveBeenCalledWith(expect.objectContaining({
      previousResultId: "result-parent", refinement: "Improve retry behavior",
    }), expect.any(AbortSignal));
  });

  it("reconnects to a running saved job by polling, without submitting another model request", async () => {
    const client = new TestClient();
    const saved = savedRun();
    saved.job = pending("running");
    saved.summary = { ...saved.summary, status: "running", resultId: null };
    client.history.mockResolvedValue({ scope: "workspace", runs: [saved.summary] });
    client.historyRun.mockResolvedValue(saved);
    render(<StudioApp client={client} />);
    fireEvent.click(screen.getByRole("button", { name: "Run history" }));
    fireEvent.click(await screen.findByRole("button", { name: "Open this run" }));
    expect(await screen.findByText("LIVE MODEL RESULT", {}, { timeout: 4000 })).toBeVisible();
    expect(client.job).toHaveBeenCalledTimes(1);
    expect(client.analyze).not.toHaveBeenCalled();
  });

  it("downloads a historical run record without generating or compiling anything", async () => {
    const client = new TestClient();
    vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:history-test"), revokeObjectURL: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(<StudioApp client={client} />);
    fireEvent.click(screen.getByRole("button", { name: "Run history" }));
    fireEvent.click(await screen.findByRole("button", { name: "Download run record ZIP" }));
    await screen.findByText("Run record downloaded, including original input and document text.");
    expect(client.downloadRun).toHaveBeenCalledWith("job-one", expect.any(AbortSignal));
    expect(client.analyze).not.toHaveBeenCalled();
    expect(client.build).not.toHaveBeenCalled();
  });

  it("shows history failures explicitly and recovers through Refresh history", async () => {
    const client = new TestClient();
    client.history.mockRejectedValueOnce(new Error("Saved run storage is unavailable"));
    render(<StudioApp client={client} />);
    fireEvent.click(screen.getByRole("button", { name: "Run history" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Saved run storage is unavailable");
    expect(screen.queryByText(/No saved runs yet/)).not.toBeInTheDocument();
    client.history.mockResolvedValue({ scope: "workspace", runs: [] });
    fireEvent.click(screen.getByRole("button", { name: "Refresh history" }));
    expect(await screen.findByText(/No saved runs yet/)).toBeVisible();
  });

  it("keeps old character counters out of the customer activity timeline", async () => {
    const client = new TestClient();
    const job = succeeded();
    job.events = [
      { sequence: 1, stage: "synthesis", message: "Calling synthesis model", at: "2026-09-13T12:00:00Z" },
      { sequence: 2, stage: "synthesis", message: "Received 2,107 response characters from the live synthesis call.", at: "2026-09-13T12:00:01Z" },
      { sequence: 3, stage: "synthesis", message: "Received 4,201 response characters from the live synthesis call.", at: "2026-09-13T12:00:02Z" },
      { sequence: 4, stage: "complete", message: "Design ready for review", at: "2026-09-13T12:00:03Z" },
    ];
    client.analyze.mockResolvedValue(job);
    render(<StudioApp client={client} />);
    await generate();
    expect(document.querySelectorAll(".st-activity > ol > li")).toHaveLength(2);
    expect(screen.getByText("Technical stream diagnostics (2)")).toBeVisible();
    expect(screen.getByText(/Received 2,107 response characters/)).not.toBeVisible();
  });

  it("starts a new analysis when original sources change instead of sending an invalid refinement", async () => {
    const client = new TestClient();
    render(<StudioApp client={client} />);
    await generate();
    fireEvent.change(screen.getByRole("textbox", { name: "Refine this architecture" }), { target: { value: "Earlier instruction" } });
    enterPrompt("A different workshop booking process with distinct requirements.");
    expect(screen.queryByRole("textbox", { name: "Refine this architecture" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate architecture" }));
    await waitFor(() => expect(client.analyze).toHaveBeenCalledTimes(2));
    expect(client.analyze.mock.calls[1]?.[0]).toMatchObject({
      previousResultId: null, refinement: "", prompt: "A different workshop booking process with distinct requirements.",
    });
  });

  it("requires a refinement instruction before another chargeable call and discloses server persistence", async () => {
    const client = new TestClient();
    render(<StudioApp client={client} />);
    expect(screen.getByText(/stored unencrypted on this machine/)).toBeVisible();
    await generate();
    fireEvent.click(screen.getByRole("button", { name: "Refine architecture" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Describe the change");
    expect(client.analyze).toHaveBeenCalledTimes(1);
  });

  it("starts without a result or consent; example loading only seeds input", async () => {
    const client = new TestClient();
    render(<StudioApp client={client} />);
    expect(screen.getByRole("textbox", { name: "What should this system do?" })).toHaveValue("");
    expect(screen.getByRole("checkbox", { name: /I consent to send/ })).not.toBeChecked();
    expect(screen.getByText("Illustration only. No architecture has been generated.")).toBeVisible();
    await screen.findByText("Ready · configuration only");
    fireEvent.click(screen.getByRole("button", { name: /Load example inputs/ }));
    expect(client.analyze).not.toHaveBeenCalled();
    expect(screen.getByRole("checkbox", { name: /I consent to send/ })).not.toBeChecked();
    expect(screen.queryByText("LIVE MODEL RESULT")).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Preview attached/ })).toHaveLength(3);
  });

  it("requires consent and a meaningful prompt before any analysis request", async () => {
    const client = new TestClient();
    render(<StudioApp client={client} />);
    enterPrompt();
    fireEvent.click(screen.getByRole("button", { name: "Generate architecture" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Confirm consent");
    expect(client.analyze).not.toHaveBeenCalled();
    consent(); enterPrompt("short");
    fireEvent.click(screen.getByRole("button", { name: "Generate architecture" }));
    expect(screen.getByRole("alert")).toHaveTextContent("at least 10");
    expect(client.analyze).not.toHaveBeenCalled();
  });

  it("sends entered documents only on consented generation and opens exact source snapshots", async () => {
    const client = new TestClient();
    client.analyze.mockImplementation(async (input) => succeeded(result("result-one", "Support process", ["prompt", input.documents[0]!.id])));
    render(<StudioApp client={client} />);
    const user = userEvent.setup();
    await user.upload(screen.getByLabelText("Attach source documents"), uploadedFile());
    await screen.findByRole("button", { name: "Preview attached process.md" });
    expect(client.analyze).not.toHaveBeenCalled();
    await generate();
    expect(client.analyze).toHaveBeenCalledWith(expect.objectContaining({ prompt: promptText, documents: [expect.objectContaining({ name: "process.md", text: "Exact document: support owns the human handoff." })], consentToModel: true, previousResultId: null, idempotencyKey: expect.any(String) }), expect.any(AbortSignal));
    const node = screen.getByRole("button", { name: "Inspect Request API" });
    node.focus(); await user.keyboard("{Enter}");
    expect(screen.getByRole("heading", { name: "Request API" })).toBeVisible();
    expect(screen.getByText("Accept requests.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Open source process.md" }));
    const drawer = screen.getByRole("dialog");
    expect(within(drawer).getByText("Exact document: support owns the human handoff.")).toBeVisible();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open source Original prompt" }));
    expect(within(screen.getByRole("dialog")).getByText(promptText)).toBeVisible();
  });

  it("switches real topology with alternatives and highlights only supplied requirement links", async () => {
    const client = new TestClient();
    render(<StudioApp client={client} />);
    await generate();
    expect(screen.getByRole("button", { name: "Inspect Request API" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /Event-driven service/ }));
    expect(screen.queryByRole("button", { name: "Inspect Request API" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Inspect Queue worker" })).toBeVisible();
    fireEvent.click(screen.getByRole("tab", { name: "Sources" }));
    fireEvent.click(screen.getByRole("button", { name: "Highlight requirement r2: Retain status" }));
    expect(screen.getByRole("button", { name: "Inspect Queue worker" })).toHaveClass("is-muted");
    expect(screen.getByRole("button", { name: "Inspect Existing ERP" })).not.toHaveClass("is-muted");
    fireEvent.click(screen.getByRole("button", { name: "Clear requirement highlight" }));
    fireEvent.click(screen.getByRole("tab", { name: /Assurance/ }));
    const lenses = screen.getByRole("group", { name: "Nine assurance dimensions" });
    expect(within(lenses).getAllByRole("button")).toHaveLength(9);
    fireEvent.click(within(lenses).getByRole("button", { name: "Review Reliability: warning" }));
    expect(screen.getByText("reliability assessment")).toBeVisible();
    expect(screen.getByText(/no dimension-to-component links/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Inspect Queue worker" })).not.toHaveClass("is-muted");
  });

  it("runs a distinct actual job on refinement and presents requirement changes", async () => {
    const client = new TestClient();
    const changed = result("result-two", "Resilient support");
    changed.analysis.requirements[0]!.text = "Add recoverable request processing.";
    changed.analysis.requirements[0]!.sourceIds = ["refinement"];
    changed.sources.push({ id: "refinement", name: "Refinement instruction" });
    client.analyze.mockResolvedValueOnce(succeeded()).mockResolvedValueOnce(succeeded(changed));
    render(<StudioApp client={client} />);
    await generate();
    fireEvent.click(screen.getByRole("button", { name: /Make this more resilient/ }));
    expect(screen.getByText("PREVIOUS RESULT · NOT CURRENT")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Refine architecture" }));
    await screen.findByText("Resilient support");
    expect(client.analyze).toHaveBeenLastCalledWith(expect.objectContaining({ previousResultId: "result-one", refinement: "Make this more resilient", consentToModel: true }), expect.any(AbortSignal));
    fireEvent.click(screen.getByText("Architecture for Resilient support"));
    expect(screen.getByText("result-two changed requirements and service boundaries.")).toBeVisible();
    fireEvent.click(screen.getByRole("tab", { name: "Sources" }));
    expect(screen.getByText("Add recoverable request processing.")).toBeVisible();
    expect(screen.getByText("Changed")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Open source Refinement instruction" }));
    expect(within(screen.getByRole("dialog")).getByText("Make this more resilient")).toBeVisible();
    expect(within(screen.getByRole("dialog")).queryByText(promptText)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close source" }));
    fireEvent.click(screen.getByRole("button", { name: "Open source Original prompt" }));
    expect(within(screen.getByRole("dialog")).getByText(promptText)).toBeVisible();
    expect(within(screen.getByRole("dialog")).queryByText("Make this more resilient")).not.toBeInTheDocument();
  });

  it("polls actual queued/running/succeeded states and aborts pending polling on unmount", async () => {
    vi.useFakeTimers();
    const client = new TestClient();
    client.analyze.mockResolvedValue(pending("queued"));
    client.job.mockResolvedValueOnce(pending("running")).mockResolvedValueOnce(succeeded());
    const view = render(<StudioApp client={client} />);
    enterPrompt(); consent();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Generate architecture" })); });
    expect(screen.getByText("Request queued")).toBeVisible();
    await act(async () => { await vi.advanceTimersByTimeAsync(1200); });
    expect(screen.getByText("Calling synthesis model")).toBeVisible();
    await act(async () => { await vi.advanceTimersByTimeAsync(1200); });
    expect(screen.getByText("LIVE MODEL RESULT")).toBeVisible();
    expect(client.job).toHaveBeenCalledTimes(2);
    view.unmount();
    const secondClient = new TestClient();
    secondClient.analyze.mockResolvedValue(pending("queued"));
    const second = render(<StudioApp client={secondClient} />);
    enterPrompt(); consent();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Generate architecture" })); });
    const signal = secondClient.analyze.mock.calls[0]![1]!;
    second.unmount();
    expect(signal.aborted).toBe(true);
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(secondClient.job).not.toHaveBeenCalled();
  });

  it("shows polling failures without replacing the previous result or freezing editing", async () => {
    const client = new TestClient();
    render(<StudioApp client={client} />);
    await generate();
    client.analyze.mockResolvedValue({ jobId: "job-two", status: "failed", events: [{ sequence: 1, stage: "error", message: "Model connection failed", at: "2026-09-13T12:00:00Z" }], result: null, error: { code: "model-unavailable", message: "Foundry request failed", retryable: true } });
    fireEvent.change(screen.getByRole("textbox", { name: "Refine this architecture" }), { target: { value: "Separate the worker." } });
    fireEvent.click(screen.getByRole("button", { name: "Refine architecture" }));
    await screen.findByRole("alert");
    expect(screen.getByRole("alert")).toHaveTextContent("Foundry request failed");
    expect(screen.getByText("PREVIOUS RESULT · NOT CURRENT")).toBeVisible();
    expect(screen.getByRole("button", { name: "Inspect Request API" })).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Refine this architecture" })).toHaveValue("Separate the worker.");
    expect(screen.getByRole("button", { name: "Refine architecture" })).toBeEnabled();
    enterPrompt("Updated intent after the failed model request.");
    expect(screen.getByRole("textbox", { name: "What should this system do?" })).toHaveValue("Updated intent after the failed model request.");
    client.analyze.mockResolvedValue(succeeded(result("recovered", "Recovered process")));
    fireEvent.click(screen.getByRole("button", { name: "Generate architecture" }));
    await screen.findByText("Recovered process");
    expect(screen.getByText("LIVE MODEL RESULT")).toBeVisible();
  });

  it("surfaces a rejected polling request and stops observing without claiming server cancellation", async () => {
    vi.useFakeTimers();
    const client = new TestClient();
    client.analyze.mockResolvedValue(pending("queued"));
    client.job.mockRejectedValueOnce(new Error("Job polling connection dropped."));
    render(<StudioApp client={client} />);
    enterPrompt(); consent();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Generate architecture" })); });
    await act(async () => { await vi.advanceTimersByTimeAsync(1200); });
    expect(screen.getByRole("alert")).toHaveTextContent("Job polling connection dropped.");
    expect(screen.getByRole("button", { name: "Generate architecture" })).toBeEnabled();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Generate architecture" })); });
    const signal = client.analyze.mock.calls[1]![1]!;
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Stop waiting" })); });
    expect(signal.aborted).toBe(true);
    expect(screen.getByText("Stopped waiting locally. This does not cancel the server job.")).toBeVisible();
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(client.job).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Generate architecture" })).toBeEnabled();
  });

  it("handles different prompts as distinct returned scenarios, not a fixed sample architecture", async () => {
    const client = new TestClient();
    render(<StudioApp client={client} />);
    await generate();
    const second = result("clinical-result", "Clinic scheduling");
    second.analysis.options[0]!.components[0]!.label = "Appointment API";
    client.analyze.mockResolvedValue(succeeded(second));
    enterPrompt("Schedule clinic visits with patient reminders and staff approval.");
    fireEvent.click(screen.getByRole("button", { name: "Generate architecture" }));
    await screen.findByText("Clinic scheduling");
    expect(screen.getByRole("button", { name: "Inspect Appointment API" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Inspect Request API" })).not.toBeInTheDocument();
    expect(client.analyze).toHaveBeenLastCalledWith(expect.objectContaining({ prompt: "Schedule clinic visits with patient reminders and staff approval." }), expect.any(AbortSignal));
  });

  it("rejects malformed success fields rather than drawing an incomplete result", async () => {
    const client = new TestClient();
    const malformed: unknown = { ...succeeded(), result: { resultId: "bad", analysis: { summary: "Incomplete" } } };
    client.analyze.mockResolvedValue(malformed as StudioJob);
    render(<StudioApp client={client} />);
    enterPrompt(); consent(); fireEvent.click(screen.getByRole("button", { name: "Generate architecture" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("invalid job response");
    expect(screen.queryByText("LIVE MODEL RESULT")).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "What should this system do?" })).toHaveValue(promptText);
    expect(screen.getByRole("button", { name: "Generate architecture" })).toBeEnabled();
  });

  it("requires explicit generation confirmation, reports actual compilation and downloads the returned blob", async () => {
    const client = new TestClient();
    const createObjectURL = vi.fn(() => "blob:test-compiled-package");
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL: vi.fn() }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    render(<StudioApp client={client} />);
    await generate();
    fireEvent.click(screen.getByRole("tab", { name: "Build" }));
    const buildButton = screen.getByRole("button", { name: "Generate deployment package" });
    expect(buildButton).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: /I confirm package generation only/ }));
    fireEvent.click(buildButton);
    await screen.findByText("COMPILED", { exact: true });
    expect(client.build).toHaveBeenCalledWith(expect.objectContaining({ resultId: "result-one", optionId: "first", confirmGeneration: true }), expect.any(AbortSignal));
    expect(screen.getByText("Bicep CLI 0.41.2")).toBeVisible();
    expect(screen.getByText("Not deployed", { exact: true })).toBeVisible();
    expect(screen.getByLabelText("Preview main.bicep")).toHaveTextContent("targetScope");
    fireEvent.click(screen.getByRole("button", { name: "Download compiled ZIP" }));
    await waitFor(() => expect(client.download).toHaveBeenCalledTimes(1));
    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(click).toHaveBeenCalledTimes(1);
    expect(await screen.findByText(/Compiled ZIP handed to your browser/)).toBeVisible();
  });

  it("disables stale builds and treats a different alternative's package as irrelevant", async () => {
    const client = new TestClient();
    render(<StudioApp client={client} />);
    await generate();
    fireEvent.click(screen.getByRole("tab", { name: "Build" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /I confirm package generation only/ }));
    enterPrompt("This edited system has entirely different requirements.");
    expect(screen.getByRole("button", { name: "Generate deployment package" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Generate deployment package" }));
    expect(client.build).not.toHaveBeenCalled();
    enterPrompt();
    fireEvent.click(screen.getByRole("button", { name: "Generate deployment package" }));
    await screen.findByRole("button", { name: "Download compiled ZIP" });
    fireEvent.click(screen.getByRole("button", { name: /Event-driven service/ }));
    expect(screen.queryByRole("button", { name: "Download compiled ZIP" })).not.toBeInTheDocument();
    expect(screen.getByText(/Previous package belongs to another/)).toBeVisible();
    expect(screen.getByRole("checkbox", { name: /I confirm package generation only/ })).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Generate deployment package" })).toBeDisabled();
  });

  it.each(["failed", "blocked"] as const)("shows %s compilation diagnostics without a ZIP success action", async (status) => {
    const client = new TestClient();
    client.build.mockResolvedValue(packageResult(status));
    render(<StudioApp client={client} />);
    await generate();
    fireEvent.click(screen.getByRole("tab", { name: "Build" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /I confirm package generation only/ }));
    fireEvent.click(screen.getByRole("button", { name: "Generate deployment package" }));
    expect(await screen.findByText(status.toUpperCase(), { exact: true })).toBeVisible();
    expect(screen.getByRole("alert")).toHaveTextContent("Compiler rejected unsupported configuration.");
    expect(screen.queryByRole("button", { name: "Download compiled ZIP" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Regenerate deployment package" })).toBeEnabled();
    expect(screen.getByRole("textbox", { name: "What should this system do?" })).toBeEnabled();
  });

  it("keeps a recoverable error on service or download failures and never loads examples automatically", async () => {
    const client = new TestClient();
    client.analyze.mockRejectedValueOnce(new Error("Service is offline"));
    render(<StudioApp client={client} />);
    enterPrompt(); consent(); fireEvent.click(screen.getByRole("button", { name: "Generate architecture" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Service is offline");
    expect(screen.queryByRole("button", { name: "Inspect Request API" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate architecture" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Generate architecture" }));
    await screen.findByText("LIVE MODEL RESULT");
    fireEvent.click(screen.getByRole("tab", { name: "Build" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /I confirm package generation only/ }));
    fireEvent.click(screen.getByRole("button", { name: "Generate deployment package" }));
    await screen.findByRole("button", { name: "Download compiled ZIP" });
    client.download.mockRejectedValue(new Error("Archive could not be retrieved."));
    fireEvent.click(screen.getByRole("button", { name: "Download compiled ZIP" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Archive could not be retrieved.");
    expect(screen.getByRole("button", { name: "Download compiled ZIP" })).toBeEnabled();
  });
});
