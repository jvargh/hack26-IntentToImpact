import { useEffect, useRef, useState } from "react";
import type { RunHistory, SavedRun } from "../contracts";
import type { StudioClient } from "../client";
import { StudioDrawer } from "./SourceDrawer";
import { DesignChangeOutcome } from "./DesignChange";

export type HistoryClient = Pick<StudioClient, "history" | "historyRun" | "historyBuild" | "downloadRun" | "download">;

function date(value: string) {
  return value && Number.isFinite(Date.parse(value)) ? new Date(value).toLocaleString() : "Time unavailable";
}
function errorText(error: unknown) {
  return error instanceof Error ? error.message : "Saved history could not be loaded.";
}

export function RunHistoryPanel({ client, workingCopyHasContent, working, onOpen, onClose }: {
  client: HistoryClient; workingCopyHasContent: boolean; working: boolean;
  onOpen: (run: SavedRun) => void; onClose: () => void;
}) {
  const [history, setHistory] = useState<RunHistory | null>(null);
  const [selected, setSelected] = useState("");
  const [run, setRun] = useState<SavedRun | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const downloads = useRef(new Set<AbortController>());
  const urls = useRef(new Map<string, ReturnType<typeof setTimeout>>());
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    const controllers = downloads.current;
    const activeUrls = urls.current;
    return () => {
      mounted.current = false;
      controllers.forEach((controller) => controller.abort());
      activeUrls.forEach((timer, url) => { clearTimeout(timer); URL.revokeObjectURL(url); });
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(""); setHistory(null); setRun(null); setSelected("");
    client.history(controller.signal).then((value) => {
      if (!controller.signal.aborted) { setHistory(value); setSelected(value.runs[0]?.jobId ?? ""); }
    }).catch((failure: unknown) => { if (!controller.signal.aborted) setError(errorText(failure)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [client, attempt]);
  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    setRun(null); setError(""); setConfirmOpen(false);
    client.historyRun(selected, controller.signal).then((value) => {
      if (!controller.signal.aborted) setRun(value);
    }).catch((failure: unknown) => { if (!controller.signal.aborted) setError(errorText(failure)); });
    return () => controller.abort();
  }, [client, selected, attempt]);

  async function download(buildId?: string) {
    if (!run || downloading) return;
    const controller = new AbortController();
    downloads.current.add(controller);
    setDownloading(true); setError(""); setNotice("");
    try {
      const blob = buildId
        ? await client.download(await client.historyBuild(run.summary.jobId, buildId, controller.signal), controller.signal)
        : await client.downloadRun(run.summary.jobId, controller.signal);
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = buildId ? `studio-${buildId}.zip` : `studio-run-${run.summary.jobId}.zip`;
      document.body.append(anchor);
      anchor.click(); anchor.remove();
      urls.current.set(url, setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url); }, 1000));
      setNotice(buildId ? "Saved infrastructure package downloaded. No new build or deployment ran." : "Run record downloaded, including original input and document text.");
    } catch (failure) { if (!controller.signal.aborted) setError(errorText(failure)); }
    finally {
      downloads.current.delete(controller);
      if (mounted.current) setDownloading(false);
    }
  }

  return <StudioDrawer title="Run history" eyebrow="SAVED RUNS / LOCAL STORAGE" closeLabel="Close run history" variant="history" onClose={onClose}>
    <p>{history?.scope === "workspace"
      ? "Shared local workspace: includes runs from earlier browser sessions. Anyone using this studio can view these inputs, documents and results."
      : "Saved runs available to this session. Reopening a run makes no model call."}</p>
    <button type="button" className="st-secondary" onClick={() => setAttempt((value) => value + 1)} disabled={loading || downloading}>Refresh history</button>
    {error && <p className="st-error" role="alert">{error}</p>}
    {notice && <p className="st-notice" role="status">{notice}</p>}
    {loading && <p role="status">Loading saved runs...</p>}
    {history && history.runs.length === 0 && <p>No saved runs yet. Generated and failed runs will appear here automatically.</p>}
    {!!history?.runs.length && <>
      <label className="st-label" htmlFor="st-saved-run">Earlier runs · {history.runs.length}</label>
      <select id="st-saved-run" className="st-history-select" value={selected} onChange={(event) => setSelected(event.target.value)}>
        {history.runs.map((item) => <option key={item.jobId} value={item.jobId}>
          {item.title} · {item.status} · {date(item.createdAt)} · {item.jobId.slice(-6)}
        </option>)}
      </select>
      {!run && !error && <p role="status">Loading the selected run...</p>}
    </>}
    {run && <div className="st-history-detail">
      <div className="st-section-heading"><h3>{run.summary.title}</h3><span className="st-badge">{run.summary.status}</span></div>
      <dl className="st-facts">
        <div><dt>Started</dt><dd>{date(run.summary.createdAt)}</dd></div>
        <div><dt>Updated</dt><dd>{date(run.summary.updatedAt)}</dd></div>
        <div><dt>Documents</dt><dd>{run.summary.documentCount}</dd></div>
        <div><dt>Compiled packages</dt><dd>{run.summary.compiledPackageCount}</dd></div>
      </dl>
      <code className="st-hash">{run.summary.jobId}</code>
      {run.summary.previousResultId && <p className="st-muted">Revision of <code>{run.summary.previousResultId}</code></p>}
      <h3>Original intent</h3><p>{run.inputs.prompt}</p>
      <DesignChangeOutcome job={run.job} />
      {run.inputs.refinement && <><h3>Refinement</h3><p>{run.inputs.refinement}</p></>}
      {run.job.error && <p className="st-warning">Saved failure: {run.job.error.message}</p>}
      {working && <p className="st-warning">Finish or stop waiting for the current operation before opening another run.</p>}
      {confirmOpen ? <div className="st-boundary">
        <strong>Replace the current working view?</strong>
        <p>Unsaved edits in this tab will be replaced. Saved runs are unchanged. No AI call or deployment will start.</p>
        <div className="st-history-actions"><button className="st-secondary" onClick={() => setConfirmOpen(false)}>Cancel</button>
          <button className="st-primary" onClick={() => onOpen(run)} disabled={working || downloading}>Open saved run</button></div>
      </div> : <button className="st-primary st-wide" disabled={working || downloading} onClick={() => workingCopyHasContent ? setConfirmOpen(true) : onOpen(run)}>Open this run</button>}
      <h3>Download records</h3>
      <p className="st-input-note">The run ZIP contains original prompts and document text, outcomes and activity. It excludes session cookies and authentication tokens.</p>
      <button className="st-secondary st-wide" disabled={downloading} onClick={() => { void download(); }}>Download run record ZIP</button>
      <h3>Saved infrastructure packages</h3>
      {run.builds.length === 0 ? <p>No package was generated for this run.</p> : <ul className="st-history-builds">
        {run.builds.map((item) => <li key={item.buildId}>
          <strong>{run.job.result?.analysis.options.find((option) => option.id === item.optionId)?.name ?? item.optionId}</strong>
          <span className="st-badge">{item.status}</span><small>{item.compilerVersion ?? "Compiler not run"} · exit {item.exitCode ?? "not run"}</small>
          {item.status === "compiled" && <button className="st-download st-wide" disabled={downloading} onClick={() => { void download(item.buildId); }}>Download saved package</button>}
        </li>)}
      </ul>}
    </div>}
  </StudioDrawer>;
}
