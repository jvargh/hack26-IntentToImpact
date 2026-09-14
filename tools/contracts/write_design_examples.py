"""Author fixture-only requirement/decision records; never execute a model, gate or approval."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.contracts.design_integrity import artifact_reference, catalog_checksum, validate_design_references
from tools.contracts.integrity import scenario_identity, semantic_checksum, validate_scenario
from tools.contracts.validate import identify_contract

OUTPUT = ROOT / "contracts" / "examples" / "1.0.0" / "design-examples.json"
SCENARIO = ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json"
TIME = "2026-09-12T18:30:00Z"
HUMAN = {"kind": "human", "actorId": "demo-human", "identityAssurance": "local-demo"}


def seal(value):
    value["stateChecksum"] = semantic_checksum(value)
    return value


def build_examples():
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    validate_scenario(scenario)
    identity = scenario_identity(scenario)
    old = json.loads((ROOT / "contracts" / "examples" / "1.0.0" / "risk-examples.json").read_text(encoding="utf-8"))
    run = deepcopy(old["runManifest"])
    run.update(
        artifactId="ART-RUN-DESIGN-V2", runId="RUN-DESIGN-V2", caseId="CASE-DESIGN-V2",
        rootId="ROOT-DESIGN-V2", configId="CONFIG-DESIGN-V2", createdAt=TIME, updatedAt=TIME,
    )
    seal(run)
    examples = {}

    def common(kind, artifact_id):
        return {
            "schemaVersion": "1.0.0", "artifactType": kind, "artifactId": artifact_id,
            "runId": run["runId"], "caseId": run["caseId"], "scope": deepcopy(run["scope"]),
            "caseRevisionAtWrite": 1, "createdAt": TIME, "updatedAt": TIME,
            "stateChecksum": "", "derivedFrom": {"scenario": scenario["stateChecksum"]},
        }

    def domain(kind, artifact_id):
        return {**common(kind, artifact_id), "scenario": deepcopy(identity), "runMode": "fixture", "purpose": "test"}

    def put(name, value, inputs=None):
        if inputs:
            value.update(deepcopy(inputs))
            value["derivedFrom"].update({
                name: (reference["artifact"] if "contractId" in reference else reference)["checksum"]
                for name, reference in inputs.items() if reference is not None
            })
        if value["artifactType"] == "review-gate-evaluation":
            value["gate"]["boundChecksums"] = deepcopy(value["derivedFrom"])
        if value["artifactType"] == "architecture-decision-record" and value["decisionReceipt"] is not None:
            value["decisionReceipt"]["boundChecksums"] = deepcopy(value["derivedFrom"])
        examples[name] = seal(value)
        return examples[name]

    def typed_ref(contract_id, value):
        return {"contractId": contract_id, "artifact": artifact_reference(value), "scenario": deepcopy(identity)}

    def attention(name, action_id, decision_id, kind, when, question_id=None):
        source = put(f"{name}-source-event", {
            **common("domain-event", f"ART-EVENT-{name.upper()}"),
            "eventId": f"EVENT-{name.upper()}", "sequence": len(examples) + 1,
            "eventType": action_id, "correlationId": "CORRELATION-DESIGN-FIXTURE",
            "workId": None, "actor": deepcopy(HUMAN), "payloadRefs": [],
        })
        return put(f"{name}-attention", {
            **domain("human-attention-event", f"ART-ATTENTION-{name.upper()}"),
            "eventId": f"ATTENTION-EVENT-{name.upper()}", "attentionId": f"ATTENTION-{name.upper()}",
            "stepId": f"STEP-{name.upper()}", "questionId": question_id, "decisionId": decision_id,
            "activityClass": "product-workflow", "actionId": action_id, "attentionKind": kind,
            "actor": deepcopy(HUMAN), "occurredAt": when, "durationSeconds": None,
            "sourceEvent": typed_ref("E04", source), "correlationId": "CORRELATION-DESIGN-FIXTURE",
        })

    requirement_ids = [rid for promise in scenario["promises"] for rid in promise["requirementIds"]]
    promise_ids = [promise["promiseId"] for promise in scenario["promises"]]
    unknown = put("requirements-unknown-rpo", {
        **domain("requirements", "ART-REQUIREMENTS-UNKNOWN"),
        "requirementsId": "REQUIREMENTS-CLAIMS", "status": "awaiting-answers",
        "businessIntent": scenario["businessIntent"], "requirementIds": requirement_ids,
        "promiseIds": promise_ids,
        "rpoQuestion": {
            "questionId": "QUESTION-RPO", "promiseId": "CP-05",
            "prompt": "For the declared regional-loss scenario, explicitly confirm the 15-minute RPO.",
            "required": True, "status": "unanswered", "valueMinutes": None, "confirmation": None,
        },
        "constraints": {
            "rtoMinutes": scenario["rtoMinutes"], "monthlyBudgetUsd": scenario["monthlyBudgetUsd"],
            "geography": "US", "minimumDiagnosticRetentionDays": 90,
            "storageConfiguration": deepcopy(scenario["desiredStorageConfiguration"]),
        },
    })
    rpo_attention = attention(
        "rpo-confirmed", "confirm-rpo-r1", "DECISION-RPO-FIXTURE", "answered",
        "2026-09-12T18:05:00Z", "QUESTION-RPO",
    )
    confirmed = deepcopy(unknown)
    confirmed.update(artifactId="ART-REQUIREMENTS-CONFIRMED", status="confirmed")
    confirmed["rpoQuestion"].update(
        status="answered", valueMinutes=15,
        confirmation={
            "decisionId": "DECISION-RPO-FIXTURE", "actionId": "confirm-rpo-r1",
            "actor": deepcopy(HUMAN), "confirmedAt": "2026-09-12T18:05:00Z",
            "attentionEvent": typed_ref("E05", rpo_attention),
        },
    )
    confirmed = put("requirements-confirmed-rpo", confirmed)

    def promises(name, requirements, confirmed_ids, status):
        return put(name, {
            **domain("customer-promise-contract", f"ART-{name.upper()}"),
            "contractId": "PROMISES-CLAIMS-V2", "status": status,
            "requirementChecksum": requirements["stateChecksum"],
            "confirmationDecisionId": "DECISION-RPO-FIXTURE" if status == "confirmed" else "DECISION-INITIAL-FIXTURE",
            "confirmedPromiseIds": confirmed_ids, "promises": deepcopy(scenario["promises"]),
        })

    old_promises = promises("promises-unknown-rpo", unknown, [pid for pid in promise_ids if pid != "CP-05"], "partially-confirmed")
    current_promises = promises("promises-confirmed-rpo", confirmed, promise_ids, "confirmed")
    module = {
        "moduleId": "MODULE-CLAIMS-STORAGE-V2", "version": "1.0.0",
        "checksum": semantic_checksum({"fixture": "approved storage module descriptor; no module files installed"}),
    }
    options = [
        {
            "optionId": "OPTION-" + candidate["candidateId"],
            "title": "Catalog candidate " + candidate["candidateId"],
            "summary": (
                "Synthetic USD 6,000/month with no reviewed regional-recovery profile."
                if candidate["candidateId"] == "A"
                else "Synthetic USD 7,200/month with the catalog active-passive recovery profile."
            ),
            "catalogFacts": deepcopy(candidate),
            "components": [{
                "componentId": scenario["componentId"], "resourceType": scenario["resourceType"],
                "dataClassification": "confidential", "identityMode": "managed-identity",
                "networkExposure": "public-endpoint", "geography": "US",
                "storageConfiguration": deepcopy(scenario["desiredStorageConfiguration"]),
                "module": deepcopy(module), "promiseIds": promise_ids, "requirementIds": requirement_ids,
            }],
            "relationships": [], "assumptions": ["Operator resource and region bindings are separate preflight inputs."],
            "unresolvedItems": [],
        }
        for candidate in scenario["candidates"]
    ]
    proposal_inputs = {
        "requirements": artifact_reference(confirmed),
        "promiseContract": typed_ref("D03", current_promises),
    }
    proposal = put("architecture-proposal", {
        **domain("architecture-proposal", "ART-PROPOSAL-CLAIMS"),
        "proposalId": "PROPOSAL-CLAIMS", "authority": "proposal-only",
        "producer": {"kind": "agent", "actorId": "AGENT-FIXTURE-SYNTHESIS"},
        "origin": "fixture", "invocationReceipt": None,
        "catalog": {
            "catalogId": scenario["catalog"]["catalogId"], "version": scenario["catalog"]["catalogVersion"],
            "checksum": catalog_checksum(scenario),
        },
        "options": options, "recommendedOptionId": "OPTION-A",
        "rationale": "Fixture-only lower-price proposal. This recommendation has no eligibility or approval authority.",
    }, proposal_inputs)

    def review_gate(name, subject, subject_kind, requirements, promise_contract, gate_id, *,
                    deterministic="pass", inference="pass", effective="pass",
                    approval_status="pending", approval=None, findings=None, assessments=None):
        return put(name, {
            **domain("review-gate-evaluation", f"ART-{name.upper()}"),
            "subjectContractId": subject_kind,
            "review": {
                "reviewId": f"REVIEW-{name.upper()}", "deterministicStatus": deterministic,
                "inferenceStatus": inference, "findings": findings or [], "optionAssessments": assessments or [],
            },
            "gate": {
                "gateId": gate_id, "version": "1.0.0", "effectiveStatus": effective,
                "approvalStatus": approval_status, "approval": artifact_reference(approval) if approval else None,
                "evaluatedAt": TIME, "expectedRevision": 1, "boundChecksums": {},
            },
        }, {
            "subject": artifact_reference(subject), "requirements": artifact_reference(requirements),
            "promiseContract": typed_ref("D03", promise_contract),
        })

    review_gate(
        "requirements-blocked-gate", unknown, "D02", unknown, old_promises, "requirements-ready",
        deterministic="blocked", effective="blocked",
    )
    # These are authored engine-result fixtures, not eligibility calculations.
    assessments = [
        {
            "assessmentId": "ASSESSMENT-A", "optionId": "OPTION-A", "evaluationKind": "design-eligibility",
            "producer": {"kind": "system", "actorId": "SYSTEM-REVIEW-ENGINE"},
            "eligibility": "ineligible", "reasonCodes": ["approved-recovery-profile-missing"],
            "ruleResults": [
                {"ruleId": "RULE-RECOVERY-PROFILE-V2", "mandatory": True, "status": "fail", "reasonCode": "approved-recovery-profile-missing", "inputChecksum": catalog_checksum(scenario)},
                {"ruleId": "RULE-MONTHLY-BUDGET-V2", "mandatory": True, "status": "pass", "reasonCode": "within-estimated-budget", "inputChecksum": catalog_checksum(scenario)},
            ],
        },
        {
            "assessmentId": "ASSESSMENT-B", "optionId": "OPTION-B", "evaluationKind": "design-eligibility",
            "producer": {"kind": "system", "actorId": "SYSTEM-REVIEW-ENGINE"},
            "eligibility": "eligible", "reasonCodes": ["reviewed-catalog-criteria-supported"],
            "ruleResults": [
                {"ruleId": "RULE-RECOVERY-PROFILE-V2", "mandatory": True, "status": "pass", "reasonCode": "approved-recovery-profile-present", "inputChecksum": catalog_checksum(scenario)},
                {"ruleId": "RULE-MONTHLY-BUDGET-V2", "mandatory": True, "status": "pass", "reasonCode": "within-estimated-budget", "inputChecksum": catalog_checksum(scenario)},
            ],
        },
    ]
    findings = [
        {
            "findingId": "FINDING-DESIGN-A", "source": "deterministic",
            "actor": {"kind": "system", "actorId": "SYSTEM-REVIEW-ENGINE"}, "severity": "blocker",
            "ruleId": "RULE-RECOVERY-PROFILE-V2", "optionId": "OPTION-A",
            "message": "A lacks the reviewed recovery profile; lower estimated spend does not make it eligible.",
            "evidenceRefs": [],
        },
        {
            "findingId": "FINDING-AGENT-RECOVERY", "source": "agent",
            "actor": {"kind": "agent", "actorId": "AGENT-FIXTURE-ASSURANCE"}, "severity": "warning",
            "ruleId": "RULE-RECOVERY-EVIDENCE-V2", "optionId": "OPTION-B",
            "message": "A supported design profile is not runtime recovery-test evidence or an approval.",
            "evidenceRefs": [],
        },
    ]
    design_review = review_gate(
        "design-review", proposal, "D04", confirmed, current_promises, "design-ready",
        deterministic="pass-with-warnings", effective="pass-with-warnings",
        findings=findings, assessments=assessments,
    )
    model = put("architecture-model", {
        **domain("architecture-model", "ART-ARCHITECTURE-CLAIMS"),
        "architectureId": "ARCHITECTURE-CLAIMS", "status": "validated",
        "options": deepcopy(options), "recommendedOptionId": "OPTION-B",
        "selectedOptionId": None, "decision": None,
    }, {
        "sourceProposal": artifact_reference(proposal), "review": artifact_reference(design_review),
        "promiseContract": typed_ref("D03", current_promises),
    })
    adr_inputs = {
        "architecture": artifact_reference(model), "review": artifact_reference(design_review),
        "requirements": artifact_reference(confirmed), "promiseContract": typed_ref("D03", current_promises),
    }
    proposed_adr = put("adr-proposed", {
        **domain("architecture-decision-record", "ART-ADR-PROPOSED"),
        "adrId": "ADR-CLAIMS", "status": "proposed", "title": "Claims storage and regional recovery",
        "context": "Choose against confirmed requirements and reviewed catalog facts; no runtime assurance is implied.",
        "consideredOptionIds": ["OPTION-A", "OPTION-B"], "decisionReceipt": None,
    }, adr_inputs)
    selection_attention = attention("option-selection", "select-option-b-r1", "DECISION-SELECT-B", "confirmed", "2026-09-12T18:15:00Z")
    adr = deepcopy(proposed_adr)
    adr.update(artifactId="ART-ADR-RECORDED", status="recorded")
    adr["decisionReceipt"] = {
        "decisionId": "DECISION-SELECT-B", "outcome": "selected", "selectedOptionId": "OPTION-B",
        "rationale": "Fixture human selection of the reviewed eligible alternative, not an execution approval.",
        "actor": deepcopy(HUMAN), "actionId": "select-option-b-r1", "decidedAt": "2026-09-12T18:15:00Z",
        "attentionEvent": typed_ref("E05", selection_attention), "boundChecksums": {},
    }
    adr = put("adr-recorded", adr, adr_inputs)
    expected_binding = {
        "subjectContractId": "D06", "subject": artifact_reference(adr), "capability": "approve-design",
        "actionId": "approve-design-r1", "expectedRevision": 1, "gateId": "design-ready",
        "boundChecksums": {
            "scenario": scenario["stateChecksum"], "requirements": confirmed["stateChecksum"],
            "promiseContract": current_promises["stateChecksum"], "architecture": model["stateChecksum"],
            "decision": adr["stateChecksum"], "review": design_review["stateChecksum"],
        },
    }
    pending = put("approval-pending", {
        **domain("approval", "ART-APPROVAL-PENDING"), "approvalId": "APPROVAL-DESIGN",
        "approvalClass": "design", "status": "pending", "binding": deepcopy(expected_binding),
        "issuedAt": "2026-09-12T18:16:00Z", "expiresAt": "2026-09-12T19:00:00Z",
        "decidedAt": None, "decisionId": None, "actor": None, "attentionEvent": None,
    }, {"gateEvaluation": artifact_reference(design_review)})
    approved_attention = attention("design-approval", "approve-design-r1", "DECISION-APPROVE-DESIGN", "approved", "2026-09-12T18:20:00Z")
    approved = deepcopy(pending)
    approved.update(
        artifactId="ART-APPROVAL-APPROVED", status="approved", decidedAt="2026-09-12T18:20:00Z",
        decisionId="DECISION-APPROVE-DESIGN", actor=deepcopy(HUMAN), attentionEvent=typed_ref("E05", approved_attention),
    )
    approved = put("approval-approved", approved)
    for status in ("stale", "expired"):
        value = deepcopy(approved)
        value.update(artifactId=f"ART-APPROVAL-{status.upper()}", status=status)
        put(f"approval-{status}", value)
    rejected_attention = attention("design-rejection", "approve-design-r1", "DECISION-REJECT-DESIGN", "rejected", "2026-09-12T18:21:00Z")
    rejected = deepcopy(approved)
    rejected.update(
        artifactId="ART-APPROVAL-REJECTED", status="rejected", decidedAt="2026-09-12T18:21:00Z",
        decisionId="DECISION-REJECT-DESIGN", attentionEvent=typed_ref("E05", rejected_attention),
    )
    put("approval-rejected", rejected)
    generation_gate = review_gate(
        "generation-gate", adr, "D06", confirmed, current_promises, "generation-ready",
        approval_status="approved", approval=approved,
    )
    review_gate(
        "blocked-checks-approved-snapshot", adr, "D06", confirmed, current_promises, "generation-ready",
        deterministic="blocked", effective="blocked", approval_status="approved", approval=approved,
    )
    generation_inputs = {
        "requirements": artifact_reference(confirmed), "promiseContract": typed_ref("D03", current_promises),
        "architecture": artifact_reference(model), "decision": artifact_reference(adr),
        "gateEvaluation": artifact_reference(generation_gate), "approval": None,
    }
    draft_plan = put("generation-draft", {
        **domain("generation-contract", "ART-GENERATION-DRAFT"),
        "generationId": "GENERATION-CLAIMS", "status": "draft", "selectedOptionId": "OPTION-B",
        "renderMode": "approved-templates-only", "outputRootId": "ROOT-DESIGN-OUTPUT",
        "modules": [deepcopy(module)],
        "outputs": [{
            "relativePath": "infra/main.bicep", "kind": "bicep", "template": deepcopy(module),
            "componentIds": [scenario["componentId"]], "promiseIds": promise_ids,
        }],
        "desiredStorageConfiguration": deepcopy(scenario["desiredStorageConfiguration"]),
        "desiredStateChecksum": scenario["desiredStateChecksum"],
    }, generation_inputs)
    ready_plan = deepcopy(draft_plan)
    ready_plan.update(artifactId="ART-GENERATION-READY", status="ready")
    put("generation-ready", ready_plan, {**generation_inputs, "approval": artifact_reference(approved)})
    bindings = {approved["artifactId"]: deepcopy(expected_binding)}
    validate_design_references(examples.values(), {run["runId"]: run}, scenario, current_bindings=bindings, as_of=TIME)
    return {
        "exampleOrigin": "fixture",
        "description": "Authored contract examples only. No model invocation, real human decision/approval, generation, provider operation or product/UX approval is claimed.",
        "scenario": identity, "runManifest": run, "asOf": TIME,
        "currentApprovalBindings": bindings,
        "currentInputReferences": {"architecture-proposal": proposal_inputs},
        "records": [{"name": name, "contractId": identify_contract(value), "value": value} for name, value in examples.items()],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = (json.dumps(build_examples(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != data:
            print("Design fixture bytes differ; run tools\\contracts\\write_design_examples.py", file=sys.stderr)
            return 1
        print("Design fixture shapes, source references, current binding comparisons and bytes match.")
    else:
        OUTPUT.write_bytes(data)
        print(f"Wrote validated fixture-only design records: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
