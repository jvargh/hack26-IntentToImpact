import { useCallback, useEffect, useRef, useState } from "react";
import { CaseShell } from "./components/CaseShell";
import { PromiseCard } from "./components/PromiseCard";
import { RiskPanel } from "./components/RiskPanel";
import { ContinuityGraph } from "./components/ContinuityGraph";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { createFixtureTransport } from "./data/fixtureTransport";
import type { FixtureTransport, LoadedScene } from "./data/fixtureTransport";

const defaultTransport = createFixtureTransport();

export function LegacyPreview({ transport = defaultTransport, initialSceneId }: {
  transport?: FixtureTransport;
  initialSceneId?: string;
}) {
  const initial = initialSceneId ?? new URLSearchParams(window.location.search).get("scene") ?? transport.initialSceneId;
  const [selectedId, setSelectedId] = useState(initial);
  const [scene, setScene] = useState<LoadedScene | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<{ opener: HTMLElement | null; recordId?: string } | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const request = useRef(0);
  const focusAfterLoad = useRef(false);

  const load = useCallback(async (id: string) => {
    const number = ++request.current;
    setSelectedId(id); setBusy(true); setError(null); setDrawer(null);
    try {
      const loaded = await transport.loadScene(id);
      if (number !== request.current) return;
      focusAfterLoad.current = true;
      setScene(loaded);
    } catch (failure) {
      if (number !== request.current) return;
      setScene(null);
      setError(failure instanceof Error ? failure.message : "The fixture could not be loaded.");
    } finally {
      if (number === request.current) setBusy(false);
    }
  }, [transport]);

  useEffect(() => {
    if (transport.choices.length > 0) void load(initial);
    return () => { request.current += 1; };
  }, [transport, load, initial]);
  useEffect(() => {
    if (scene && !busy && focusAfterLoad.current) {
      heading.current?.focus();
      focusAfterLoad.current = false;
    }
  }, [scene, busy]);

  function inspect(recordId?: string) {
    setDrawer({ opener: document.activeElement instanceof HTMLElement ? document.activeElement : null, recordId });
  }
  async function act(actionId: string) {
    if (!scene || busy) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const number = ++request.current;
    setBusy(true); setError(null);
    try {
      const result = await transport.navigate(scene, actionId);
      if (number !== request.current) return;
      if (result.kind === "inspect-records") setDrawer({ opener });
      else {
        setScene(result.scene);
        setSelectedId(result.scene.id);
        focusAfterLoad.current = true;
      }
    } catch (failure) {
      if (number !== request.current) return;
      setScene(null);
      setError(failure instanceof Error ? failure.message : "The fixture action failed.");
    } finally {
      if (number === request.current) setBusy(false);
    }
  }

  return <>
    <div inert={drawer ? true : undefined}>
      <CaseShell choices={transport.choices} selectedId={selectedId} busy={busy} onSceneChange={(id) => void load(id)}>
        {busy && <p className="loading-note" role="status">Opening an authored snapshot… no workflow is running.</p>}
        {error && <section className="state-panel" role="alert">
          <p className="eyebrow">PREVIEW STOPPED SAFELY</p><h1>Snapshot unavailable.</h1>
          <p>{error}</p><p>No live API was contacted and no success state was substituted.</p>
          <button className="button button-secondary" onClick={() => void load(transport.initialSceneId)}>Reload initial preview</button>
        </section>}
        {!busy && !error && transport.choices.length === 0 && <section className="state-panel">
          <p className="eyebrow">EMPTY PREVIEW</p><h1>No authored snapshots.</h1>
          <p>The fixture catalog is empty. Supply an accepted fixture handoff; there is no live fallback.</p>
        </section>}
        {scene && !error && <>
          <div className="hero-grid">
            <RiskPanel risk={scene.response.operationsRisk} actions={scene.response.allowedActions}
              primaryActionId={scene.primaryActionId} busy={busy} headingRef={heading}
              onAction={(id) => void act(id)} onInspect={() => inspect()} />
            <PromiseCard overview={scene.response} />
          </div>
          <ContinuityGraph graph={scene.response.continuityGraph} onInspect={inspect} />
          <section className="review-boundary" aria-label="Preview completeness">
            <span className="boundary-index" aria-hidden="true">07</span>
            <div><h2>A small preview, an explicit boundary.</h2>
              <p>Review the promise, risk and evidence across seven authored snapshots. Full questions, approval and materialization flows are not implemented here. The current NSP scenario requires a separate V3 contract and fixture handoff.</p>
            </div>
          </section>
        </>}
      </CaseShell>
    </div>
    {drawer && scene && <EvidenceDrawer records={scene.records} selectedRecordId={drawer.recordId}
      opener={drawer.opener} onClose={() => setDrawer(null)} />}
  </>;
}
