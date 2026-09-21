import { useId, useState } from "react";
import type { AnalysisRequest, ArchitectureOption, ReviewFinding, StudioJob } from "../contracts";
import { dimensionNames } from "./Inspector";
import { StudioDrawer } from "./SourceDrawer";

export type ChangeIntent = NonNullable<AnalysisRequest["designChange"]>["intent"];

export function DesignChangeDrawer({ finding, option, intent, busy, current, error, onApprove, onClose, simulated = false }: {
  finding: ReviewFinding; option: ArchitectureOption; intent: ChangeIntent;
  busy: boolean; current: boolean; error: string;
  onApprove: (instruction: string) => void; onClose: () => void;
  simulated?: boolean;
}) {
  const instructionId = useId();
  const [instruction, setInstruction] = useState(intent === "recommendation" ? finding.recommendation : "");
  const [consent, setConsent] = useState(false);
  return <StudioDrawer title={intent === "recommendation" ? "Approve a design change" : "Challenge this finding"}
    eyebrow={`${dimensionNames[finding.dimension].toUpperCase()} / REVISE, THEN REASSESS`}
    closeLabel="Close design change" variant="change" onClose={onClose}>
    <ol className="st-change-steps" aria-label="Design change workflow">
      <li><span>01</span>Review instruction</li><li><span>02</span>Approve & regenerate</li><li><span>03</span>Re-run assurance</li>
    </ol>
    <div className="st-change-context">
      <span className={`st-badge st-badge-${finding.severity}`}>{finding.severity}</span>
      <h3>{dimensionNames[finding.dimension]} finding</h3><p>{finding.finding}</p>
      <h4>Recommended action</h4><p>{finding.recommendation}</p>
      <p><strong>Target alternative:</strong> {option.name}</p>
      <small>Findings review the whole proposal. This request directs a change to the selected alternative; it does not infer component impact.</small>
    </div>
    <form onSubmit={(event) => { event.preventDefault(); if (consent && current && !busy && instruction.trim().length >= 10) onApprove(instruction.trim()); }}>
      <label className="st-label" htmlFor={instructionId}>{intent === "recommendation" ? "Design change instruction" : "Your challenge and proposed correction"}</label>
      <textarea id={instructionId} rows={6} maxLength={2000} minLength={10} required disabled={busy}
        value={instruction} onChange={(event) => { setInstruction(event.target.value); setConsent(false); }}
        placeholder="Explain what is incorrect, cite supporting evidence, and describe the design correction you want." />
      <small>{instruction.length}/2000 characters. The server includes the exact finding and selected alternative with your instruction.</small>
      <p className="st-warning">Approval authorizes a new design proposal, not a risk waiver. The original blocker stays on the original revision. The new assurance review may still report a blocker.</p>
      <label className="st-check"><input type="checkbox" checked={consent} disabled={busy}
        onChange={(event) => setConsent(event.target.checked)} />{simulated ? "I approve this scripted demonstration revision. My instruction is recorded, not interpreted by AI; no Foundry call is made." : "I approve this revision request and consent to send the original sources and this instruction to Microsoft Foundry for synthesis and a separate assurance review."}</label>
      <p className="st-input-note">{simulated ? "Judge simulation: no model charges. This produces an authored example change and scripted review, not a general response to your instruction. Records persist in this browser session's server history." : "Two model calls may incur charges. Approval and results are stored unencrypted locally under demo-human (not a verified production identity). No application code is implemented or Azure resources deployed by this action."}</p>
      {!current && !busy && <p className="st-warning" role="alert">The working design or input changed. Close this panel and reopen the finding on the current result before approving.</p>}
      {error && <p className="st-error" role="alert">{error}</p>}
      {busy && <p role="status">Regenerating the architecture and re-running independent assurance. Closing this panel does not cancel the server job.</p>}
      <div className="st-change-actions"><button type="button" className="st-secondary" onClick={onClose}>{busy ? "Hide progress" : "Cancel"}</button>
        <button type="submit" className="st-primary" disabled={busy || !current || !consent || instruction.trim().length < 10}>
          {busy ? "Regenerating..." : "Approve & regenerate"}
        </button></div>
    </form>
  </StudioDrawer>;
}

export function DesignChangeOutcome({ job }: { job: StudioJob }) {
  const approval = job.changeApproval;
  if (!approval) return null;
  const simulated = job.result?.origin === "simulated";
  const latest = job.result?.analysis.review.find((finding) => finding.dimension === approval.finding.dimension);
  const outcome = job.status === "failed" ? "Revision failed; original unchanged"
    : latest?.severity === "blocker" ? "Blocker remains in revised design"
      : latest ? `Latest ${simulated ? "scripted" : "AI"} review: ${latest.severity}` : "Revision and re-review pending";
  return <details className="st-change-outcome">
    <summary><span className="st-overline">APPROVED REVISION REQUEST / {dimensionNames[approval.finding.dimension].toUpperCase()}</span>
      <strong>{outcome}</strong><span>View change & decision record</span></summary>
    <dl className="st-facts">
      <div><dt>Before</dt><dd>{approval.finding.severity}</dd></div>
      <div><dt>After</dt><dd>{latest?.severity ?? "No new reviewed result"}</dd></div>
      <div><dt>Approved by</dt><dd>{approval.actor} · local demo identity</dd></div>
      <div><dt>Approved at</dt><dd>{new Date(approval.approvedAt).toLocaleString()}</dd></div>
      <div><dt>Parent result</dt><dd className="st-hash">{approval.baseResultId}</dd></div>
      <div><dt>Parent hash</dt><dd className="st-hash">{approval.baseResultHash}</dd></div>
      <div><dt>Target option</dt><dd>{approval.optionId}</dd></div>
      <div><dt>Action</dt><dd>{approval.intent === "challenge" ? "Challenge finding" : "Request recommended change"}</dd></div>
    </dl>
    <h4>Approved instruction</h4><p className="st-verbatim">{approval.instruction}</p>
    <h4>Original finding</h4><p>{approval.finding.finding}</p>
    {latest && <><h4>{simulated ? "Latest scripted finding" : "Latest independent model finding"}</h4><p>{latest.finding}</p>
      <h4>{simulated ? "Simulated change summary" : "Model change summary"}</h4><p>{job.result?.analysis.changeSummary}</p>
      {!job.result?.analysis.options.some((option) => option.id === approval.optionId) && <p className="st-warning">The model did not retain the target alternative ID. Inspect the revised alternatives before generating a package.</p>}</>}
    <p className="st-input-note">{simulated ? "This is a scripted simulation, not AI reasoning or verified resolution. The instruction is recorded for the workflow demonstration; approval is not risk acceptance." : "Approval was permission to revise, not sign-off on the resulting design. A changed severity is an AI assessment, not verified resolution. Review the new proposal before separately generating its infrastructure package."}</p>
  </details>;
}
