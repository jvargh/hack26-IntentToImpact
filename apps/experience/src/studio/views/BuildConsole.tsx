import { useEffect, useState } from "react";
import type { ArchitectureOption, BuildResult, ReviewFinding } from "../contracts";
import { DeploymentPanel } from "./DeploymentPanel";

export function BuildConsole({ option, resultId, build, stale, busy, onBuild, onDownload, review = [] }: {
  option: ArchitectureOption;
  resultId: string;
  build: BuildResult | null;
  stale: boolean;
  busy: "analysis" | "build" | "download" | null;
  onBuild: () => void;
  onDownload: () => void;
  review?: ReviewFinding[];
}) {
  const [confirmed, setConfirmed] = useState(false);
  const [filePath, setFilePath] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  const [deploymentOpen, setDeploymentOpen] = useState(false);
  const relevant = build?.resultId === resultId && build.optionId === option.id;
  const current = relevant ? build : null;
  const file = current?.files.find((item) => item.path === filePath) ?? current?.files[0];
  useEffect(() => { setConfirmed(false); setCopyStatus(""); }, [resultId, option.id]);
  useEffect(() => { setDeploymentOpen(false); }, [resultId, option.id, build?.buildId, stale]);
  async function copy() {
    if (!file) return;
    try {
      if (!navigator.clipboard) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(file.content);
      setCopyStatus("Copied file contents.");
    } catch { setCopyStatus("Copy unavailable. Select and copy the preview text instead."); }
  }
  return <section className="st-build-console" aria-label="Build console">
    <div className="st-section-heading"><span className="st-overline">INFRASTRUCTURE PACKAGE</span><span className="st-badge st-badge-warning">NOT DEPLOYED</span></div>
    <h2>From design to files.</h2><p>Generate infrastructure for <strong>{option.name}</strong>, then run the actual Bicep compiler on the server.</p>
    <div className="st-boundary">This is infrastructure output, not a generated business application. Compilation is not deployment validation or authorization.</div>
    {stale && <p className="st-warning">The displayed design is a previous result. Regenerate your architecture before building.</p>}
    {build && !relevant && <p className="st-warning">Previous package belongs to another result or alternative. Generate a package for this selection.</p>}
    <label className="st-check"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} disabled={!!busy || stale} />I confirm package generation only. Do not deploy Azure resources.</label>
    <button type="button" className={`${current?.status === "compiled" ? "st-secondary" : "st-primary"} st-wide`} onClick={onBuild} disabled={!confirmed || !!busy || stale}>{busy === "build" ? "Generating & compiling…" : current ? "Regenerate deployment package" : "Generate deployment package"}<span aria-hidden="true">↗</span></button>
    {current && <div className="st-build-output">
      <div className="st-build-status"><span className={`st-badge st-badge-${current.status === "compiled" ? "info" : "blocker"}`}>{current.status === "compiled" ? "COMPILED" : current.status.toUpperCase()}</span><code>{current.buildId}</code></div>
      <dl className="st-facts"><div><dt>Compiler</dt><dd>{current.compilerVersion ?? "Unavailable / not run"}</dd></div><div><dt>Exit code</dt><dd>{current.exitCode ?? "Unavailable / not run"}</dd></div><div><dt>Deployment</dt><dd>Not deployed</dd></div></dl>
      {current.status === "compiled" && current.exitCode === 0 && current.downloadUrl && !stale && <button type="button" className="st-download st-wide" disabled={!!busy} onClick={onDownload}>{busy === "download" ? "Downloading…" : "Download compiled ZIP"}<span aria-hidden="true">↓</span></button>}
      {current.status === "compiled" && !stale && <><button type="button" className="st-secondary st-wide st-deploy-button" disabled={!!busy} onClick={() => setDeploymentOpen(true)}>Deploy to Azure</button>
        <p className="st-input-note">Guided portal handoff. No resources are created by this button.</p></>}
      <h3>Compiler diagnostics</h3><pre className="st-diagnostics">{current.diagnostics || "No compiler diagnostics were supplied."}</pre>
      <h3>Boundaries & limitations</h3>{current.limitations.length ? <ul>{current.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}</ul> : <p>No additional limitations supplied. Application behavior and deployed resources have not been verified.</p>}
      <h3>Generated files <span className="st-muted">/ {current.files.length}</span></h3>
      {current.files.length ? <><div className="st-file-tabs" role="group" aria-label="Generated files">{current.files.map((item) => <button type="button" key={item.path} aria-pressed={file?.path === item.path} onClick={() => { setFilePath(item.path); setCopyStatus(""); }}><span aria-hidden="true">⌑</span>{item.path}</button>)}</div>
        {file && <div className="st-code-panel"><header><code>{file.path}</code><button type="button" onClick={() => { void copy(); }}>Copy file</button></header><pre tabIndex={0} aria-label={`Preview ${file.path}`}><code>{file.content.split("\n").map((line, index) => <span className="st-code-line" key={index}><span className="st-line-number" aria-hidden="true">{index + 1}</span><span>{line || "\u00a0"}</span>{"\n"}</span>)}</code></pre><details><summary>SHA-256</summary><code className="st-hash">{file.sha256}</code></details><p role="status">{copyStatus}</p></div>}
      </> : <p>No generated files returned.</p>}
      {current.status !== "compiled" && <p className="st-warning">No compiled ZIP is available. Review the diagnostics, adjust the design if needed, and retry generation.</p>}
    </div>}
    {deploymentOpen && current?.status === "compiled" && !stale && !busy && <DeploymentPanel key={current.buildId} build={current} review={review} onClose={() => setDeploymentOpen(false)} />}
  </section>;
}
