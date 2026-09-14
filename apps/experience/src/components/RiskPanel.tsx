import type { Ref } from "react";
import type { AllowedAction, OperationsRisk } from "@contracts/projections";
import { StatusBadge, statusTone, formatTime } from "./StatusBadge";

interface RiskPanelProps {
  risk: OperationsRisk;
  actions: readonly AllowedAction[];
  primaryActionId: string;
  busy: boolean;
  headingRef?: Ref<HTMLHeadingElement>;
  onAction(id: string): void;
  onInspect(): void;
}
const restorationLabels: Readonly<Record<OperationsRisk["restoration"]["status"], string>> = {
  "not-requested": "Restoration not requested",
  prepared: "Correction prepared",
  "awaiting-operator": "Awaiting operator",
  "verification-pending": "Verification pending",
  verified: "Fixture verification only",
  blocked: "Restoration blocked",
};
const riskLabels: Readonly<Record<OperationsRisk["riskState"], string>> = {
  "known-risk": "Promise at risk",
  unknown: "Assurance unknown",
  "restoration-pending": "Restoration pending",
  "no-known-risk": "No known risk in this fixture",
};

export function RiskPanel({ risk, actions, primaryActionId, busy, headingRef, onAction, onInspect }: RiskPanelProps) {
  return <section className="risk-panel" data-risk-state={risk.riskState} aria-labelledby="scene-title">
    <div className="scene-status">
      <StatusBadge label={riskLabels[risk.riskState]} tone={statusTone(risk.riskState)} />
      <span className="origin-note">Fixture evidence · {formatTime(risk.asOf)}</span>
    </div>
    <h1 id="scene-title" ref={headingRef} tabIndex={-1}>{risk.headline}</h1>
    <p className="customer-impact">{risk.customerImpact}</p>
    <div className="restoration-line">
      <span className="small-label">RESTORATION</span>
      <StatusBadge label={restorationLabels[risk.restoration.status]} tone={statusTone(risk.restoration.status)} />
    </div>
    <p className="scope-reminder">Prepared or materialized files are not runtime verification. All displayed outcomes are historical fixture examples.</p>
    <div className="action-row">
      {actions.map((action) => <button key={action.actionId}
        className={action.actionId === primaryActionId ? "button button-primary" : "button button-secondary"}
        data-primary={action.actionId === primaryActionId ? "true" : undefined}
        data-action-id={action.actionId}
        disabled={busy} onClick={() => onAction(action.actionId)}>
        {action.label}<span aria-hidden="true"> ↗</span>
      </button>)}
      <button className="text-button" disabled={busy} onClick={onInspect}>Inspect evidence <span aria-hidden="true">→</span></button>
    </div>
    <p className="action-disclaimer">These controls browse authored snapshots; they never approve, apply or restore anything.</p>
    {risk.blockers.length > 0 && <details className="limit-detail">
      <summary>Evidence limits &amp; preview boundaries</summary>
      <ul>{risk.blockers.map((blocker) => <li key={blocker.code}>{blocker.message}</li>)}</ul>
    </details>}
  </section>;
}
