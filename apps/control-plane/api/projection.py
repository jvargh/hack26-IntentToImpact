"""Initial unknown-risk projection from actual case state, not fixture response snapshots."""

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from reporting.continuity.graph import build_graph
from tools.contracts.integrity import (
    scenario_identity, semantic_checksum, validate_reference_integrity,
)
from tools.contracts.validate import validate_contract


def issue_context_action(case, scenario):
    return f"acknowledge-context-r{case['logicalRevision']}-{scenario['stateChecksum'][7:19]}"


def initial_overview(case, run, scenario, *, can_acknowledge):
    identity = scenario_identity(scenario)
    acknowledged = "api-context-ack" in case["sections"]
    blockers = [
        {"code": "historical-scenario",
         "message": "Historical V2 scenario input only; not LOCAL-09 NSP/V3 or live Azure proof."},
        {"code": "binding-missing", "message": "No Azure runtime binding has been recorded."},
        {"code": "runtime-not-assessed", "message": "No provider evidence or runtime assessment exists."},
        {"code": "promises-unconfirmed", "message": "Context acknowledgement does not confirm business promises or RPO."},
        {"code": "demo-identity", "message": "Local demo approver demo-human; identity is not independently verified."},
    ]
    if not can_acknowledge:
        blockers.append({"code": "acknowledgement-capability-unavailable",
                         "message": "The policy owner must register acknowledge-run-context before this mutation is available."})
    if not acknowledged:
        blockers.append({"code": "context-not-acknowledged",
                         "message": "The selected known scenario and immutable run context have not been acknowledged."})
    actions = ([{"actionId": issue_context_action(case, scenario), "capability": "acknowledge-run-context",
                 "label": "Acknowledge scenario context only"}]
               if can_acknowledge and not acknowledged else [])
    at = datetime.now(timezone.utc).isoformat()

    def envelope(kind):
        return {
            "schemaVersion": "1.0.0", "artifactType": kind, "artifactId": f"PROJECTION-{uuid4().hex}",
            "runId": run["runId"], "caseId": run["caseId"], "scope": deepcopy(run["scope"]),
            "caseRevisionAtWrite": case["logicalRevision"], "createdAt": at, "updatedAt": at,
            "derivedFrom": {"case": case["stateChecksum"], "runManifest": run["stateChecksum"]},
            "scenario": identity, "runMode": run["runMode"], "purpose": run["purpose"],
            "logicalRevision": case["logicalRevision"], "asOf": at,
            "scenarioOrigin": scenario["scenarioOrigin"], "evidence": [],
            "currentWork": deepcopy(case["work"]), "allowedActions": deepcopy(actions),
            "blockers": deepcopy(blockers), "artifactRefs": [],
        }

    graph = build_graph(
        run=run, scenario=scenario, documents=[], promise_id="CP-01",
        logical_revision=case["logicalRevision"], as_of=at,
        evaluation_id=None, restoration_pending=False, external_references=[],
    )
    risk = {
        **envelope("operations-risk"), "riskState": "unknown",
        "headline": "Runtime assurance is unknown",
        "customerImpact": next(p["customerImpact"] for p in scenario["promises"] if p["promiseId"] == "CP-01"),
        "binding": None, "snapshot": None, "findingRefs": [], "evaluationRefs": [],
        "restoration": {"status": "not-requested", "operationReceipt": None, "verificationEvaluation": None},
    }
    risk["stateChecksum"] = semantic_checksum(risk)
    overview = {
        **envelope("experience-overview"), "businessGoal": scenario["businessIntent"],
        "coverage": {
            "phase": "runtime", "assessmentState": "not-assessed", "verifiedCount": None, "applicableCount": None,
            "rows": [{"promiseId": p["promiseId"], "confirmed": False, "status": "unknown",
                      "reasonCode": "binding-missing", "evaluation": None} for p in scenario["promises"]],
        },
        "operationsRisk": risk, "continuityGraph": graph,
    }
    overview["stateChecksum"] = semantic_checksum(overview)
    validate_contract(overview, "P01")
    validate_reference_integrity([case, *case["work"], *case["events"], overview], {run["runId"]: run}, scenario)
    return overview
