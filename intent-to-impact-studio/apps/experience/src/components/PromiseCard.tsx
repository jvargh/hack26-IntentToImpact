import type { ExperienceOverview } from "@contracts/projections";
import { StatusBadge, statusTone } from "./StatusBadge";

export function PromiseCard({ overview }: { overview: ExperienceOverview }) {
  return <aside className="promise-card" aria-labelledby="promise-title">
    <p className="eyebrow">THE CUSTOMER PROMISE</p>
    <h2 id="promise-title">Protected claims.<br />Explicit evidence.</h2>
    <p className="business-goal">{overview.businessGoal}</p>
    <div className="assurance-note">
      <span className="small-label">Historical V2 scope</span>
      <p>Public-endpoint configuration assurance. Not complete access-control assurance, and not current NSP proof.</p>
    </div>
    <details className="coverage-detail">
      <summary>All eight promise states</summary>
      <p className="muted">
        {overview.coverage.verifiedCount === null || overview.coverage.applicableCount === null
          ? "Coverage counts are not assessed."
          : `${overview.coverage.verifiedCount} / ${overview.coverage.applicableCount} — producer-supplied fixture counts.`}
      </p>
      <ul className="promise-rows">
        {overview.coverage.rows.map((row) => <li key={row.promiseId}>
          <span><strong>{row.promiseId}</strong><small>{row.confirmed ? "Scripted confirmation" : "Unconfirmed"}</small></span>
          <StatusBadge label={row.status === "verified" ? "Fixture verified" : row.status} tone={statusTone(row.status)} />
        </li>)}
      </ul>
      <p className="fine-print">Confirmations here are authored examples, not actual human decisions. RPO remains unconfirmed.</p>
    </details>
  </aside>;
}
