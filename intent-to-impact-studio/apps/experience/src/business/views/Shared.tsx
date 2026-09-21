import { useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import type { SourceDocument } from "../model";
import { MAX_TEXT_LENGTH } from "../draft";

export function Arrow() {
  return <span aria-hidden="true">↗</span>;
}

export function PageHeading({ eyebrow, title, children }: { eyebrow: string; title: string; children: ReactNode }) {
  return <header className="wb-page-heading">
    <p className="wb-eyebrow">{eyebrow}</p>
    <h1 tabIndex={-1} id="wb-page-title">{title}</h1>
    <div className="wb-lead">{children}</div>
  </header>;
}

export function SourceLinks({ documents, sourceIds, onOpen }: {
  documents: SourceDocument[]; sourceIds?: string[]; onOpen: (id: string) => void;
}) {
  const sources = sourceIds ? documents.filter((doc) => sourceIds.includes(doc.id)) : documents;
  return <div className="wb-source-links">
    {sources.map((doc) => <button className="wb-source-link" key={doc.id} onClick={() => onOpen(doc.id)}>
      <span aria-hidden="true">↳</span> {doc.name}
    </button>)}
  </div>;
}

export function Modal({ title, children, onClose, wide = false }: {
  title: string; children: ReactNode; onClose: () => void; wide?: boolean;
}) {
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const dialog = panel.current;
    dialog?.querySelector<HTMLElement>("[data-wb-initial-focus]")?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
      if (previous?.isConnected) previous.focus();
    };
  }, []);

  const handleKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); onClose(); return; }
    if (event.key !== "Tab" || !panel.current) return;
    const items = Array.from(panel.current.querySelectorAll<HTMLElement>("*")).filter((node) => !node.hidden && node.matches(
      'button:not(:disabled), [href], input:not(:disabled), textarea:not(:disabled), select:not(:disabled), [tabindex="0"]',
    ));
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); event.stopPropagation(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); event.stopPropagation(); first?.focus(); }
  };

  return <div className="wb-modal-backdrop">
    <div className={`wb-modal${wide ? " wb-modal-wide" : ""}`} ref={panel} role="dialog" aria-modal="true" aria-labelledby={titleId} onKeyDown={handleKey}>
      <header className="wb-modal-header">
        <h2 id={titleId}>{title}</h2>
        <button className="wb-icon-button" aria-label="Close dialog" data-wb-initial-focus onClick={onClose}>×</button>
      </header>
      {children}
    </div>
  </div>;
}

export function SourceInspector({ document: source, onClose, onEdit }: {
  document: SourceDocument; onClose: () => void; onEdit: (text: string) => string | null;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(source.text);
  const [error, setError] = useState("");
  const [discard, setDiscard] = useState(false);
  const requestClose = () => {
    if (editing && text !== source.text) setDiscard(true);
    else onClose();
  };
  return <Modal title={source.name} onClose={requestClose} wide>
    <p className="wb-caption">Local source · {source.text.length.toLocaleString()} characters · Nothing is uploaded</p>
    {error && <p role="alert" className="wb-error">{error}</p>}
    {discard ? <div className="wb-stack">
      <h3>Discard source edits?</h3>
      <p>The attached document will keep its previous contents.</p>
      <div className="wb-actions">
        <button className="wb-button wb-primary" onClick={() => setDiscard(false)}>Keep editing</button>
        <button className="wb-button wb-secondary" onClick={onClose}>Discard edits</button>
      </div>
    </div> : <>
      {editing ? <label className="wb-field">
        <span>Document text</span>
        <textarea className="wb-source-editor" value={text} maxLength={MAX_TEXT_LENGTH} onChange={(event) => setText(event.target.value)} />
        <small>Applying changes resets the understanding, pattern selection and review notes. Your original file is not modified.</small>
      </label> : <pre className="wb-source-text" tabIndex={0}>{source.text}</pre>}
      <div className="wb-actions">
        {editing ? <>
          <button className="wb-button wb-primary" onClick={() => {
            const message = onEdit(text);
            if (message) setError(message);
            else onClose();
          }}>Apply source changes</button>
          <button className="wb-button wb-secondary" onClick={() => { setText(source.text); setEditing(false); setError(""); }}>Cancel editing</button>
        </> : <button className="wb-button wb-secondary" onClick={() => setEditing(true)}>Edit local copy</button>}
      </div>
    </>}
  </Modal>;
}
