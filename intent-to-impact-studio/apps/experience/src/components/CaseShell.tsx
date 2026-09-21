import type { ReactNode } from "react";
import { HISTORICAL_NOTICE } from "../data/fixtureTransport";
import type { SceneChoice } from "../data/fixtureTransport";

interface CaseShellProps {
  choices: readonly SceneChoice[];
  selectedId: string;
  busy: boolean;
  onSceneChange(id: string): void;
  children: ReactNode;
}

export function CaseShell({ choices, selectedId, busy, onSceneChange, children }: CaseShellProps) {
  return <>
    <a href="#main-content" className="skip-link">Skip to preview</a>
    <aside className="historical-notice" aria-label="Historical fixture notice">
      <span className="notice-label">Historical fixture · V2</span>
      <span><strong>{HISTORICAL_NOTICE}</strong> LOCAL-09 requires NSP Enforced with zero external access rules. V3 handoff pending.</span>
    </aside>
    <header className="site-header">
      <div className="wordmark" aria-label="Intent to Impact">
        <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
        <span>intent <span className="wordmark-divider">/</span> impact</span>
      </div>
      <div className="review-context"><span className="mode-label">fixture / ux-mock</span><span>Visual review only</span></div>
    </header>
    <div className="workspace">
      <div className="review-toolbar">
        <div><p className="eyebrow">CONTOSO · CLAIMS EXPERIENCE</p><p className="toolbar-note">Seven authored snapshots. No workflow is executed.</p></div>
        <label className="scene-picker">Review scene
          <select value={choices.some((choice) => choice.id === selectedId) ? selectedId : ""}
            disabled={busy || choices.length === 0} onChange={(event) => onSceneChange(event.target.value)}>
            <option value="" disabled>Select a snapshot</option>
            {choices.map((choice) => <option key={choice.id} value={choice.id}>{choice.label}</option>)}
          </select>
        </label>
      </div>
      <main id="main-content" aria-busy={busy}>{children}</main>
      <footer className="page-footer">
        <span>Early preview · 7 scenes, not the full journey</span>
        <span>GATE-UX01 pending · Not eligible for live proof</span>
        <span className="identity-marker" title="Fixed demo-human; local-demo assurance only. No real approval is recorded.">Demo Identity · local-demo</span>
      </footer>
    </div>
  </>;
}
