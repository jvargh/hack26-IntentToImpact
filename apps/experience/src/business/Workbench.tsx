import { useEffect, useRef, useState } from "react";
import type { DesignDraft, Step } from "./model";
import { STEPS } from "./model";
import {
  appendDocuments, choosePattern, clearDraft, exampleDraft, exportMarkdown, loadDraft,
  MAX_DOCUMENTS, MAX_FILE_BYTES, MAX_TEXT_LENGTH, newDraft, prepareBrief, readDocument, reviseInputs, saveDraft,
} from "./draft";
import { IntentComposer } from "./views/Intent";
import { ArchitectureOptions, Assessment360, DesignBrief, UnderstandingEditor } from "./views/DesignPages";
import { Modal, SourceInspector } from "./views/Shared";
import "./workbench.css";

type Dialog = { type: "source"; id: string } | { type: "new" | "example" | "resume" | "save" | "clear" };

function hasContent(draft: DesignDraft): boolean {
  return Boolean(draft.title || draft.prompt || draft.documents.length || draft.selectedOptionId || draft.designRationale
    || Object.values(draft.brief).some(Boolean) || draft.questions.some((question) => question.answer)
    || Object.values(draft.reviews).some((review) => review.note || review.status !== "not-reviewed"));
}

function messageFrom(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Your current draft has been kept.";
}

export function Workbench() {
  const [draft, setDraft] = useState<DesignDraft>(newDraft);
  const current = useRef(draft);
  const [step, setStep] = useState<Step>("intent");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const reading = useRef(false);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [stored, setStored] = useState<{ draft: DesignDraft | null; error: string }>(() => {
    try { return { draft: loadDraft(), error: "" }; }
    catch (loadError) { return { draft: null, error: messageFrom(loadError) }; }
  });
  const navigated = useRef(false);

  const apply = (next: DesignDraft, changed = true) => {
    current.current = next;
    setDraft(next);
    setDirty(changed);
    setNotice("");
  };
  const edit = (patch: Partial<DesignDraft>) => apply({ ...current.current, ...patch, updatedAt: new Date().toISOString() });
  const go = (next: Step) => { navigated.current = true; setStep(next); setError(""); };

  useEffect(() => {
    if (navigated.current) document.getElementById("wb-page-title")?.focus();
  }, [step]);

  useEffect(() => {
    if (!dirty || !hasContent(draft)) return;
    const preventLoss = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", preventLoss);
    return () => window.removeEventListener("beforeunload", preventLoss);
  }, [dirty, draft]);

  const replace = (type: "new" | "example" | "resume") => {
    const next = type === "example" ? exampleDraft() : type === "resume" ? stored.draft : newDraft();
    if (!next) return;
    apply(next, type === "example");
    go("intent");
    setDialog(null);
    if (type === "resume") setNotice("Saved draft opened. Its documents are stored in this browser; new edits stay in memory until you save again.");
    if (type === "example") setNotice("Worked example opened. Its understanding and findings are illustrative, not live analysis.");
    if (type === "new") setNotice("New in-memory draft started. Any previously saved draft remains in this browser.");
  };

  const requestReplace = (type: "new" | "example" | "resume") => {
    if (hasContent(current.current) || type === "resume") setDialog({ type });
    else replace(type);
  };

  const addFiles = async (files: File[]) => {
    if (!files.length || reading.current) return;
    reading.current = true;
    setBusy(true);
    setError("");
    try {
      if (files.length + current.current.documents.length > MAX_DOCUMENTS) {
        throw new Error(`Add up to ${MAX_DOCUMENTS} documents per brief.`);
      }
      const documents = await Promise.all(files.map(readDocument));
      apply(appendDocuments(current.current, documents));
      setNotice(`${documents.length} document${documents.length === 1 ? "" : "s"} attached locally. No content was uploaded or analysed.`);
    } catch (fileError) { setError(messageFrom(fileError)); }
    finally { reading.current = false; setBusy(false); }
  };

  const exportBrief = () => {
    try {
      const markdown = exportMarkdown(current.current);
      const url = URL.createObjectURL(new Blob([markdown], { type: "text/markdown;charset=utf-8" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${(current.current.title || "architecture-design-brief").replace(/[^\p{L}\p{N} _-]/gu, "").trim().replace(/\s+/g, "-").slice(0, 100) || "architecture-design-brief"}.md`;
      document.body.append(anchor);
      try { anchor.click(); }
      finally { anchor.remove(); window.setTimeout(() => URL.revokeObjectURL(url), 1000); }
      setError("");
      setNotice("Markdown download started. Raw source documents are not included.");
    } catch (exportError) { setError(messageFrom(exportError)); }
  };

  const save = () => {
    if (stored.error) {
      setError("The previous saved data could not be read. Remove it explicitly before saving a replacement. You can still export your current brief.");
      setDialog(null);
      return;
    }
    try {
      saveDraft(current.current);
      setDirty(false);
      setStored({ draft: current.current, error: "" });
      setDialog(null);
      setError("");
      setNotice("Draft saved in this browser, including document contents. Avoid shared devices and remove saved data when finished.");
    } catch (saveError) { setDialog(null); setError(messageFrom(saveError)); }
  };

  const removeSaved = () => {
    try {
      clearDraft();
      setStored({ draft: null, error: "" });
      setDialog(null);
      if (hasContent(current.current)) setDirty(true);
      setError("");
      setNotice("Saved browser data removed. Your open draft is still in memory and can be exported.");
    } catch (clearError) { setDialog(null); setError(messageFrom(clearError)); }
  };

  const source = dialog?.type === "source" ? draft.documents.find((doc) => doc.id === dialog.id) : undefined;
  const contentPresent = hasContent(draft);
  const stepIndex = STEPS.findIndex((item) => item.id === step);
  const openSource = (id: string) => setDialog({ type: "source", id });

  return <div className="business-workbench">
    <div inert={dialog !== null}>
      <a className="wb-skip-link" href="#wb-main">Skip to your architecture workbench</a>
      <header className="wb-site-header">
        <a className="wb-wordmark" href="#wb-main" aria-label="Intent to Impact workbench">
          <span className="wb-brand-mark" aria-hidden="true"><i /><i /><i /></span><span>intent<span className="wb-wordmark-arrow">→</span>impact</span>
        </a>
        <span className="wb-preview-indicator"><span aria-hidden="true" />Frontend preview · AI analysis not connected</span>
        <div className="wb-header-actions">
          <button className="wb-button wb-text" disabled={busy} onClick={() => requestReplace("new")}>New brief</button>
          <button className="wb-button wb-secondary" disabled={busy} onClick={() => setDialog({ type: "save" })}>Save in browser</button>
        </div>
      </header>
      <div className="wb-workspace">
        <nav className="wb-step-nav" aria-label="Architecture design steps">
          <ol>{STEPS.map((item) => <li key={item.id}>
            <button aria-current={step === item.id ? "step" : undefined} onClick={() => go(item.id)}>
              <span className="wb-step-number">{item.number}</span><span><strong>{item.title}</strong><small>{item.description}</small></span>
              <span className="wb-step-arrow" aria-hidden="true">→</span>
            </button>
          </li>)}</ol>
        </nav>
        <div className="wb-draft-strip">
          <div><span className={`wb-origin${draft.kind === "example" ? " wb-origin-example" : ""}`}>{draft.kind === "example" ? "Worked example · illustrative" : "Your architecture studio"}</span>
            {contentPresent && <span className="wb-save-state">{dirty ? "Unsaved · in this tab only" : stored.draft?.id === draft.id ? "Saved locally" : "In this tab only"}</span>}</div>
          {step !== "intent" && <span className="wb-caption">{draft.title || "Untitled brief"}</span>}
        </div>
        {stored.error && <div className="wb-storage-warning" role="alert"><div><strong>Saved browser data needs attention</strong><p>{stored.error}</p><p>Your saved data has not been changed. You can work in memory and export below.</p></div><button className="wb-button wb-secondary" onClick={() => setDialog({ type: "clear" })}>Remove saved browser data</button></div>}
        {stored.draft && stored.draft.id !== draft.id && <div className="wb-saved-banner"><div><strong>A saved brief is available in this browser</strong><p>{stored.draft.title || "Untitled brief"} · {stored.draft.documents.length} stored document{stored.draft.documents.length === 1 ? "" : "s"}. Open it only on a device you trust.</p></div><button className="wb-button wb-secondary" disabled={busy} onClick={() => requestReplace("resume")}>Resume saved draft</button></div>}
        {error && <div className="wb-feedback wb-error" role="alert"><p>{error}</p><button className="wb-icon-button" aria-label="Dismiss error" onClick={() => setError("")}>×</button></div>}
        <div className="wb-live-region" role="status" aria-live="polite">{notice && <div className="wb-feedback wb-notice"><p>{notice}</p><button className="wb-icon-button" aria-label="Dismiss notification" onClick={() => setNotice("")}>×</button></div>}</div>
        <main id="wb-main" tabIndex={-1}>
          {step === "intent" && <IntentComposer draft={draft} busy={busy}
            onTitle={(title) => edit({ title })}
            onPrompt={(prompt) => apply(reviseInputs(current.current, { prompt }))}
            onFiles={(files) => { void addFiles(files); }} onSource={openSource}
            onRemove={(id) => apply(reviseInputs(current.current, { documents: current.current.documents.filter((doc) => doc.id !== id) }))}
            onBuild={() => {
              try { apply(prepareBrief(current.current)); go("understanding"); }
              catch (prepareError) { setError(messageFrom(prepareError)); }
            }} onExample={() => requestReplace("example")} />}
          {step === "understanding" && <UnderstandingEditor draft={draft} onSource={openSource}
            onBrief={(key, value) => edit({ brief: { ...current.current.brief, [key]: value } })}
            onAnswer={(id, answer) => edit({ questions: current.current.questions.map((question) => question.id === id ? { ...question, answer } : question) })}
            onNext={() => go("architecture")} />}
          {step === "architecture" && <ArchitectureOptions draft={draft} onSource={openSource}
            onSelect={(id) => {
              const previous = current.current;
              const next = choosePattern(previous, id);
              if (next === previous) return;
              apply(next);
              if (previous.selectedOptionId) setNotice("Pattern changed; review notes retained for re-review.");
            }}
            onRationale={(designRationale) => edit({ designRationale })} onNext={() => go("assessment")} />}
          {step === "assessment" && <Assessment360 draft={draft} onSource={openSource}
            onReview={(id, patch) => edit({ reviews: { ...current.current.reviews, [id]: { ...current.current.reviews[id]!, ...patch } } })}
            onNext={() => go("handoff")} />}
          {step === "handoff" && <DesignBrief draft={draft} onSource={openSource} onExport={exportBrief} onStep={go} />}
        </main>
        <footer className="wb-footer"><div><strong>Business context, before cloud components.</strong><p>Local authoring preview. No documents are uploaded and no AI assessment is performed.</p></div>
          <div><span className="wb-caption">Step {stepIndex + 1} of {STEPS.length}</span><button className="wb-button wb-text" onClick={exportBrief}>Export current brief</button>
            {(stored.draft || stored.error) && <button className="wb-button wb-text" onClick={() => setDialog({ type: "clear" })}>Remove saved data</button>}</div>
        </footer>
      </div>
    </div>
    {source && <SourceInspector key={source.id} document={source} onClose={() => setDialog(null)} onEdit={(text) => {
      if (text === source.text) return null;
      if (!text.trim()) return "A document needs readable content. Your original text has been kept.";
      if (text.includes("\0")) return "Binary content is not supported.";
      const bytes = new TextEncoder().encode(text).length;
      if (bytes > MAX_FILE_BYTES) return "Keep each document under 1 MB.";
      if (current.current.documents.reduce((count, doc) => count + (doc.id === source.id ? text.length : doc.text.length), 0) > MAX_TEXT_LENGTH) return "Keep combined document text within 150,000 characters.";
      apply(reviseInputs(current.current, { documents: current.current.documents.map((doc) => doc.id === source.id ? { ...doc, text, bytes } : doc) }));
      setNotice("Local source updated. Understanding, selection and review notes were reset; rebuild and review your brief.");
      return null;
    }} />}
    {dialog && dialog.type !== "source" && <Modal title={
      dialog.type === "save" ? "Save this draft in your browser?" : dialog.type === "clear" ? "Remove saved browser data?"
        : dialog.type === "resume" ? "Open the saved local draft?" : dialog.type === "example" ? "Replace this draft with the worked example?" : "Start a new brief?"
    } onClose={() => setDialog(null)}>
      <div className="wb-stack">
        {dialog.type === "save" ? <>
          <p>This explicitly saves your prompt, authored notes and <strong>full document contents</strong> in this browser. Nothing is uploaded.</p>
          <p>Other people using this browser profile may be able to read them. Avoid shared devices and sensitive documents. Future edits are not saved automatically.</p>
          {stored.draft && stored.draft.id !== draft.id && <p className="wb-warning-text">Saving will replace “{stored.draft.title || "Untitled brief"}”, the draft currently saved in this browser.</p>}
          {stored.error && <p className="wb-warning-text">The previous saved data could not be read. It must be explicitly removed before you can save a replacement.</p>}
        </> : dialog.type === "clear" ? <p>This deletes the saved draft and its document contents from this browser. Your currently open in-memory draft will remain. This cannot be undone.</p>
          : dialog.type === "resume" ? <><p>The saved draft contains {stored.draft?.documents.length ?? 0} document(s) stored in this browser. Opening it restores those contents for local editing.</p>{contentPresent && <p>Your current draft will be replaced. Unsaved changes will be lost; cancel and export first if you need to keep them.</p>}</>
            : <><p>{dirty ? "Your current draft has unsaved work." : "Your current draft contains content."} Replacing it discards the in-memory draft. Cancel and export first to keep a copy.</p><p>{dialog.type === "example" ? "The example uses a supplied order-to-fulfilment scenario with clearly labelled illustrative findings." : "You will get an empty local brief. Any previously saved browser draft will remain."}</p></>}
        <div className="wb-actions">
          <button className="wb-button wb-secondary" onClick={() => setDialog(null)}>Cancel</button>
          <button className="wb-button wb-primary" disabled={dialog.type === "save" && Boolean(stored.error)} onClick={() => {
            if (dialog.type === "save") save();
            else if (dialog.type === "clear") removeSaved();
            else replace(dialog.type);
          }}>{dialog.type === "save" ? "Save draft locally" : dialog.type === "clear" ? "Remove saved data permanently" : dialog.type === "resume" ? "Open saved draft" : dialog.type === "example" ? "Replace with example" : "Start new brief"}</button>
        </div>
      </div>
    </Modal>}
  </div>;
}
