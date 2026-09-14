"""Author deterministic fixture-only contract examples; never run an evaluator or provider."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.contracts.integrity import scenario_identity, semantic_checksum, validate_reference_integrity, validate_scenario
from tools.contracts.validate import identify_contract

SCENARIO_PATH = ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json"
OUTPUT = ROOT / "contracts" / "examples" / "1.0.0" / "risk-examples.json"
TIME = "2026-09-12T17:05:00Z"
RUN_ID = "RUN-CONTRACT-V2"
CASE_ID = "CASE-CONTRACT-V2"
RESOURCE = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-contract-fixture/providers/Microsoft.Storage/storageAccounts/claimsfixturev2"
SCOPE = {
    "scopeId": "SCOPE-CONTRACT-V2",
    "subscriptionId": "00000000-0000-0000-0000-000000000000",
    "resourceGroup": "rg-contract-fixture",
    "resourceIds": [RESOURCE],
}
HUMAN = {"kind": "human", "actorId": "demo-human", "identityAssurance": "local-demo"}
INITIATOR = {"actorId": "demo-human", "identityAssurance": "local-demo"}
READ_RPO_ACTION = {
    "actionId": "view-rpo-question", "capability": "read-case", "label": "View the RPO question",
}


def seal(value):
    value["stateChecksum"] = semantic_checksum(value)
    return value


def build_examples():
    scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    validate_scenario(scenario)
    identity = scenario_identity(scenario)
    examples = {}

    def common(artifact_type, artifact_id):
        return {
            "schemaVersion": "1.0.0", "artifactType": artifact_type, "artifactId": artifact_id,
            "runId": RUN_ID, "caseId": CASE_ID, "scope": deepcopy(SCOPE),
            "caseRevisionAtWrite": 0, "createdAt": TIME, "updatedAt": TIME,
            "stateChecksum": "", "derivedFrom": {},
        }

    def domain(artifact_type, artifact_id):
        return {**common(artifact_type, artifact_id), "scenario": deepcopy(identity), "runMode": "fixture", "purpose": "test"}

    def projection(artifact_type, artifact_id, evidence):
        return {
            **domain(artifact_type, artifact_id), "logicalRevision": 0, "asOf": TIME,
            "scenarioOrigin": "fixture", "evidence": deepcopy(evidence), "currentWork": [],
            "allowedActions": [deepcopy(READ_RPO_ACTION)] if artifact_type in {"experience-overview", "operations-risk"} else [],
            "blockers": [], "artifactRefs": [],
        }

    def put(name, value):
        examples[name] = seal(value)
        return examples[name]

    def link(contract_id, value):
        return {
            "contractId": contract_id,
            "artifact": {"artifactId": value["artifactId"], "checksum": value["stateChecksum"]},
            "scenario": deepcopy(identity),
        }

    def opaque(contract_id, artifact_id, description):
        return link(contract_id, {"artifactId": artifact_id, "stateChecksum": semantic_checksum({"fixture": description})})

    generation = opaque("D10", "GENERATION-FIXTURE-V2", "owner-validated manifest reference placeholder, not a live generation manifest")
    application = opaque("D12", "APPLICATION-FIXTURE-V2", "owner-validated application reference placeholder, not live materialization")
    correction = opaque("D11", "CORRECTION-FIXTURE-V2", "owner-validated correction reference placeholder, not an applied correction")
    external = [generation, application, correction]
    run = seal({
        **common("local-run-manifest", "ART-RUN-CONTRACT-V2"),
        "runMode": "fixture", "purpose": "test", "scenarioId": identity["scenarioId"],
        "scenarioVersion": identity["scenarioVersion"], "scenarioHash": identity["scenarioHash"],
        "rootId": "ROOT-CONTRACT-V2", "configId": "CONFIG-CONTRACT-V2",
    })
    promises = put("promise-contract", {
        **domain("customer-promise-contract", "ART-PROMISES-V2"),
        "contractId": "PROMISES-CONTRACT-V2", "status": "partially-confirmed",
        "requirementChecksum": semantic_checksum({"fixture": "requirements excluding the unresolved RPO answer"}),
        "confirmationDecisionId": "DECISION-FIXTURE-NOT-LIVE",
        "confirmedPromiseIds": ["CP-01", "CP-02", "CP-03", "CP-04", "CP-06", "CP-07", "CP-08"],
        "promises": deepcopy(scenario["promises"]),
    })

    def evidence(name, properties):
        value = put(f"evidence-{name}", {
            **common("evidence-reference", f"EVIDENCE-{name.upper()}-V2"),
            "origin": "fixture", "evidenceState": "fresh",
            "collector": {"collectorId": "COLLECTOR-CONTRACT-FIXTURE", "version": "1.0.0"},
            "observedAt": TIME, "retrievedAt": TIME, "validUntil": "2026-09-12T17:10:00Z",
            "eligibility": "ineligible",
            "sourceChecksum": semantic_checksum({"resourceId": RESOURCE, "properties": properties}),
            "completeness": "complete",
            "supportedAssertionIds": [item["predicateId"] for item in scenario["cp01Verifier"]["predicates"]],
        })
        return {"reference": link("E01", value), "origin": "fixture"}

    desired = deepcopy(scenario["desiredStorageConfiguration"])
    observed = {**desired, "supportsHttpsTrafficOnly": False}
    baseline_evidence = evidence("baseline", desired)
    breach_evidence = evidence("breach", observed)
    operation = put("baseline-operation", {
        **domain("sandbox-operation-receipt", "ART-BASELINE-OP-V2"),
        "operationId": "OPERATION-BASELINE-V2", "operation": "deploy-baseline", "result": "acknowledged",
        "generationManifest": generation, "applicationReceipt": application,
        "desiredStateChecksum": scenario["desiredStateChecksum"], "resourceIds": [RESOURCE],
        "providerOperationId": "fixture-operation-not-provider-proof",
        "operatorConsentId": "CONSENT-FIXTURE-NOT-LIVE",
        "actor": {"kind": "system", "actorId": "SYSTEM-AZURE-ADAPTER"},
        "humanInitiator": deepcopy(INITIATOR), "startedAt": TIME, "completedAt": TIME,
        "evidence": [baseline_evidence], "correlationId": "CORRELATION-CONTRACT-V2",
    })
    binding = put("runtime-binding", {
        **domain("runtime-binding", "ART-BINDING-V2"),
        "bindingId": "BINDING-CONTRACT-V2", "componentId": scenario["componentId"], "resourceId": RESOURCE,
        "bindingState": "bound", "operationReceipt": link("D13", operation),
        "generationManifest": generation, "applicationReceipt": application,
        "desiredStateChecksum": scenario["desiredStateChecksum"], "boundAt": TIME, "gaps": [],
    })
    put("missing-binding", {
        **domain("runtime-binding", "ART-BINDING-MISSING-V2"),
        "bindingId": "BINDING-MISSING-V2", "componentId": scenario["componentId"], "resourceId": RESOURCE,
        "bindingState": "missing", "operationReceipt": None, "generationManifest": None,
        "applicationReceipt": None, "desiredStateChecksum": None, "boundAt": None,
        "gaps": ["deployment-binding-missing"],
    })
    snapshot = put("risk-snapshot", {
        **domain("runtime-snapshot", "ART-SNAPSHOT-RISK-V2"),
        "snapshotId": "SNAPSHOT-RISK-V2", "binding": link("D14", binding), "collectedAt": TIME,
        "evidenceWindow": {"from": TIME, "to": TIME}, "completeness": "complete",
        "observations": [{
            "resourceId": RESOURCE, "componentId": scenario["componentId"], "resourceType": scenario["resourceType"],
            "properties": observed, "evidence": [breach_evidence],
        }],
        "evidence": [breach_evidence], "missingEvidenceKinds": [], "collectionErrors": [],
    })
    unknown_snapshot = put("unknown-snapshot", {
        **domain("runtime-snapshot", "ART-SNAPSHOT-UNKNOWN-V2"),
        "snapshotId": "SNAPSHOT-UNKNOWN-V2", "binding": None, "collectedAt": TIME,
        "evidenceWindow": {"from": TIME, "to": TIME}, "completeness": "missing", "observations": [],
        "evidence": [], "missingEvidenceKinds": ["resource-configuration"], "collectionErrors": ["binding-missing"],
    })
    verifier = {
        "verifierId": scenario["cp01Verifier"]["verifierId"],
        "version": scenario["cp01Verifier"]["version"],
        "checksum": semantic_checksum(scenario["cp01Verifier"]),
    }
    # These are authored fixture results, deliberately not calculated by an evaluator.
    predicate_outcomes = [
        ("PRED-PUBLIC-NETWORK-ENABLED", "pass", "fixture-matches"),
        ("PRED-HTTPS-REQUIRED", "fail", "https-not-required"),
        ("PRED-ANONYMOUS-BLOB-DISABLED", "pass", "fixture-matches"),
        ("PRED-TLS12-MINIMUM", "pass", "fixture-matches"),
    ]
    evaluation = put("risk-evaluation", {
        **domain("promise-evaluation", "ART-EVALUATION-RISK-V2"),
        "evaluationId": "EVALUATION-RISK-V2", "promiseId": "CP-01", "phase": "runtime", "status": "breached",
        "reasonCode": "https-not-required", "evaluatedAt": TIME, "evidenceWindow": {"from": TIME, "to": TIME},
        "promiseContract": link("D03", promises), "binding": link("D14", binding),
        "runtimeSnapshot": link("D15", snapshot), "verifier": verifier,
        "predicateResults": [
            {"predicateId": predicate, "result": result, "reasonCode": reason, "evidence": [breach_evidence]}
            for predicate, result, reason in predicate_outcomes
        ],
        "evidence": [breach_evidence], "findingId": "FINDING-CP01-V2", "notApplicableDecision": None,
    })
    unknown_evaluation = put("unknown-evaluation", {
        **domain("promise-evaluation", "ART-EVALUATION-UNKNOWN-V2"),
        "evaluationId": "EVALUATION-UNKNOWN-V2", "promiseId": "CP-01", "phase": "runtime", "status": "unknown",
        "reasonCode": "binding-missing", "evaluatedAt": TIME, "evidenceWindow": {"from": TIME, "to": TIME},
        "promiseContract": link("D03", promises), "binding": None, "runtimeSnapshot": link("D15", unknown_snapshot),
        "verifier": verifier,
        "predicateResults": [
            {"predicateId": item["predicateId"], "result": "unknown", "reasonCode": "evidence-missing", "evidence": []}
            for item in scenario["cp01Verifier"]["predicates"]
        ],
        "evidence": [], "findingId": None, "notApplicableDecision": None,
    })
    finding = put("risk-finding", {
        **domain("drift-finding", "ART-FINDING-OPEN-V2"),
        "findingId": "FINDING-CP01-V2", "promiseId": "CP-01", "ruleId": verifier["verifierId"],
        "componentId": scenario["componentId"], "resourceId": RESOURCE, "severity": "high", "status": "open",
        "reasonCode": "https-not-required", "customerImpact": scenario["promises"][0]["customerImpact"],
        "baseline": link("D14", binding), "runtimeSnapshot": link("D15", snapshot), "evaluation": link("D17", evaluation),
        "proposedCorrection": None, "restorationOperation": None, "firstObservedAt": TIME, "lastObservedAt": TIME,
        "evidence": [breach_evidence], "correlationId": "CORRELATION-CONTRACT-V2",
    })
    pending_finding = put("pending-finding", {
        **deepcopy(finding), "artifactId": "ART-FINDING-PENDING-V2",
        "status": "restoration-pending", "proposedCorrection": correction,
    })

    for name, activity_class, attention_kind, action in (
        ("product", "product-workflow", "presented", "view-rpo-question"),
        ("operator", "demo-operator", "operator-action", "inspect-preflight"),
    ):
        event = put(f"{name}-source-event", {
            **common("domain-event", f"ART-EVENT-{name.upper()}-V2"),
            "eventId": f"EVENT-{name.upper()}-V2", "sequence": 1 if name == "product" else 2,
            "eventType": action, "correlationId": "CORRELATION-CONTRACT-V2",
            "workId": None, "actor": deepcopy(HUMAN), "payloadRefs": [],
        })
        put(f"{name}-attention", {
            **domain("human-attention-event", f"ART-ATTENTION-{name.upper()}-V2"),
            "eventId": f"ATTENTION-EVENT-{name.upper()}-V2", "attentionId": f"ATTENTION-{name.upper()}-V2",
            "stepId": f"STEP-{name.upper()}-V2", "questionId": "QUESTION-RPO" if name == "product" else None,
            "decisionId": None, "activityClass": activity_class, "actionId": action, "attentionKind": attention_kind,
            "actor": deepcopy(HUMAN), "occurredAt": TIME, "durationSeconds": None,
            "sourceEvent": link("E04", event), "correlationId": "CORRELATION-CONTRACT-V2",
        })

    def graph_for(scene, selected_evaluation, scene_evidence):
        def scenario_node(node_id, node_type, entity_id, label):
            return {"nodeId": node_id, "nodeType": node_type, "label": label, "source": {"kind": "scenario", "scenario": deepcopy(identity), "entityId": entity_id}}

        def artifact_node(node_id, node_type, contract_id, value, label):
            return {"nodeId": node_id, "nodeType": node_type, "label": label, "source": {"kind": "artifact", "reference": link(contract_id, value)}}

        nodes = [
            scenario_node("NODE-INTENT", "intent", scenario["intentId"], "Contoso claims intent"),
            scenario_node("NODE-CP01", "promise", "CP-01", "Approved public storage configuration"),
            scenario_node("NODE-STORE", "component", scenario["componentId"], "Claims storage"),
            artifact_node("NODE-EVALUATION", "evaluation", "D17", selected_evaluation, "CP-01 evaluation"),
        ]
        edges = [
            {
                "edgeId": "EDGE-INTENT-PROMISE", "fromNodeId": "NODE-INTENT", "toNodeId": "NODE-CP01",
                "relation": "defines", "status": "supported",
                "support": {"kind": "scenario-link", "scenario": deepcopy(identity), "fromEntityId": scenario["intentId"], "toEntityId": "CP-01"},
            },
            {
                "edgeId": "EDGE-PROMISE-STORE", "fromNodeId": "NODE-CP01", "toNodeId": "NODE-STORE",
                "relation": "implemented-by", "status": "supported",
                "support": {"kind": "scenario-link", "scenario": deepcopy(identity), "fromEntityId": "CP-01", "toEntityId": scenario["componentId"]},
            },
            {
                "edgeId": "EDGE-EVALUATION-PROMISE", "fromNodeId": "NODE-EVALUATION", "toNodeId": "NODE-CP01",
                "relation": "evaluates", "status": "gap" if scene == "unknown" else "broken",
                "support": {"kind": "evaluation", "reference": link("D17", selected_evaluation), "promiseId": "CP-01"},
            },
        ]
        if scene == "unknown":
            nodes.append({
                "nodeId": "NODE-BASELINE-GAP", "nodeType": "baseline", "label": "Deployment binding unavailable",
                "source": {"kind": "gap", "expectedContractId": "D14", "reasonCode": "binding-missing"},
            })
            edges.append({
                "edgeId": "EDGE-BASELINE-GAP", "fromNodeId": "NODE-EVALUATION", "toNodeId": "NODE-BASELINE-GAP",
                "relation": "references", "status": "gap", "support": {"kind": "gap", "reasonCode": "binding-missing"},
            })
        else:
            nodes.extend([
                artifact_node("NODE-SNAPSHOT", "runtime-snapshot", "D15", snapshot, "Observed storage configuration"),
                artifact_node("NODE-BASELINE", "baseline", "D14", binding, "Acknowledged fixture baseline"),
                artifact_node("NODE-EVIDENCE", "evidence", "E01", examples["evidence-breach"], "Fixture configuration evidence"),
            ])
            for edge_id, source_id, target_id, source_ref, target_ref in (
                ("EDGE-EVALUATION-SNAPSHOT", "NODE-EVALUATION", "NODE-SNAPSHOT", link("D17", evaluation), link("D15", snapshot)),
                ("EDGE-SNAPSHOT-BASELINE", "NODE-SNAPSHOT", "NODE-BASELINE", link("D15", snapshot), link("D14", binding)),
                ("EDGE-SNAPSHOT-EVIDENCE", "NODE-SNAPSHOT", "NODE-EVIDENCE", link("D15", snapshot), breach_evidence["reference"]),
            ):
                edges.append({
                    "edgeId": edge_id, "fromNodeId": source_id, "toNodeId": target_id, "relation": "references",
                    "status": "supported", "support": {"kind": "artifact-link", "source": source_ref, "target": target_ref},
                })
            if scene == "pending":
                nodes.append({
                    "nodeId": "NODE-VERIFICATION-GAP", "nodeType": "evaluation", "label": "Fresh restoration verification pending",
                    "source": {"kind": "gap", "expectedContractId": "D17", "reasonCode": "fresh-evidence-required"},
                })
                edges.append({
                    "edgeId": "EDGE-VERIFICATION-PENDING", "fromNodeId": "NODE-CP01", "toNodeId": "NODE-VERIFICATION-GAP",
                    "relation": "evaluates", "status": "pending", "support": {"kind": "gap", "reasonCode": "fresh-evidence-required"},
                })
        return put(f"{scene}-graph", {
            **projection("intent-continuity-graph", f"ART-GRAPH-{scene.upper()}-V2", scene_evidence),
            "nodes": nodes, "edges": edges,
            "listEntries": [
                {"nodeId": node["nodeId"], "relatedEdgeIds": [edge["edgeId"] for edge in edges if node["nodeId"] in (edge["fromNodeId"], edge["toNodeId"])]}
                for node in nodes
            ],
        })

    for scene, risk_state, headline in (
        ("unknown", "unknown", "Runtime assurance is unavailable"),
        ("risk", "known-risk", "Claims storage no longer requires HTTPS"),
        ("pending", "restoration-pending", "Correction prepared; authorized restoration and fresh verification pending"),
    ):
        selected_evaluation = unknown_evaluation if scene == "unknown" else evaluation
        selected_snapshot = unknown_snapshot if scene == "unknown" else snapshot
        selected_finding = pending_finding if scene == "pending" else finding
        scene_evidence = [] if scene == "unknown" else [breach_evidence]
        risk = put(f"{scene}-operations", {
            **projection("operations-risk", f"ART-OPERATIONS-{scene.upper()}-V2", scene_evidence),
            "riskState": risk_state, "headline": headline, "customerImpact": scenario["promises"][0]["customerImpact"],
            "binding": None if scene == "unknown" else link("D14", binding),
            "snapshot": link("D15", selected_snapshot),
            "findingRefs": [] if scene == "unknown" else [link("D16", selected_finding)],
            "evaluationRefs": [link("D17", selected_evaluation)],
            "restoration": {"status": "awaiting-operator" if scene == "pending" else "not-requested", "operationReceipt": None, "verificationEvaluation": None},
        })
        graph = graph_for(scene, selected_evaluation, scene_evidence)
        overview = {
            **projection("experience-overview", f"ART-OVERVIEW-{scene.upper()}-V2", scene_evidence),
            "businessGoal": scenario["businessIntent"],
            "coverage": {
                "phase": "runtime", "assessmentState": "not-assessed" if scene == "unknown" else "partial",
                "verifiedCount": None, "applicableCount": None,
                "rows": [
                    {
                        "promiseId": promise["promiseId"], "confirmed": promise["promiseId"] != "CP-05",
                        "status": selected_evaluation["status"] if promise["promiseId"] == "CP-01" else "unknown",
                        "reasonCode": selected_evaluation["reasonCode"] if promise["promiseId"] == "CP-01" else ("rpo-unconfirmed" if promise["promiseId"] == "CP-05" else "evidence-not-collected"),
                        "evaluation": link("D17", selected_evaluation) if promise["promiseId"] == "CP-01" else None,
                    }
                    for promise in scenario["promises"]
                ],
            },
            "operationsRisk": deepcopy(risk), "continuityGraph": deepcopy(graph),
        }
        overview["artifactRefs"] = [link("P05", risk), link("P06", graph)]
        put(f"{scene}-overview", overview)

    validate_reference_integrity(examples.values(), {RUN_ID: run}, scenario, external)
    return {
        "exampleOrigin": "fixture",
        "description": "Contract shape examples only. Azure IDs, acknowledgements, decisions and outcomes are synthetic; no operation or human approval is authorized or proved.",
        "scenario": identity, "runManifest": run, "externalReferences": external,
        "records": [{"name": name, "contractId": identify_contract(value), "value": value} for name, value in examples.items()],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = (json.dumps(build_examples(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != data:
            print("Risk fixture bytes differ; run tools\\contracts\\write_risk_examples.py", file=sys.stderr)
            return 1
        print("Risk fixture examples are schema-valid, reference-consistent and byte-stable.")
    else:
        OUTPUT.write_bytes(data)
        print(f"Wrote schema-validated fixture examples: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
