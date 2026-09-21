import type { AnalysisRequest, ArchitectureOption, BuildResult, Component, Requirement, ReviewFinding, StudioResult } from "../contracts";
import { BuildConsole } from "./BuildConsole";

export type InspectorTab = "component" | "sources" | "assurance" | "build";
export const dimensionNames: Record<ReviewFinding["dimension"], string> = {
  business: "Business fit", security: "Security", reliability: "Reliability", performance: "Performance",
  cost: "Cost", integration: "Integration", compliance: "Compliance", operations: "Operations", delivery: "Delivery",
};

export function Inspector({ tab, onTab, result, option, component, selectedRequirement, onRequirement, onSource, lens, onLens, build, stale, busy, onBuild, onDownload, previousRequirements, onDesignChange }: {
  tab: InspectorTab;
  onTab: (tab: InspectorTab) => void;
  result: StudioResult | null;
  option: ArchitectureOption | null;
  component: Component | null;
  selectedRequirement: string | null;
  onRequirement: (id: string | null) => void;
  onSource: (id: string) => void;
  lens: ReviewFinding["dimension"] | null;
  onLens: (dimension: ReviewFinding["dimension"] | null) => void;
  build: BuildResult | null;
  stale: boolean;
  busy: "analysis" | "build" | "download" | null;
  onBuild: () => void;
  onDownload: () => void;
  previousRequirements: Requirement[] | null;
  onDesignChange?: (finding: ReviewFinding, intent: NonNullable<AnalysisRequest["designChange"]>["intent"]) => void;
}) {
  const analysis = result?.analysis;
  const activeFinding = analysis?.review.find((finding) => finding.dimension === lens);
  function sourceLinks(ids: string[]) {
    return <div className="st-source-links">{ids.map((id) => <button type="button" key={id} onClick={() => onSource(id)} aria-label={`Open source ${result?.sources.find((source) => source.id === id)?.name ?? id}`}><span aria-hidden="true">↗</span>{result?.sources.find((source) => source.id === id)?.name ?? `${id} (unavailable)`}</button>)}</div>;
  }
  function requirementCard(requirement: Requirement) {
    const previous = previousRequirements?.find((item) => item.id === requirement.id);
    const difference = previousRequirements ? !previous ? "Added" : previous.text !== requirement.text || JSON.stringify(previous.sourceIds) !== JSON.stringify(requirement.sourceIds) ? "Changed" : null : null;
    return <article className={`st-requirement ${selectedRequirement === requirement.id ? "is-selected" : ""}`} key={requirement.id}>
      <button type="button" className="st-requirement-target" aria-label={`Highlight requirement ${requirement.id}: ${requirement.text}`} aria-pressed={selectedRequirement === requirement.id} onClick={() => onRequirement(selectedRequirement === requirement.id ? null : requirement.id)}><code>{requirement.id}</code>{difference && <span className="st-badge">{difference}</span>}<span>{requirement.text}</span></button>
      {sourceLinks(requirement.sourceIds)}
    </article>;
  }
  return <aside className="st-inspector" aria-label="Architecture inspector">
    <div className="st-inspector-tabs" role="tablist" aria-label="Inspector views">
      {(["component", "sources", "assurance", "build"] as const).map((item) => <button type="button" key={item} role="tab" id={`st-tab-${item}`} aria-controls={`st-panel-${item}`} aria-selected={tab === item} onClick={() => onTab(item)}>{item === "component" ? "Inspect" : item.charAt(0).toUpperCase() + item.slice(1)}{item === "assurance" && <span>{analysis?.review.length ?? "—"}</span>}</button>)}
    </div>
    <div className="st-inspector-content" role="tabpanel" id={`st-panel-${tab}`} aria-labelledby={`st-tab-${tab}`}>
      {!result || !analysis || !option ? <div className="st-inspector-empty"><span className="st-inspector-empty-icon" aria-hidden="true">⌖</span><span className="st-overline">EVIDENCE, NOT GUESSWORK</span><h2>A design you can inspect.</h2><p>Select a generated component to trace its purpose back to your source requirements.</p><ul><li><span>01</span>Source-backed requirements</li><li><span>02</span>Independent 9-dimension review</li><li><span>03</span>Real compiler diagnostics</li></ul><small>Nothing is assessed until the model returns a validated result.</small></div> : <>
        {tab === "component" && <>
          <span className="st-overline">COMPONENT INSPECTOR</span>
          {component ? <><div className="st-section-heading"><h2>{component.label}</h2><span className="st-badge">{component.kind}</span></div><p className="st-service-name">{component.service}</p><p>{component.responsibility}</p>
            {component.kind === "external" && <div className="st-boundary">External boundary. This existing system is not provisioned by the generated Azure infrastructure.</div>}
            {component.kind === "external" && component.externalDependency && <div className="st-requirement">
              <strong>Existing integration: {component.externalDependency.name}</strong>
              <p>{component.externalDependency.quote}</p>
              {sourceLinks([component.externalDependency.sourceId])}
            </div>}
            <h3>Connected requirements <span className="st-muted">/ {component.requirementIds.length}</span></h3>
            {analysis.requirements.filter((requirement) => component.requirementIds.includes(requirement.id)).map(requirementCard)}
          </> : <p>Select a node on the canvas to inspect its responsibility and source-linked requirements.</p>}
          <details className="st-details" open><summary>Why this alternative</summary><p>{option.rationale}</p><h3>Trade-offs</h3><ul>{option.tradeoffs.map((tradeoff, index) => <li key={index}>{tradeoff}</li>)}</ul><h3>Cost notes · model assessment</h3><p>{option.costNotes}</p><small>Not a priced quote or measured usage estimate.</small></details>
        </>}
        {tab === "sources" && <>
          <span className="st-overline">REQUIREMENTS & PROVENANCE</span><h2>Follow the evidence.</h2><p>Click a requirement to highlight only components with a model-supplied requirement link.</p>
          {selectedRequirement && <button type="button" className="st-text-button" onClick={() => onRequirement(null)}>Clear requirement highlight</button>}
          {analysis.requirements.map(requirementCard)}
          {previousRequirements && previousRequirements.filter((item) => !analysis.requirements.some((requirement) => requirement.id === item.id)).map((item) => <div className="st-requirement st-removed" key={item.id}><span className="st-badge">Removed</span><code>{item.id}</code><p>{item.text}</p></div>)}
          <details className="st-details"><summary>Inferred business process</summary><ol>{analysis.businessProcess.map((step, index) => <li key={index}>{step}</li>)}</ol></details>
          <details className="st-details"><summary>Assumptions ({analysis.assumptions.length}) & open questions ({analysis.questions.length})</summary><ul>{analysis.assumptions.map((assumption, index) => <li key={index}>{assumption}</li>)}</ul>{analysis.questions.map((question) => <div key={question.id}><h3>{question.question}</h3><p>{question.why}</p></div>)}{!analysis.assumptions.length && !analysis.questions.length && <p>None supplied by the model. This is not evidence that there are no unknowns.</p>}</details>
          <details className="st-details"><summary>{result.origin === "simulated" ? "Simulation records & input identity" : "Model receipts & input identity"}</summary><code className="st-hash">Result: {result.resultId}<br />Input hash: {result.inputHash}</code>{result.modelReceipts.map((receipt) => <dl className="st-facts" key={receipt.role}><div><dt>Role</dt><dd>{receipt.role}</dd></div><div><dt>{result.origin === "simulated" ? "Simulator" : "Model"}</dt><dd>{receipt.model || "Unavailable"}</dd></div><div><dt>Response</dt><dd className="st-hash">{receipt.responseId}</dd></div><div><dt>Duration</dt><dd>{(receipt.durationMs / 1000).toFixed(1)} s</dd></div></dl>)}<p>{result.origin === "simulated" ? "Origin: simulated. These are local simulation records, not Foundry response receipts or independent AI evidence." : "Origin: live-model. Receipts record model responses, not correctness or production approval."}</p></details>
        </>}
        {tab === "assurance" && <>
          <span className="st-overline">{result.origin === "simulated" ? "SCRIPTED REVIEW / 09 LENSES" : "INDEPENDENT MODEL REVIEW / 09 LENSES"}</span><h2>Challenge the design.</h2><p>{result.origin === "simulated" ? "Authored example findings for the judge walkthrough, not an independent AI review or compliance certification." : "An independent model pass, not human sign-off or compliance certification."}</p>
          <div className="st-lens-grid" role="group" aria-label="Nine assurance dimensions">{analysis.review.map((finding) => <button type="button" key={finding.dimension} className={`st-lens st-severity-${finding.severity}`} aria-label={`Review ${dimensionNames[finding.dimension]}: ${finding.severity}`} aria-pressed={lens === finding.dimension} onClick={() => onLens(lens === finding.dimension ? null : finding.dimension)}><span className="st-severity-dot" /><strong>{dimensionNames[finding.dimension]}</strong><small>{finding.severity}</small></button>)}</div>
          <div className="st-boundary">Review findings cite sources, but this response has no dimension-to-component links. No graph-node impact is inferred from a review lens.</div>
          {stale && onDesignChange && <p className="st-warning">This result is not current. Regenerate from your edited input or reopen the saved result before requesting a finding change.</p>}
          {(activeFinding ? [activeFinding] : analysis.review).map((finding) => <article className="st-finding" key={finding.dimension}><div className="st-section-heading"><h3>{dimensionNames[finding.dimension]}</h3><span className={`st-badge st-badge-${finding.severity}`}>{finding.severity}</span></div>
            {onDesignChange && <div className="st-finding-actions">
              <button type="button" className="st-primary" disabled={stale || !!busy} onClick={() => onDesignChange(finding, "recommendation")}>Request recommended change</button>
              <button type="button" className="st-secondary" disabled={stale || !!busy} onClick={() => onDesignChange(finding, "challenge")}>Challenge finding</button>
              <small>{result.origin === "simulated" ? "Review the instruction before a scripted revision. No model call or risk waiver." : "Review and approve the instruction before a new model run. No blocker is waived."}</small>
            </div>}
            <p>{finding.finding}</p><h4>Recommended action</h4><p>{finding.recommendation}</p>{sourceLinks(finding.sourceIds)}
          </article>)}
        </>}
        {tab === "build" && <BuildConsole option={option} resultId={result.resultId} build={build} stale={stale} busy={busy} onBuild={onBuild} onDownload={onDownload} review={analysis.review} />}
      </>}
    </div>
  </aside>;
}
