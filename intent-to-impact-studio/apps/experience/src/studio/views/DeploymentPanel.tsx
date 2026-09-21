import { useEffect, useState } from "react";
import type { BuildResult, ReviewFinding } from "../contracts";
import { AZURE_PORTAL_DEPLOY_URL, AZURE_PORTAL_GUIDE_URL, prepareDeploymentHandoff } from "../deployment";
import type { DeploymentHandoff } from "../deployment";
import { StudioDrawer } from "./SourceDrawer";

export function DeploymentPanel({ build, review, onClose }: { build: BuildResult; review: ReviewFinding[]; onClose: () => void }) {
  const [handoff, setHandoff] = useState<DeploymentHandoff | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  useEffect(() => {
    let active = true;
    prepareDeploymentHandoff(build).then((value) => { if (active) setHandoff(value); })
      .catch((failure: unknown) => { if (active) setError(failure instanceof Error ? failure.message : "Deployment handoff validation failed."); });
    return () => { active = false; };
  }, [build]);
  function download(kind: "template" | "parameters") {
    if (!handoff) return;
    const file = handoff[kind];
    const url = URL.createObjectURL(new Blob([file.content], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `${build.buildId}-${file.path}`;
    document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setNotice(`${file.path} handed to the browser for download. No file has been uploaded to Azure.`);
  }
  const blockers = review.filter((finding) => finding.severity === "blocker");
  return <StudioDrawer title="Deploy to Azure" eyebrow="GUIDED PORTAL HANDOFF / NOT DEPLOYED" closeLabel="Close Azure deployment" variant="change" onClose={onClose}>
    <p>This prepares your exact compiled template for manual Azure Portal deployment. It does not create resources, submit a deployment, or report Azure success.</p>
    <code className="st-hash">Result: {build.resultId}<br />Option: {build.optionId}<br />Build: {build.buildId}</code>
    {blockers.length > 0 && <div className="st-warning">
      <strong>{blockers.length} unresolved design blocker{blockers.length === 1 ? "" : "s"}</strong>
      <ul>{blockers.map((finding) => <li key={finding.dimension}><strong>{finding.dimension}</strong>: {finding.finding}</li>)}</ul>
      <p>Do not select Create until these issues are resolved and the target deployment is authorized. Exporting files is not a risk waiver.</p>
    </div>}
    {error ? <p role="alert" className="st-error">{error}</p> : !handoff ? <p role="status">Checking compiled JSON and recorded file hashes...</p> : <>
      <p className="st-notice">Compiled template and parameter-file SHA-256 checks passed. Azure policy, quota, permissions, pricing and target parameters have not been validated.</p>
      <h3>1 / Download the exact compiled files</h3>
      <div className="st-change-actions"><button type="button" onClick={() => download("template")}>Download ARM template</button>
        <button type="button" onClick={() => download("parameters")}>Download parameter file</button></div>
      {notice && <p role="status">{notice}</p>}
      <h3>2 / Gather target and existing integration values</h3>
      <p>Choose your approved subscription, resource group and region in Azure Portal. Confirm the expected cost, resource inventory and deployment permissions first. No target is preselected here.</p>
      <ul className="st-deploy-parameters">{handoff.fields.map((field) => <li key={field.name}>
        <code>{field.name}</code> <span className="st-badge">{field.required ? "REQUIRED" : "HAS DEFAULT"}</span>
        <p>{field.description || `Azure template parameter (${field.type}).`}</p>
      </li>)}</ul>
      <p className="st-warning">Required Entra registrations and external endpoints are not fabricated. Public-network policies may reject this catalog. Application handlers and callback security remain separate implementation work. Resources are billable if created.</p>
      <h3>3 / Review and create in Azure Portal</h3>
      <ol>
        <li>Open the portal below and sign in to your approved tenant.</li>
        <li>Select <strong>Build your own template in the editor</strong>. Load the downloaded ARM template (or paste its JSON), then Save.</li>
        <li>Enter the target and all required parameter values. Do not use sample IDs or credentials embedded in URLs.</li>
        <li>Select <strong>Review + create</strong>. Resolve validation errors and review resources/costs. Only an authorized person should select <strong>Create</strong>.</li>
        <li>Inspect deployment operations and resource state in Azure. A portal success still does not prove application behavior.</li>
      </ol>
      <label className="st-check"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />
        I understand this is a manual handoff, not deployment approval; I must validate the target, resolve blockers and approve billable resources separately.</label>
      {acknowledged ? <a className="st-portal-link" href={AZURE_PORTAL_DEPLOY_URL} target="_blank" rel="noopener noreferrer">Open Azure Portal deployment</a>
        : <button type="button" className="st-wide" disabled>Open Azure Portal deployment</button>}
      <p><a href={AZURE_PORTAL_GUIDE_URL} target="_blank" rel="noopener noreferrer">Microsoft instructions for custom template deployment</a></p>
      <p className="st-input-note">The template is not hosted publicly or sent to Azure by this studio. You choose when to upload it. Portal deployment is not tracked in Run history; this package remains not-deployed in the local record.</p>
    </>}
  </StudioDrawer>;
}
