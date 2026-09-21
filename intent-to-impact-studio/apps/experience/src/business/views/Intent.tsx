import { useRef, useState } from "react";
import type { DesignDraft } from "../model";
import { MAX_DOCUMENTS, MAX_PROMPT_LENGTH } from "../draft";
import { Arrow } from "./Shared";

export function IntentComposer({ draft, busy, onTitle, onPrompt, onFiles, onSource, onRemove, onBuild, onExample }: {
  draft: DesignDraft; busy: boolean; onTitle: (title: string) => void; onPrompt: (prompt: string) => void;
  onFiles: (files: File[]) => void; onSource: (id: string) => void; onRemove: (id: string) => void;
  onBuild: () => void; onExample: () => void;
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  return <div className="wb-intake">
    <section className="wb-composer">
      <header className="wb-hero-heading">
        <p className="wb-eyebrow"><span className="wb-small-rule" /> Business first. Architecture next.</p>
        <h1 id="wb-page-title" tabIndex={-1}>Turn your business process into an architecture you can <em>defend.</em></h1>
        <p className="wb-lead">Start with what your business needs to do. Shape a shared understanding, explore design choices, and challenge the whole picture.</p>
      </header>
      <form className="wb-intent-form" onSubmit={(event) => { event.preventDefault(); onBuild(); }}>
        <label className="wb-field">
          <span>Project name <small>optional</small></span>
          <input value={draft.title} maxLength={160} placeholder="e.g. A better order-to-fulfilment experience" onChange={(event) => onTitle(event.target.value)} />
        </label>
        <label className="wb-field">
          <span id="wb-prompt-label">What are you trying to achieve?</span>
          <textarea className="wb-prompt" value={draft.prompt} maxLength={MAX_PROMPT_LENGTH} onChange={(event) => onPrompt(event.target.value)}
            aria-labelledby="wb-prompt-label" aria-describedby="wb-prompt-help" placeholder="Describe your process, who it serves, and what needs to work better. What systems must stay? What constraints matter?" />
          <span className="wb-field-meta" id="wb-prompt-help"><span>Your own words are a good starting point.</span><span>{draft.prompt.length.toLocaleString()} / {MAX_PROMPT_LENGTH.toLocaleString()}</span></span>
        </label>
        <div className={`wb-dropzone${dragging ? " wb-dragging" : ""}`}
          onDragOver={(event) => { event.preventDefault(); if (!busy) setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => { event.preventDefault(); setDragging(false); if (!busy) onFiles(Array.from(event.dataTransfer.files)); }}>
          <span className="wb-document-glyph" aria-hidden="true">↥</span>
          <div><strong>Add the context behind the process</strong><p>Drop business-process documents here, or browse files.</p>
            <p className="wb-caption">UTF-8 TXT or Markdown · 1 MB each · up to {MAX_DOCUMENTS} files · 150,000 characters combined</p></div>
          <input className="wb-visually-hidden" type="file" multiple accept=".txt,.md,.markdown,text/plain,text/markdown" ref={fileInput}
            aria-label="Attach business-process documents" disabled={busy} onChange={(event) => {
              onFiles(Array.from(event.target.files ?? [])); event.target.value = "";
            }} />
          <button className="wb-button wb-secondary" type="button" disabled={busy} onClick={() => fileInput.current?.click()}>
            {busy ? "Reading files…" : "Attach files"}
          </button>
        </div>
        {draft.documents.length > 0 && <ul className="wb-document-list" aria-label="Attached documents">
          {draft.documents.map((doc) => <li key={doc.id}>
            <button type="button" className="wb-source-link" onClick={() => onSource(doc.id)}><span aria-hidden="true">▤</span> {doc.name}</button>
            <span className="wb-caption">{doc.text.length.toLocaleString()} characters</span>
            <button className="wb-icon-button" type="button" aria-label={`Remove ${doc.name}`} disabled={busy} onClick={() => onRemove(doc.id)}>×</button>
          </li>)}
        </ul>}
        <div className="wb-intake-footer">
          <p className="wb-caption">Private by default. Files stay in this tab unless you explicitly save in this browser.</p>
          {(draft.selectedOptionId || draft.kind === "example" || Object.values(draft.brief).some(Boolean)) && <p className="wb-caption">Changing the prompt or sources resets the understanding, selection and review notes so they stay aligned.</p>}
          <div className="wb-actions">
            <button className="wb-button wb-primary wb-build" type="submit" disabled={busy}>Build my brief <Arrow /></button>
            <button className="wb-button wb-text" type="button" disabled={busy} onClick={onExample}>Try worked example <span aria-hidden="true">→</span></button>
          </div>
          <p className="wb-caption">Create an editable local brief, not an AI-generated assessment.</p>
        </div>
      </form>
    </section>
    <aside className="wb-studio-preview" aria-label="What you will create">
      <div className="wb-preview-topline"><span className="wb-eyebrow">From intent to impact</span><span aria-hidden="true">↗</span></div>
      <h2>Not just a diagram.<br />A reason behind<br /><em>every decision.</em></h2>
      <div className="wb-mini-diagram" aria-hidden="true">
        <div className="wb-mini-node wb-mini-origin"><span>01 / BUSINESS INTENT</span><strong>A process that works</strong></div>
        <div className="wb-mini-connector" />
        <div className="wb-mini-pair"><div className="wb-mini-node"><span>PEOPLE</span><strong>Who it serves</strong></div><div className="wb-mini-node"><span>SYSTEMS</span><strong>How it happens</strong></div></div>
        <div className="wb-mini-connector" />
        <div className="wb-mini-node wb-mini-outcome"><span>02 / DESIGN DECISION</span><strong>Architecture with context <span>↗</span></strong></div>
      </div>
      <ol className="wb-output-list">
        <li><span>01</span><div><h3>A shared understanding</h3><p>Goals, people, process and the questions worth asking.</p></div></li>
        <li><span>02</span><div><h3>Considered architecture</h3><p>Compare starting patterns. Capture why one fits.</p></div></li>
        <li><span>03</span><div><h3>A complete perspective</h3><p>Nine review dimensions and an exportable design brief.</p></div></li>
      </ol>
      <div className="wb-preview-footnote"><span aria-hidden="true">◌</span> The worked example shows the proposed experience. Your own project stays yours to author.</div>
    </aside>
  </div>;
}
