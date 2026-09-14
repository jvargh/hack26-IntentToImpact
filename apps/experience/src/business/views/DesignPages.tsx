import { useId } from "react";
import type { ArchitectureOption, BusinessBrief, DesignDraft, ReviewStatus } from "../model";
import { DIMENSIONS, OPTIONS } from "../model";
import { Arrow, PageHeading, SourceLinks } from "./Shared";

interface DraftViewProps {
  draft: DesignDraft;
  onSource: (id: string) => void;
}

const BRIEF_FIELDS: { key: keyof BusinessBrief; title: string; hint: string }[] = [
  { key: "goal", title: "Business outcome", hint: "What should become possible, and how will you know it worked?" },
  { key: "actors", title: "People & responsibilities", hint: "Who participates? Who owns each part of the process?" },
  { key: "process", title: "The process, step by step", hint: "Describe the happy path, hand-offs and what happens when something goes wrong." },
  { key: "systems", title: "Existing systems & integrations", hint: "Which systems own the data? What must remain in place?" },
  { key: "constraints", title: "Non-negotiables & constraints", hint: "Capture data boundaries, business obligations, deadlines and known limits." },
];

export function UnderstandingEditor({ draft, onSource, onBrief, onAnswer, onNext }: DraftViewProps & {
  onBrief: (key: keyof BusinessBrief, value: string) => void; onAnswer: (id: string, answer: string) => void; onNext: () => void;
}) {
  return <>
    <PageHeading eyebrow="02 / Understanding" title="First, get the business right.">
      {draft.kind === "example" ? "An illustrative understanding of the attached order-to-fulfilment documents. Read the sources, then make the brief your own."
        : "Your prompt is copied literally below. Shape the remaining fields yourself—your documents have not been automatically analysed."}
    </PageHeading>
    <div className="wb-two-column">
      <div className="wb-stack">
        <section className="wb-paper">
          <div className="wb-section-top"><h2>Our understanding</h2><span className="wb-tag">{draft.kind === "example" ? "Illustrative example" : "Author review needed"}</span></div>
          <p className="wb-caption">Editable by you. No inferred requirements or hidden assumptions.</p>
          <div className="wb-fields">
            {BRIEF_FIELDS.map((field) => <label className="wb-field" key={field.key}>
              <span>{field.title}</span>
              <textarea rows={field.key === "process" ? 4 : 3} value={draft.brief[field.key]} maxLength={12_000}
                onChange={(event) => onBrief(field.key, event.target.value)} placeholder={field.hint} />
            </label>)}
          </div>
          {draft.kind === "example" && <div className="wb-source-reference"><p className="wb-caption">Example understanding refers to these supplied sources:</p><SourceLinks documents={draft.documents} onOpen={onSource} /></div>}
        </section>
        <section className="wb-paper">
          <p className="wb-eyebrow">Clarifications</p>
          <h2>Good questions make better architecture.</h2>
          <p className="wb-caption">{draft.kind === "example"
            ? "Sample answers are filled in for this walkthrough. Edit them to explore the design; they are illustrative assumptions, not AI-extracted facts or confirmed customer requirements."
            : "A standard starting checklist, not questions extracted by AI. Leave unknowns open."}</p>
          {draft.kind === "example" && <SourceLinks documents={draft.documents} sourceIds={["example-clarifications"]} onOpen={onSource} />}
          <div className="wb-question-list">
            {draft.questions.map((question, index) => <label className="wb-field wb-question" key={question.id}>
              <span><b className="wb-question-number">{String(index + 1).padStart(2, "0")}</b>{question.question}</span>
              <small>{question.reason}</small>
              <textarea rows={2} maxLength={12_000} value={question.answer} onChange={(event) => onAnswer(question.id, event.target.value)} placeholder="Your answer, or leave open for follow-up" />
            </label>)}
          </div>
        </section>
      </div>
      <aside className="wb-source-panel">
        <p className="wb-eyebrow">Keep the context close</p><h2>Source material</h2>
        <div className="wb-source-prompt"><h3>Your original prompt</h3><p>{draft.prompt || "No business prompt entered yet. Return to Your business to add one."}</p></div>
        <h3>Attached documents <span className="wb-count">{draft.documents.length}</span></h3>
        {draft.documents.length === 0 ? <p className="wb-caption">No documents attached. You can work from your prompt or add supporting process notes.</p>
          : draft.documents.map((doc) => <article className="wb-source-excerpt" key={doc.id}>
            <button className="wb-source-link" onClick={() => onSource(doc.id)}>{doc.name} <Arrow /></button>
            <p>{doc.text.slice(0, 240)}{doc.text.length > 240 ? "…" : ""}</p>
            <span className="wb-caption">Literal source excerpt · Open to read or edit</span>
          </article>)}
        <p className="wb-sidebar-note">A source is context—not proof that a design is correct. Resolve the open questions with the people who own the process.</p>
      </aside>
    </div>
    <div className="wb-page-actions"><p className="wb-caption">Unknowns can remain open. Capture them, don’t guess.</p><button className="wb-button wb-primary" onClick={onNext}>Explore architecture <Arrow /></button></div>
  </>;
}

const COORDINATES: Record<string, { x: number; y: number }> = {
  experience: { x: 150, y: 85 }, api: { x: 450, y: 85 }, data: { x: 750, y: 85 },
  queue: { x: 750, y: 265 }, worker: { x: 450, y: 265 }, external: { x: 150, y: 265 },
};

export function ArchitectureDiagram({ option }: { option: ArchitectureOption }) {
  const arrowId = `wb-arrow-${useId().replace(/:/g, "")}`;
  return <div className="wb-diagram-shell">
    <div className="wb-diagram">
      <svg className="wb-diagram-connectors" viewBox="0 0 900 350" preserveAspectRatio="none" aria-hidden="true">
        <defs><marker id={arrowId} markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="currentColor" /></marker></defs>
        {option.flows.map((flow, index) => {
          const start = COORDINATES[flow.from];
          const end = COORDINATES[flow.to];
          if (!start || !end) return null;
          const direction = end.x > start.x ? 1 : -1;
          const down = end.y > start.y ? 1 : -1;
          const path = start.y === end.y
            ? `M${start.x + 126 * direction},${start.y + (index === 5 ? 14 : 0)} L${end.x - 126 * direction},${end.y + (index === 5 ? 14 : 0)}`
            : `M${start.x},${start.y + 62 * down} V175 H${end.x} V${end.y - 62 * down}`;
          return <path key={`${flow.from}-${flow.to}-${index}`} d={path} markerEnd={`url(#${arrowId})`} />;
        })}
      </svg>
      {option.nodes.map((node, index) => <article className="wb-diagram-node" key={node.id}>
        <span className="wb-node-index">{String(index + 1).padStart(2, "0")}</span>
        <h3>{node.title}</h3><p>{node.service}</p><span className="wb-node-detail">{node.responsibility}</span>
        <div className="wb-node-flows">{option.flows.filter((flow) => flow.from === node.id).map((flow, flowIndex) =>
          <span key={flowIndex}>{flow.label} → {option.nodes.find((target) => target.id === flow.to)?.title}</span>)}</div>
      </article>)}
    </div>
    <details className="wb-flow-details"><summary>View connections & responsibilities</summary>
      <ol>{option.flows.map((flow, index) => <li key={index}><strong>{option.nodes.find((node) => node.id === flow.from)?.title}</strong> → <strong>{option.nodes.find((node) => node.id === flow.to)?.title}</strong><span>{flow.label}</span></li>)}</ol>
    </details>
  </div>;
}

export function ArchitectureOptions({ draft, onSource, onSelect, onRationale, onNext }: DraftViewProps & {
  onSelect: (id: string) => void; onRationale: (text: string) => void; onNext: () => void;
}) {
  const option = OPTIONS.find((item) => item.id === draft.selectedOptionId) ?? OPTIONS[0]!;
  return <>
    <PageHeading eyebrow="03 / Architecture" title="A design is a set of choices.">
      Compare three reference patterns. Choose a starting point and document your reasoning—not an automatic recommendation.
    </PageHeading>
    <div className="wb-pattern-grid">
      {OPTIONS.map((item, index) => <article key={item.id} className={`wb-pattern-card${item.id === draft.selectedOptionId ? " wb-selected" : ""}`}>
        <div className="wb-pattern-label"><span className="wb-eyebrow">Pattern {String(index + 1).padStart(2, "0")}</span>{item.id === draft.selectedOptionId && <span className="wb-tag">Selected by you</span>}</div>
        <h2>{item.title}</h2><p className="wb-pattern-subtitle">{item.subtitle}</p>
        <dl><dt>Where it can fit</dt><dd>{item.fit}</dd><dt>What you take on</dt><dd>{item.tradeoff}</dd><dt>Cost drivers—not an estimate</dt><dd>{item.costDriver}</dd></dl>
        <button className="wb-button wb-secondary"
          aria-label={`Use ${item.title}`} aria-pressed={item.id === draft.selectedOptionId} onClick={() => onSelect(item.id)}>
          {item.id === draft.selectedOptionId ? "Selected starting pattern" : "Use this starting pattern"} <span aria-hidden="true">→</span>
        </button>
      </article>)}
    </div>
    <section className="wb-paper wb-architecture-paper">
      <div className="wb-section-top"><div><p className="wb-eyebrow">Logical architecture</p><h2>{option.title}</h2></div>
        <span className="wb-tag">{draft.selectedOptionId ? "Manually selected" : "Preview only · not selected"}</span></div>
      <p className="wb-caption">A six-responsibility reference design. Service labels are candidates, not validated infrastructure or a deployment plan.</p>
      <ArchitectureDiagram option={option} />
      {draft.kind === "example" && <div className="wb-example-reason">
        <h3>An example trade-off to investigate</h3>
        <p>The supplied process allows the warehouse to be offline while orders arrive. Compare each pattern’s buffering and recovery approach against that requirement—not just its service names.</p>
        <SourceLinks documents={draft.documents} sourceIds={["example-process"]} onOpen={onSource} />
      </div>}
      <label className="wb-field wb-rationale"><span id="wb-rationale-label">Your design rationale</span>
        <textarea rows={4} value={draft.designRationale} maxLength={12_000} onChange={(event) => onRationale(event.target.value)}
          aria-labelledby="wb-rationale-label" aria-describedby="wb-rationale-hint" placeholder="Why does this pattern fit your process? Record the source, assumptions, trade-offs and alternatives you considered." />
        <small id="wb-rationale-hint">Changing the starting pattern resets checklist statuses to “Not reviewed.” Existing notes remain for you to reconsider.</small>
      </label>
    </section>
    <div className="wb-page-actions"><p className="wb-caption">You can review the checklist before selecting a pattern.</p><button className="wb-button wb-primary" onClick={onNext}>Open the 360 review <Arrow /></button></div>
  </>;
}

export function Assessment360({ draft, onSource, onReview, onNext }: DraftViewProps & {
  onReview: (id: string, patch: { status?: ReviewStatus; note?: string }) => void; onNext: () => void;
}) {
  const reviewed = DIMENSIONS.filter((item) => draft.reviews[item.id]?.status === "reviewed").length;
  return <>
    <PageHeading eyebrow="04 / 360 review" title="Look beyond the happy path.">
      Nine perspectives on a defensible design. Record evidence, identify unresolved work, and make the next conversation more useful.
    </PageHeading>
    <div className="wb-review-summary"><div><strong>{draft.kind === "example" ? "Illustrative findings, real questions." : "Your project has not been assessed."}</strong>
      <p>{draft.kind === "example" ? "The findings below are written for the supplied example documents. They are not live AI results."
        : "This is a manual review checklist. No findings or recommendations have been generated from your inputs."}</p></div>
      <div className="wb-review-progress"><strong>{reviewed} of {DIMENSIONS.length}</strong><span>marked reviewed by you</span></div>
    </div>
    <p className="wb-caption wb-review-caveat">These statuses record your review activity—not an approval, certification, readiness score or server assessment.</p>
    <div className="wb-review-grid">
      {DIMENSIONS.map((dimension, index) => {
        const review = draft.reviews[dimension.id]!;
        return <article className={`wb-review-card wb-review-${review.status}`} key={dimension.id}>
          <div className="wb-review-card-heading"><span className="wb-eyebrow">{String(index + 1).padStart(2, "0")}</span><span className="wb-tag">{draft.kind === "example" ? "Example finding" : "Not assessed"}</span></div>
          <h2>{dimension.title}</h2><p className="wb-review-question">{dimension.question}</p>
          {draft.kind === "example" ? <div className="wb-findings">
            <h3>What the example surfaces</h3><p>{dimension.finding}</p>
            <h3>A direction to investigate</h3><p>{dimension.recommendation}</p>
            <SourceLinks documents={draft.documents} sourceIds={dimension.sourceIds} onOpen={onSource} />
          </div> : <p className="wb-unassessed">Bring your source evidence and discuss this with the relevant owner. Record what you know—and what you still need to verify.</p>}
          <div className="wb-review-controls">
            <label className="wb-field"><span>Your review status</span>
              <select aria-label={`Review status for ${dimension.title}`} value={review.status} onChange={(event) => onReview(dimension.id, { status: event.target.value as ReviewStatus })}>
                <option value="not-reviewed">Not reviewed</option><option value="needs-work">Needs work</option><option value="reviewed">Reviewed by me</option>
              </select>
            </label>
            <label className="wb-field"><span>Evidence & follow-up notes</span>
              <textarea rows={3} aria-label={`Notes for ${dimension.title}`} maxLength={12_000} value={review.note}
                onChange={(event) => onReview(dimension.id, { note: event.target.value })} placeholder="Evidence, owner, open issue or next action…" />
            </label>
          </div>
        </article>;
      })}
    </div>
    <div className="wb-page-actions"><p className="wb-caption">Unreviewed dimensions remain visible in your exported brief.</p><button className="wb-button wb-primary" onClick={onNext}>Bring it into a design brief <Arrow /></button></div>
  </>;
}

export function DesignBrief({ draft, onSource, onExport, onStep }: DraftViewProps & {
  onExport: () => void; onStep: (step: "understanding" | "architecture" | "assessment") => void;
}) {
  const selected = OPTIONS.find((option) => option.id === draft.selectedOptionId);
  const openQuestions = draft.questions.filter((question) => !question.answer.trim());
  const needsWork = DIMENSIONS.filter((dimension) => draft.reviews[dimension.id]?.status === "needs-work");
  return <>
    <PageHeading eyebrow="05 / Design brief" title="Leave with a clear next conversation.">
      Your intent, design choices and unresolved questions—in one working brief. Take it to the people who can challenge and validate it.
    </PageHeading>
    <div className="wb-two-column wb-handoff-layout">
      <article className="wb-brief-document">
        <div className="wb-brief-masthead"><span className="wb-eyebrow">Architecture design brief</span><span className="wb-tag">{draft.kind === "example" ? "Illustrative worked example" : "User-authored draft"}</span></div>
        <h2>{draft.title || "Your next architecture"}</h2>
        <p className="wb-brief-intent">{draft.prompt || "No business intent entered yet."}</p>
        <section><div className="wb-section-top"><h3>01 / Business understanding</h3><button className="wb-button wb-text" onClick={() => onStep("understanding")}>Edit understanding</button></div>
          <dl className="wb-brief-facts">{BRIEF_FIELDS.map((field) => <div key={field.key}><dt>{field.title}</dt><dd>{draft.brief[field.key] || "Not supplied"}</dd></div>)}</dl>
        </section>
        <section><div className="wb-section-top"><h3>02 / Architecture direction</h3><button className="wb-button wb-text" onClick={() => onStep("architecture")}>Edit architecture</button></div>
          <h4>{selected?.title || "No starting pattern selected"}</h4>
          <p>{selected ? "Manually selected reference pattern. Feasibility and service choices still need validation." : "Compare the reference patterns before recording an architecture direction."}</p>
          <p className="wb-brief-rationale">{draft.designRationale || "Selection rationale not supplied."}</p>
          {selected && <p className="wb-caption"><strong>Trade-off:</strong> {selected.tradeoff}</p>}
        </section>
        <section><h3>03 / Questions to resolve</h3>
          {draft.questions.map((question) => <div className="wb-brief-question" key={question.id}><h4>{question.question}</h4><p>{question.answer || "Open · answer needed from the business owner"}</p></div>)}
        </section>
        <section><div className="wb-section-top"><h3>04 / Your 360 review record</h3><button className="wb-button wb-text" onClick={() => onStep("assessment")}>Edit review</button></div>
          <ul className="wb-review-record">{DIMENSIONS.map((dimension) => {
            const note = draft.reviews[dimension.id]!;
            return <li key={dimension.id}><div><strong>{dimension.title}</strong><span>{note.status === "reviewed" ? "Reviewed by me" : note.status === "needs-work" ? "Needs work" : "Not reviewed"}</span></div>
              {note.note && <p>{note.note}</p>}
            </li>;
          })}</ul>
        </section>
        <section><h3>05 / Source references</h3>
          {draft.documents.length ? <SourceLinks documents={draft.documents} onOpen={onSource} /> : <p>No supporting documents attached.</p>}
          <p className="wb-caption">The Markdown export lists source filenames, but does not include raw document contents.</p>
        </section>
      </article>
      <aside className="wb-stack">
        <section className="wb-export-card">
          <p className="wb-eyebrow">A portable working document</p><h2>Take the brief<br />with you.</h2>
          <p>Download your authored content, selected pattern, logical diagram, review notes and open questions as Markdown.</p>
          <button className="wb-button wb-primary" onClick={onExport}>Download design brief <span aria-hidden="true">↓</span></button>
          <p className="wb-caption">.md file · Includes a Mermaid diagram when a pattern is selected · No infrastructure code</p>
        </section>
        <section className="wb-next-steps"><h2>Before this becomes a build</h2><ul>
          <li>{openQuestions.length ? `Resolve ${openQuestions.length} open clarification${openQuestions.length === 1 ? "" : "s"} with accountable owners.` : "Confirm the supplied answers with accountable owners."}</li>
          <li>{needsWork.length ? `Follow up on ${needsWork.length} review dimension${needsWork.length === 1 ? "" : "s"} marked “Needs work.”` : "Review the evidence and unanswered dimensions."}</li>
          <li>Validate integration contracts, capacity, cost and controls.</li>
          <li>Review the design before generating or deploying infrastructure.</li>
        </ul><p className="wb-caption">This local author review is not an implementation approval. AI analysis and backend validation are not connected.</p></section>
      </aside>
    </div>
  </>;
}
