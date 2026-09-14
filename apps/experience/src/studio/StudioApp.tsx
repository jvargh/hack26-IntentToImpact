import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { EXAMPLE_DOCUMENTS, EXAMPLE_PROMPT } from "../business/model";
import { readDocument } from "../business/draft";
import { StudioClient, validateBuild, validateJob } from "./client";
import type { AnalysisRequest, ArchitectureOption, BuildResult, Requirement, ReviewFinding, SourceDocument, StudioJob, StudioResult, SavedRun } from "./contracts";
import { ArchitectureCanvas } from "./views/ArchitectureCanvas";
import { Inspector } from "./views/Inspector";
import type { InspectorTab } from "./views/Inspector";
import { SourceDrawer } from "./views/SourceDrawer";
import { RunHistoryPanel } from "./views/RunHistoryPanel";
import { DesignChangeDrawer, DesignChangeOutcome } from "./views/DesignChange";
import type { ChangeIntent } from "./views/DesignChange";
import "./studio.css";

type Inputs = Pick<AnalysisRequest, "title" | "prompt" | "documents" | "refinement">;
const blankInputs: Inputs = { title: "", prompt: "", documents: [], refinement: "" };
const inputIdentity = (inputs: Inputs) => JSON.stringify(inputs);
const sourceIdentity = (inputs: Inputs) => JSON.stringify([inputs.prompt, inputs.documents]);
const findingIdentity = (finding: ReviewFinding) => JSON.stringify([finding.dimension, finding.severity, finding.finding, finding.recommendation, finding.sourceIds]);
type ChangeDraft = { resultId: string; option: ArchitectureOption; finding: ReviewFinding; intent: ChangeIntent; inputIdentity: string };
function message(error: unknown) { return error instanceof Error ? error.message : "The service did not complete the request. Your input is preserved; please retry."; }
function waitForPoll(signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const abort = () => { clearTimeout(timer); reject(new DOMException("Stopped observing the job.", "AbortError")); };
    const timer = setTimeout(() => { signal.removeEventListener("abort", abort); resolve(); }, 1200);
    signal.addEventListener("abort", abort, { once: true });
    if (signal.aborted) abort();
  });
}

export function StudioApp({ client: suppliedClient }: { client?: Pick<StudioClient, "health" | "analyze" | "job" | "build" | "download" | "history" | "historyRun" | "historyBuild" | "downloadRun"> }) {
  const [client] = useState(() => suppliedClient ?? new StudioClient());
  const [inputs, setInputs] = useState<Inputs>(blankInputs);
  const [consent, setConsent] = useState(false);
  const [reading, setReading] = useState(false);
  const [health, setHealth] = useState<{ ready: boolean; model: string; message: string } | null>(null);
  const [healthError, setHealthError] = useState("");
  const [healthAttempt, setHealthAttempt] = useState(0);
  const [busy, setBusy] = useState<"analysis" | "build" | "download" | null>(null);
  const [job, setJob] = useState<StudioJob | null>(null);
  const [result, setResult] = useState<StudioResult | null>(null);
  const [snapshot, setSnapshot] = useState<Inputs | null>(null);
  const [previousRequirements, setPreviousRequirements] = useState<Requirement[] | null>(null);
  const [failedAttempt, setFailedAttempt] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [optionId, setOptionId] = useState<string | null>(null);
  const [componentId, setComponentId] = useState<string | null>(null);
  const [requirementId, setRequirementId] = useState<string | null>(null);
  const [lens, setLens] = useState<ReviewFinding["dimension"] | null>(null);
  const [tab, setTab] = useState<InspectorTab>("component");
  const [build, setBuild] = useState<BuildResult | null>(null);
  const [source, setSource] = useState<SourceDocument | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [restoredRunId, setRestoredRunId] = useState<string | null>(null);
  const [restoredParentId, setRestoredParentId] = useState<string | null>(null);
  const [promptVisible, setPromptVisible] = useState(true);
  const [inspectorVisible, setInspectorVisible] = useState(true);
  const panelsBeforeExpand = useRef({ prompt: true, inspector: true });
  const [changeDraft, setChangeDraft] = useState<ChangeDraft | null>(null);
  const [changeError, setChangeError] = useState("");
  const controllers = useRef(new Set<AbortController>());
  const downloadUrls = useRef(new Map<string, ReturnType<typeof setTimeout>>());
  const alive = useRef(true);
  const fileInput = useRef<HTMLInputElement>(null);
  const operation = useRef<AbortController | null>(null);
  const option = result?.analysis.options.find((item) => item.id === optionId) ?? result?.analysis.options[0] ?? null;
  const component = option?.components.find((item) => item.id === componentId) ?? null;
  const stale = !!result && (failedAttempt || busy === "analysis" || !snapshot || inputIdentity(snapshot) !== inputIdentity(inputs));
  const canRefine = !!result && !!snapshot && sourceIdentity(snapshot) === sourceIdentity(inputs);
  const changeCurrent = !!changeDraft && !stale && changeDraft.resultId === result?.resultId
    && changeDraft.option.id === option?.id && changeDraft.inputIdentity === inputIdentity(inputs);
  const refinementParentId = canRefine ? result!.resultId
    : restoredParentId && snapshot && sourceIdentity(snapshot) === sourceIdentity(inputs) ? restoredParentId : null;
  const status = busy === "analysis" ? "Generating" : busy === "build" ? "Compiling" : failedAttempt || job?.status === "failed" ? "Failed" : !health && !healthError ? "Connecting" : health?.ready ? "Ready" : "Unavailable";
  const technicalEvents = job?.events.filter((event) => /^Received [\d,]+ response characters\b/.test(event.message)) ?? [];
  const activityEvents = job?.events.filter((event) => !technicalEvents.includes(event)) ?? [];

  useEffect(() => {
    alive.current = true;
    const activeControllers = controllers.current;
    const activeUrls = downloadUrls.current;
    return () => {
      alive.current = false;
      activeControllers.forEach((controller) => controller.abort()); activeControllers.clear();
      activeUrls.forEach((timer, url) => { clearTimeout(timer); URL.revokeObjectURL(url); }); activeUrls.clear();
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    controllers.current.add(controller);
    setHealthError("");
    client.health(controller.signal).then((value) => { if (!controller.signal.aborted) setHealth(value); })
      .catch((failure: unknown) => { if (!controller.signal.aborted) setHealthError(message(failure)); })
      .finally(() => controllers.current.delete(controller));
    return () => controller.abort();
  }, [client, healthAttempt]);

  function begin(kind: "analysis" | "build" | "download") {
    const controller = new AbortController();
    controllers.current.add(controller); operation.current = controller;
    setBusy(kind); setError(""); setNotice("");
    return controller;
  }
  function finish(controller: AbortController) {
    controllers.current.delete(controller);
    if (operation.current === controller) { operation.current = null; if (alive.current) setBusy(null); }
  }
  function patchInput(patch: Partial<Inputs>) {
    if (patch.prompt !== undefined || patch.documents !== undefined) setRestoredParentId(null);
    setInputs((current) => ({ ...current, ...patch,
      ...(patch.prompt !== undefined || patch.documents !== undefined ? { refinement: "" } : {}),
    }));
    setNotice("");
  }

  async function observeJob(next: StudioJob, submitted: Inputs, controller: AbortController, priorRequirements: Requirement[] | null) {
    while (!controller.signal.aborted) {
      setJob(next);
      if (next.status === "failed") throw new Error(`${next.error?.code ?? "analysis-failed"}: ${next.error?.message ?? "Analysis failed without diagnostics."}`);
      if (next.status === "succeeded" && next.result) {
        setPreviousRequirements(priorRequirements);
        setResult(next.result); setSnapshot(submitted); setFailedAttempt(false);
        setRestoredRunId(null); setRestoredParentId(null);
        const target = next.changeApproval?.optionId;
        setOptionId(target && next.result.analysis.options.some((item) => item.id === target) ? target : next.result.analysis.recommendedOptionId);
        setComponentId(null); setRequirementId(null); setLens(next.changeApproval?.finding.dimension ?? null);
        if (next.changeApproval) { setTab("assurance"); setInspectorVisible(true); }
        setNotice("Architecture returned by the live model. Review the sources, assumptions and assurance findings.");
        return next.result;
      }
      await waitForPoll(controller.signal);
      next = validateJob(await client.job(next.jobId, controller.signal));
    }
  }

  async function analyze(event: FormEvent) {
    event.preventDefault();
    if (busy || reading) return;
    if (!consent) { setError("Confirm consent before sending your prompt and documents to Microsoft Foundry."); return; }
    if (inputs.prompt.trim().length < 10) { setError("Describe your process in at least 10 characters."); return; }
    if (refinementParentId && !inputs.refinement.trim()) { setError("Describe the change you want, or edit the original prompt to start a new analysis."); return; }
    const submitted = { ...inputs, documents: inputs.documents.map((document) => ({ ...document })) };
    const previousResultId = refinementParentId;
    const controller = begin("analysis");
    setJob(null);
    try {
      const next = validateJob(await client.analyze({ ...submitted, previousResultId, idempotencyKey: crypto.randomUUID(), consentToModel: true }, controller.signal));
      await observeJob(next, submitted, controller, previousResultId ? result?.analysis.requirements ?? null : null);
    } catch (failure) {
      if (!controller.signal.aborted) { setError(message(failure)); setFailedAttempt(true); }
    } finally { finish(controller); }
  }

  function requestDesignChange(finding: ReviewFinding, intent: ChangeIntent) {
    if (!result || !option || stale || busy || reading) {
      setError("Open the current, unchanged result before requesting a design change.");
      return;
    }
    setChangeError("");
    setChangeDraft({ resultId: result.resultId, option, finding, intent, inputIdentity: inputIdentity(inputs) });
  }

  async function approveDesignChange(instruction: string) {
    if (operation.current || reading) return;
    if (!changeDraft || !changeCurrent || !result || instruction.trim().length < 10 || instruction.length > 2000) {
      setChangeError("The design or instruction is no longer valid. Reopen the finding on the current result.");
      return;
    }
    const draft = changeDraft;
    const submitted: Inputs = { ...inputs, refinement: instruction, documents: inputs.documents.map((document) => ({ ...document })) };
    const controller = begin("analysis");
    setChangeError(""); setJob(null);
    try {
      const next = validateJob(await client.analyze({
        ...submitted, previousResultId: draft.resultId, idempotencyKey: crypto.randomUUID(), consentToModel: true,
        designChange: { optionId: draft.option.id, finding: draft.finding, intent: draft.intent, confirmRevision: true },
      }, controller.signal));
      if (controller.signal.aborted) return;
      const approval = next.changeApproval;
      if (!approval || approval.baseResultId !== draft.resultId || approval.optionId !== draft.option.id
        || approval.intent !== draft.intent || approval.instruction !== instruction
        || findingIdentity(approval.finding) !== findingIdentity(draft.finding)) {
        throw new Error("The service did not return an approval bound to this exact change. Check Run history before resubmitting; no blocker has been waived.");
      }
      submitted.refinement = approval.refinement;
      const revised = await observeJob(next, submitted, controller, result.analysis.requirements);
      if (revised && !controller.signal.aborted) {
        setInputs((current) => inputIdentity(current) === draft.inputIdentity ? submitted : current);
        setBuild(null); setChangeDraft(null);
        setNotice("Revised proposal and independent assurance are ready. Review what changed before generating its infrastructure package. Approval did not waive any blocker.");
      }
    } catch (failure) {
      if (!controller.signal.aborted) {
        const detail = `${message(failure)} The original design is unchanged; no blocker was waived.`;
        setError(detail); setChangeError(detail);
      }
    } finally { finish(controller); }
  }

  async function openSavedRun(saved: SavedRun) {
    if (busy || reading) return;
    setHistoryOpen(false);
    const savedInputs: Inputs = {
      title: saved.inputs.title, prompt: saved.inputs.prompt,
      documents: saved.inputs.documents.map((document) => ({ ...document })), refinement: saved.inputs.refinement,
    };
    setInputs(savedInputs); setSnapshot(savedInputs); setJob(saved.job); setResult(saved.job.result);
    setConsent(false); setBuild(null); setSource(null); setPreviousRequirements(null); setChangeDraft(null); setChangeError("");
    setRestoredRunId(saved.summary.jobId);
    setRestoredParentId(saved.job.result ? null : saved.inputs.previousResultId);
    setFailedAttempt(saved.job.status === "failed");
    setOptionId(saved.job.result?.analysis.recommendedOptionId ?? null);
    setComponentId(null); setRequirementId(null); setLens(saved.job.changeApproval?.finding.dimension ?? null);
    if (saved.job.changeApproval) { setTab("assurance"); setInspectorVisible(true); }
    setError(saved.job.error ? `Saved run failed: ${saved.job.error.message}` : "");
    setNotice("Opened a saved run. No new model request or deployment was made. Consent is required before sending another request.");
    if (saved.job.status === "running" || saved.job.status === "queued") {
      const controller = begin("analysis");
      try { await observeJob(saved.job, savedInputs, controller, null); }
      catch (failure) { if (!controller.signal.aborted) { setError(message(failure)); setFailedAttempt(true); } }
      finally { finish(controller); }
    } else if (saved.job.result) {
      const previousBuild = [...saved.builds].reverse().find((item) => item.optionId === saved.job.result!.analysis.recommendedOptionId);
      if (previousBuild) {
        const controller = begin("download");
        try {
          const restored = await client.historyBuild(saved.summary.jobId, previousBuild.buildId, controller.signal);
          if (!controller.signal.aborted) {
            setBuild(restored);
            setNotice("Saved run and package restored. No new inference, compilation or deployment ran.");
          }
        } catch (failure) { if (!controller.signal.aborted) setError(message(failure)); }
        finally { finish(controller); }
      }
    }
  }

  async function attach(files: FileList | null) {
    if (!files?.length || reading) return;
    if (inputs.documents.length + files.length > 5) { setError("Attach up to 5 TXT or Markdown documents."); return; }
    setReading(true); setError("");
    try {
      const documents = await Promise.all(Array.from(files, async (file) => {
        const parsed = await readDocument(file);
        return { id: parsed.id, name: parsed.name, text: parsed.text };
      }));
      if (!alive.current) return;
      const combined = [...inputs.documents, ...documents];
      if (new Set(combined.map((document) => document.name.toLowerCase())).size !== combined.length) throw new Error("A document with that name is already attached. Remove it before adding a replacement.");
      if (combined.reduce((sum, document) => sum + document.text.length, 0) > 150000) throw new Error("Keep combined document text within 150,000 characters.");
      patchInput({ documents: combined });
      setNotice("Files read locally. Nothing is sent until you consent and generate.");
    } catch (failure) { if (alive.current) setError(message(failure)); }
    finally { if (alive.current) setReading(false); if (fileInput.current) fileInput.current.value = ""; }
  }

  async function generateBuild() {
    if (!result || !option || stale || busy) return;
    const controller = begin("build");
    setBuild(null);
    try {
      const output = validateBuild(await client.build({ resultId: result.resultId, optionId: option.id, confirmGeneration: true, idempotencyKey: crypto.randomUUID() }, controller.signal));
      if (!controller.signal.aborted) {
        setBuild(output);
        if (output.status !== "compiled") setError(`Package ${output.status}. ${output.diagnostics || "The server supplied no compiler diagnostics."}`);
      }
    } catch (failure) { if (!controller.signal.aborted) setError(message(failure)); }
    finally { finish(controller); }
  }

  async function download() {
    if (!build || build.status !== "compiled" || build.resultId !== result?.resultId || build.optionId !== option?.id || stale || busy) return;
    const controller = begin("download");
    try {
      const blob = await client.download(build, controller.signal);
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = `${build.buildId}.zip`;
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      downloadUrls.current.set(url, setTimeout(() => { URL.revokeObjectURL(url); downloadUrls.current.delete(url); }, 1000));
      setNotice("Compiled ZIP handed to your browser for download. No Azure resources were deployed.");
    } catch (failure) { if (!controller.signal.aborted) setError(message(failure)); }
    finally { finish(controller); }
  }

  function openSource(id: string) {
    const found = id === "prompt" && snapshot
      ? { id, name: "Original prompt", text: snapshot.prompt }
      : id === "refinement" && snapshot?.refinement
        ? { id, name: "Refinement instruction", text: snapshot.refinement }
        : snapshot?.documents.find((document) => document.id === id);
    if (found) setSource(found);
    else setError(`Source "${id}" is unavailable in the submitted local snapshot. No source text has been invented.`);
  }

  return <div className={`st-app ${!promptVisible ? "st-prompt-collapsed" : ""} ${!inspectorVisible ? "st-inspector-collapsed" : ""}`}>
    <a className="st-skip-link" href="#st-workspace">Skip to architecture canvas</a>
    <header className="st-header"><a href="/" className="st-brand" aria-label="Intent to Impact Studio home"><span className="st-brand-mark" aria-hidden="true">⌘</span><span>intent<span className="st-brand-divider">/</span>impact<small>ARCHITECTURE STUDIO</small></span></a>
      <div className="st-header-center"><span className="st-header-line" /><span>DESIGN SYSTEMS. NOT SLIDES.</span></div>
      <div className="st-runtime"><span className={`st-status-dot ${busy ? "is-busy" : status === "Ready" ? "is-ready" : ""}`} /><div><span>Foundry · {health?.model || "model metadata unavailable"}</span><small>{status}{health?.ready && !result && !busy ? " · configuration only" : ""}</small></div></div>
    </header>
    <div className="st-workspace-bar"><div><span className="st-overline">WORKSPACE</span><strong>{result?.analysis.title || inputs.title || "Untitled architecture"}</strong></div><div className="st-workspace-tools"><span className="st-memory-note">Inputs in tab · submitted runs stored locally</span><button type="button" onClick={() => setHistoryOpen(true)}>Run history</button><button type="button" aria-expanded={promptVisible} onClick={() => setPromptVisible((value) => !value)}>Prompt</button><button type="button" aria-expanded={inspectorVisible} onClick={() => setInspectorVisible((value) => !value)}>Inspector</button></div></div>
    <main className="st-layout">
      <aside className="st-prompt-console" aria-label="Prompt console">
        <div className="st-panel-title"><span className="st-overline">01 / DEFINE YOUR INTENT</span><span className="st-live-word">INPUT</span></div>
        <form onSubmit={(event) => { void analyze(event); }}>
          <label className="st-label" htmlFor="st-title">Project name <span>optional</span></label><input id="st-title" maxLength={160} value={inputs.title} onChange={(event) => patchInput({ title: event.target.value })} placeholder="Name your next system" />
          <div className="st-label-row"><label className="st-label" htmlFor="st-prompt">What should this system do?</label><span>{inputs.prompt.length.toLocaleString()}/12k</span></div>
          <textarea id="st-prompt" maxLength={12000} value={inputs.prompt} onChange={(event) => patchInput({ prompt: event.target.value })} placeholder="Describe the process, the people, and what has to change. Include constraints, existing systems, and the outcome you need." rows={7} />
          <button type="button" className="st-text-button" disabled={!!busy || reading} onClick={() => { setInputs({ title: "Order fulfilment", prompt: EXAMPLE_PROMPT, refinement: "", documents: EXAMPLE_DOCUMENTS.map(({ id, name, text }) => ({ id, name, text })) }); setRestoredParentId(null); setConsent(false); setNotice("Example inputs loaded only. Consent and generate to request a real model result."); }}>Load example inputs <span aria-hidden="true">↗</span></button>
          <div className="st-label-row"><span className="st-label">Source documents</span><span>{inputs.documents.length}/5</span></div>
          <input ref={fileInput} className="st-file-input" id="st-documents" type="file" accept=".txt,.md,.markdown" multiple aria-label="Attach source documents" disabled={reading || !!busy} onChange={(event) => { void attach(event.target.files); }} />
          <button type="button" className="st-attach" onClick={() => fileInput.current?.click()} disabled={reading || !!busy}><span aria-hidden="true">+</span><span>{reading ? "Reading locally…" : "Attach process documents"}<small>TXT / Markdown · max 1 MB each</small></span></button>
          {inputs.documents.length > 0 && <ul className="st-attached">{inputs.documents.map((document) => <li key={document.id}><button type="button" onClick={() => setSource(document)} aria-label={`Preview attached ${document.name}`}><span aria-hidden="true">⌑</span><span>{document.name}</span></button><button type="button" aria-label={`Remove ${document.name}`} disabled={!!busy || reading} onClick={() => patchInput({ documents: inputs.documents.filter((item) => item.id !== document.id) })}>×</button></li>)}</ul>}
          <p className="st-input-note">Local until Generate. Submitted input and results are stored unencrypted on this machine. Do not include secrets or sensitive documents. Model calls incur charges.</p>
          {refinementParentId && <div className="st-refinement"><label className="st-label" htmlFor="st-refinement">Refine this architecture</label><textarea id="st-refinement" rows={3} maxLength={4000} value={inputs.refinement} onChange={(event) => patchInput({ refinement: event.target.value })} placeholder="What should change, and why?" /><button type="button" className="st-refine-chip" disabled={!!busy} onClick={() => patchInput({ refinement: "Make this more resilient" })}>↻ Make this more resilient</button><small>A new real model job, not a local diagram edit.</small></div>}
          <label className="st-check"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />I consent to send this prompt and attached text to the configured Microsoft Foundry model through this server.</label>
          <button className={`${!result || stale ? "st-primary" : "st-secondary"} st-wide`} type="submit" disabled={!!busy || reading}>{busy === "analysis" ? "Generating architecture…" : refinementParentId ? "Refine architecture" : "Generate architecture"}<span aria-hidden="true">{busy === "analysis" ? "◌" : "↗"}</span></button>
        </form>
        {(!health?.ready || healthError) && <div className="st-health-message"><span className="st-overline">{healthError ? "CONNECTION ERROR" : health ? "MODEL NOT READY" : "CONNECTING TO SERVER"}</span><p>{healthError || health?.message || "Checking model configuration. This does not run inference."}</p><button type="button" onClick={() => { setHealth(null); setHealthAttempt((value) => value + 1); }}>Check connection</button></div>}
        <section className="st-activity" aria-label="Live activity"><div className="st-panel-title"><span className="st-overline">ACTIVITY / SERVER EVENTS</span><span>{job?.status ?? "idle"}</span></div>
          {activityEvents.length ? <ol>{activityEvents.map((event) => <li key={event.sequence}><span className={`st-event-dot st-event-${event.stage}`} /><div><strong>{event.stage}</strong><p>{event.message}</p><time dateTime={event.at}>{new Date(event.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</time></div></li>)}</ol> : <p className="st-muted">{busy === "analysis" ? "Request submitted. Waiting for server events…" : failedAttempt ? "No server events received. The request failed or local observation stopped." : "Waiting for your first request. No model inference has run in this workspace."}</p>}
          {technicalEvents.length > 0 && <details className="st-details"><summary>Technical stream diagnostics ({technicalEvents.length})</summary><p>Transport counters from this older run, not separate model calls or retries.</p><ul>{technicalEvents.map((event) => <li key={event.sequence}>{event.message}</li>)}</ul></details>}
          {busy === "analysis" && <button type="button" className="st-text-button" onClick={() => { operation.current?.abort(); setFailedAttempt(true); setNotice("Stopped waiting locally. This does not cancel the server job."); }}>Stop waiting</button>}
        </section>
      </aside>
      <section className="st-workspace" id="st-workspace" aria-label="Architecture workspace" tabIndex={-1}>
        <div className="st-stage-header"><div><span className="st-overline">02 / EXPLORE THE SYSTEM</span><h1>{result ? "Architecture, with evidence." : "Your next system starts here."}</h1></div><span className={`st-badge ${stale ? "st-badge-warning" : ""}`}>{result ? stale ? "PREVIOUS RESULT · NOT CURRENT" : restoredRunId ? "SAVED MODEL RESULT" : "LIVE MODEL RESULT" : "AWAITING INPUT"}</span></div>
        {error && <div className="st-error" role="alert"><div><strong>Request needs attention</strong><p>{error}</p><small>Your inputs{result ? " and last result are" : " are"} preserved. No sample result has been substituted.</small></div><button type="button" onClick={() => setError("")} aria-label="Dismiss error">×</button></div>}
        {notice && <div className="st-notice" role="status">{notice}<button type="button" aria-label="Dismiss notice" onClick={() => setNotice("")}>×</button></div>}
        {result && <><div className="st-alternatives" role="group" aria-label="Architecture alternatives">{result.analysis.options.map((item, index) => <button type="button" key={item.id} aria-pressed={option?.id === item.id} onClick={() => { setOptionId(item.id); setComponentId(null); }}><span className="st-option-number">0{index + 1}</span><span>{item.name}{item.id === result.analysis.recommendedOptionId && <small>MODEL RECOMMENDATION</small>}</span><span aria-hidden="true">{option?.id === item.id ? "●" : "○"}</span></button>)}</div>
          <details className="st-result-summary"><summary>{result.analysis.summary}</summary><div><strong>{previousRequirements ? "What changed" : "Model change summary"}</strong><p>{result.analysis.changeSummary}</p></div></details>
        </>}
        {job?.changeApproval && <DesignChangeOutcome job={job} />}
        {requirementId && <div className="st-highlight-bar">Linked requirement: <code>{requirementId}</code><button type="button" onClick={() => setRequirementId(null)}>Clear highlight ×</button></div>}
        {lens && <div className="st-highlight-bar">Review lens: {lens} · source-level findings only<button type="button" onClick={() => setLens(null)}>Clear lens ×</button></div>}
        <ArchitectureCanvas key={`${result?.resultId ?? "empty"}-${option?.id ?? "none"}`} option={option} selectedId={componentId} highlightedIds={requirementId ? option?.components.filter((item) => item.requirementIds.includes(requirementId)).map((item) => item.id) ?? [] : null}
          expanded={!promptVisible && !inspectorVisible} onExpand={() => {
            if (promptVisible || inspectorVisible) {
              panelsBeforeExpand.current = { prompt: promptVisible, inspector: inspectorVisible };
              setPromptVisible(false); setInspectorVisible(false);
            } else {
              setPromptVisible(panelsBeforeExpand.current.prompt); setInspectorVisible(panelsBeforeExpand.current.inspector);
            }
          }}
          onSelect={(id) => { setComponentId(id); setTab("component"); setInspectorVisible(true); }} />
        <footer className="st-workspace-footer"><span><span className="st-status-dot" />{result ? `${result.sources.length} sources · ${result.analysis.requirements.length} requirements · ${result.analysis.review.length} review dimensions` : "Source → requirement → component → infrastructure"}</span><span>NO RESOURCES DEPLOYED</span></footer>
      </section>
      <Inspector tab={tab} onTab={setTab} result={result} option={option} component={component} selectedRequirement={requirementId} onRequirement={setRequirementId} onSource={openSource} lens={lens} onLens={setLens} build={build} stale={stale} busy={busy} onBuild={() => { void generateBuild(); }} onDownload={() => { void download(); }} previousRequirements={previousRequirements} onDesignChange={requestDesignChange} />
    </main>
    {source && <SourceDrawer source={source} onClose={() => setSource(null)} />}
    {historyOpen && <RunHistoryPanel client={client} working={!!busy || reading}
      workingCopyHasContent={Boolean(inputs.title || inputs.prompt || inputs.documents.length || result)}
      onOpen={(saved) => { void openSavedRun(saved); }} onClose={() => setHistoryOpen(false)} />}
    {changeDraft && <DesignChangeDrawer finding={changeDraft.finding} option={changeDraft.option} intent={changeDraft.intent}
      busy={busy === "analysis"} current={changeCurrent} error={changeError}
      onApprove={(instruction) => { void approveDesignChange(instruction); }} onClose={() => setChangeDraft(null)} />}
  </div>;
}
