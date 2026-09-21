import { useEffect, useRef } from "react";
import type { EvidenceReference } from "@contracts/core";
import type { FixtureRecord } from "../data/contracts";
import { HISTORICAL_NOTICE } from "../data/fixtureTransport";
import { formatTime, StatusBadge, statusTone } from "./StatusBadge";

interface EvidenceDrawerProps {
  records: readonly FixtureRecord[];
  selectedRecordId?: string;
  opener: HTMLElement | null;
  onClose(): void;
}

export function EvidenceDrawer({ records, selectedRecordId, opener, onClose }: EvidenceDrawerProps) {
  const dialog = useRef<HTMLDivElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  const evidence = records.filter((record): record is EvidenceReference => record.artifactType === "evidence-reference");
  const selected = records.find((record) => record.artifactId === selectedRecordId);
  useEffect(() => {
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    close.current?.focus();
    return () => {
      document.body.style.overflow = overflow;
      queueMicrotask(() => { if (opener?.isConnected) opener.focus(); });
    };
  }, [opener]);

  return <div className="drawer-backdrop">
    <div className="evidence-drawer" role="dialog" aria-modal="true" aria-labelledby="evidence-title"
      aria-describedby="evidence-boundary" ref={dialog} onKeyDown={(event) => {
        if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); onClose(); }
        if (event.key === "Tab") {
          const controls = Array.from(dialog.current?.querySelectorAll<HTMLElement>(
            'button:not(:disabled), a[href], summary, [tabindex="0"]',
          ) ?? []).filter((control) => {
            let parent = control.parentElement;
            while (parent && parent !== dialog.current) {
              if (parent.hidden || (parent.tagName === "DETAILS" && !parent.hasAttribute("open")
                && parent.querySelector("summary") !== control)) return false;
              parent = parent.parentElement;
            }
            return true;
          }).sort((left, right) => left === right ? 0
            : left.compareDocumentPosition(right) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1);
          if (controls.length > 0) {
            event.preventDefault();
            const current = controls.findIndex((control) => control === document.activeElement);
            const next = (current + (event.shiftKey ? -1 : 1) + controls.length) % controls.length;
            controls[next]?.focus();
          }
        }
      }}>
      <header className="drawer-heading">
        <div><p className="eyebrow">SOURCE &amp; LIMITATIONS</p><h2 id="evidence-title">Inspect the evidence.</h2></div>
        <button ref={close} className="icon-button" aria-label="Close evidence" onClick={onClose}>×</button>
      </header>
      <p id="evidence-boundary" className="drawer-warning"><strong>Fixture only. {HISTORICAL_NOTICE}</strong> All source records are synthetic and ineligible for live proof.</p>
      {evidence.length === 0 && <section className="empty-inline">
        <h3>No configuration evidence loaded</h3><p>This snapshot explicitly lacks evidence. Missing is not verified; no live source will be contacted.</p>
      </section>}
      {evidence.map((record, index) => <article className="evidence-card" key={record.artifactId}>
        <div className="evidence-card-heading"><h3>Configuration source {index + 1}</h3>
          <StatusBadge label={record.evidenceState} tone={statusTone(record.evidenceState)} /></div>
        <dl className="evidence-facts">
          <div><dt>Source</dt><dd>Authored fixture · {record.collector.collectorId}</dd></div>
          <div><dt>Observed time</dt><dd>{formatTime(record.observedAt)}</dd></div>
          <div><dt>Resource</dt><dd>{record.scope.resourceIds[0]?.split("/").at(-1) ?? "No resource supplied"} <span className="muted">(synthetic)</span></dd></div>
          <div><dt>Origin / eligibility</dt><dd>{record.origin} / {record.eligibility} for live proof</dd></div>
          <div><dt>Completeness</dt><dd>{record.completeness}</dd></div>
          <div><dt>Supported assertions</dt><dd><ul>{record.supportedAssertionIds.map((id) =>
            <li key={id}>{id.replace(/^PRED-/, "").replaceAll("-", " ").toLowerCase()}</li>)}</ul></dd></div>
          <div><dt>Valid-until example</dt><dd>{record.validUntil ? formatTime(record.validUntil) : "Not supplied"}</dd></div>
        </dl>
        <details className="technical-detail"><summary>Technical references &amp; hashes</summary>
          <dl><dt>Artifact ID</dt><dd><code>{record.artifactId}</code></dd>
            <dt>Resource ID</dt><dd><code>{record.scope.resourceIds[0] ?? "Unavailable"}</code></dd>
            <dt>Record checksum</dt><dd><code>{record.stateChecksum}</code></dd>
            <dt>Source checksum</dt><dd><code>{record.sourceChecksum}</code></dd></dl>
        </details>
      </article>)}
      {selected && <details className="technical-detail selected-record">
        <summary>Selected source: {selected.artifactType.replaceAll("-", " ")}</summary>
        <pre>{JSON.stringify(selected, null, 2)}</pre>
      </details>}
      <details className="technical-detail">
        <summary>All loaded fixture record details</summary>
        <p>Read-only fixture records. Opaque delivery references are not loaded canonical delivery records.</p>
        {records.map((record) => <details key={record.artifactId}>
          <summary>{record.artifactType.replaceAll("-", " ")}</summary>
          <pre>{JSON.stringify(record, null, 2)}</pre>
        </details>)}
      </details>
      <button className="button button-secondary drawer-done" onClick={onClose}>Return to snapshot</button>
    </div>
  </div>;
}
