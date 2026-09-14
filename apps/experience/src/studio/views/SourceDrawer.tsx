import { useEffect, useId, useRef } from "react";
import type { ReactNode } from "react";
import type { SourceDocument } from "../contracts";

export function StudioDrawer({ title, eyebrow, closeLabel, onClose, children, variant = "source" }: {
  title: string; eyebrow: string; closeLabel: string; onClose: () => void; children: ReactNode; variant?: "source" | "history" | "change";
}) {
  const titleId = useId();
  const dialog = useRef<HTMLDivElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previous = document.activeElement;
    close.current?.focus();
    return () => { if (previous instanceof HTMLElement && previous.isConnected) previous.focus(); };
  }, []);
  return <div className="st-drawer-backdrop" onClick={onClose}>
    <div className={`st-source-drawer${variant !== "source" ? ` st-${variant}-drawer` : ""}`} role="dialog" aria-modal="true" aria-labelledby={titleId} ref={dialog} onClick={(event) => event.stopPropagation()}
      onKeyDown={(event) => {
        if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); onClose(); }
        if (event.key === "Tab") {
          // Preserve DOM order even in selector engines that group selector-list matches.
          const elements = [...(dialog.current?.querySelectorAll<HTMLElement>("*") ?? [])].filter((element) =>
            element.matches("button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex='0']"));
          const first = elements?.[0]; const last = elements?.[elements.length - 1];
          if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
          if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
        }
      }}>
      <header><div><span className="st-overline">{eyebrow}</span><h2 id={titleId}>{title}</h2></div><button type="button" aria-label={closeLabel} ref={close} onClick={onClose}>×</button></header>
      {children}
    </div>
  </div>;
}

export function SourceDrawer({ source, onClose }: { source: SourceDocument; onClose: () => void }) {
  return <StudioDrawer title={source.name} eyebrow="EXACT SOURCE / LOCAL SNAPSHOT" closeLabel="Close source" onClose={onClose}>
      <p>Verbatim submitted text, not a generated summary. Citations link to the whole source, not verified passage-level quotations.</p>
      <pre tabIndex={0}>{source.text}</pre><footer><code>{source.id}</code><span>{source.text.length.toLocaleString()} characters</span></footer>
  </StudioDrawer>;
}
