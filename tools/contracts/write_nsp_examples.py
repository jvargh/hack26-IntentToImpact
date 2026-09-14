"""Author new V3 fixture records from V3 facts only; no V2 migration or provider execution."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.contracts.integrity import semantic_checksum
from tools.contracts.nsp_integrity import scenario_identity, validate_v3_reference_integrity, validate_v3_scenario
from tools.contracts.validate import identify_contract

OUTPUT = ROOT / "contracts" / "examples" / "2.0.0" / "nsp-examples.json"
SCENARIO = ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V3.json"
TIME = "2026-09-13T02:00:00Z"
BASE = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-nsp-contract-fixture"
STORAGE = BASE + "/providers/Microsoft.Storage/storageAccounts/claimsfixturev3"
PERIMETER = BASE + "/providers/Microsoft.Network/networkSecurityPerimeters/perimeterfixture"
PROFILE = PERIMETER + "/profiles/profilefixture"
ASSOCIATION = PERIMETER + "/resourceAssociations/associationfixture"
CONFIGURATION = STORAGE + "/networkSecurityPerimeterConfigurations/configfixture"
GUID = "11111111-1111-1111-1111-111111111111"


def seal(value):
    value["stateChecksum"] = semantic_checksum(value)
    return value


def build_examples():
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    validate_v3_scenario(scenario)
    identity = scenario_identity(scenario)
    scope = {
        "scopeId": "SCOPE-NSP-FIXTURE-V3", "subscriptionId": "00000000-0000-0000-0000-000000000000",
        "resourceGroup": "rg-nsp-contract-fixture",
        "resourceIds": [STORAGE, PERIMETER, PROFILE, ASSOCIATION, CONFIGURATION],
    }
    records = {}

    def metadata(kind, artifact_id, version="2.0.0"):
        value = {
            "schemaVersion": version, "artifactType": kind, "artifactId": artifact_id,
            "runId": "RUN-NSP-FIXTURE-V3", "caseId": "CASE-NSP-FIXTURE-V3", "scope": deepcopy(scope),
            "caseRevisionAtWrite": 0, "createdAt": TIME, "updatedAt": TIME,
            "stateChecksum": "", "derivedFrom": {},
        }
        if version == "2.0.0":
            value.update(scenario=deepcopy(identity), runMode="fixture", purpose="test")
        return value

    def put(name, value, inputs=None):
        if inputs:
            value.update(deepcopy(inputs))
            value["derivedFrom"].update({
                field: (ref["artifact"] if "artifact" in ref else ref)["checksum"]
                for field, ref in inputs.items() if ref is not None
            })
        records[name] = seal(value)
        return records[name]

    def bare(value):
        return {"artifactId": value["artifactId"], "checksum": value["stateChecksum"]}

    def link(contract_id, value, version=None):
        return {
            "contractId": contract_id, "schemaVersion": version or value["schemaVersion"],
            "artifact": bare(value), "scenario": deepcopy(identity),
        }

    def opaque(contract_id, name):
        return link(contract_id, {"schemaVersion": "2.0.0", "artifactId": name, "stateChecksum": semantic_checksum({"fixtureReference": name})})

    generation = opaque("D10", "GENERATION-NSP-FIXTURE-V3")
    application = opaque("D12", "APPLICATION-NSP-FIXTURE-V3")
    external = [generation, application]
    run = seal({
        **metadata("local-run-manifest", "ART-RUN-NSP-V3", "1.0.0"),
        "runMode": "fixture", "purpose": "test",
        "scenarioId": identity["scenarioId"], "scenarioVersion": identity["scenarioVersion"], "scenarioHash": identity["scenarioHash"],
        "rootId": "ROOT-NSP-FIXTURE-V3", "configId": "CONFIG-NSP-FIXTURE-V3",
    })
    requirement_ids = [rid for promise in scenario["promises"] for rid in promise["requirementIds"]]
    promise_ids = [promise["promiseId"] for promise in scenario["promises"]]
    requirements = put("requirements-unknown", {
        **metadata("requirements", "ART-REQUIREMENTS-NSP-V3"),
        "requirementsId": "REQUIREMENTS-NSP-V3", "status": "awaiting-answers",
        "businessIntent": scenario["businessIntent"], "requirementIds": requirement_ids, "promiseIds": promise_ids,
        "rpoQuestion": {
            "questionId": "QUESTION-RPO", "promiseId": "CP-05",
            "prompt": "An actual human confirmation of the scripted 15-minute RPO is still required.",
            "required": True, "status": "unanswered", "valueMinutes": None, "confirmation": None,
        },
        "constraints": {
            "rtoMinutes": 60, "monthlyBudgetUsd": 8000, "geography": "US", "minimumDiagnosticRetentionDays": 90,
            "storageConfiguration": deepcopy(scenario["desiredStorageConfiguration"]),
            "nspConfiguration": deepcopy(scenario["desiredNspConfiguration"]),
        },
    })
    promises = put("promise-contract", {
        **metadata("customer-promise-contract", "ART-PROMISES-NSP-V3"),
        "contractId": "PROMISES-NSP-V3", "status": "partially-confirmed",
        "requirementChecksum": requirements["stateChecksum"], "confirmationDecisionId": None,
        "confirmedPromiseIds": [], "promises": deepcopy(scenario["promises"]),
    })
    complete_values = {
        "storage": {"id": STORAGE, **deepcopy(scenario["desiredStorageConfiguration"])},
        "perimeter": {"id": PERIMETER, "perimeterGuid": GUID, "provisioningState": "Succeeded"},
        "profile": {"id": PROFILE, "name": "profilefixture", "accessRulesVersion": "1"},
        "association": {"id": ASSOCIATION, "name": "associationfixture", "privateLinkResourceId": STORAGE, "profileId": PROFILE, "accessMode": "Enforced"},
        "configuration": {
            "id": CONFIGURATION, "perimeterId": PERIMETER, "perimeterGuid": GUID,
            "associationName": "associationfixture", "accessMode": "Enforced", "profileName": "profilefixture",
            "accessRulesVersion": "1", "provisioningState": "Succeeded", "provisioningIssues": [],
        },
    }

    def observation_for(scene):
        values = deepcopy(complete_values)
        if scene == "breached":
            values["association"]["accessMode"] = "Learning"
            values["configuration"]["accessMode"] = "Learning"
        if scene == "pending":
            values["configuration"]["provisioningState"] = "Creating"
            values["configuration"]["accessRulesVersion"] = "0"
        result = {}
        for member, value in values.items():
            missing = scene == "unknown" and member != "storage"
            partial = scene == "pending" and member == "configuration"
            result[member] = {
                "observationState": "missing" if missing else "partial" if partial else "complete",
                "observedAt": None if missing else TIME, "evidence": [],
                "value": None if missing else value,
            }
        for name, resource in (("profileAccessRules", PROFILE), ("effectiveAccessRules", CONFIGURATION)):
            missing = scene == "unknown"
            partial = scene == "pending" and name == "effectiveAccessRules"
            result[name] = {
                "collectionState": "missing" if missing else "partial" if partial else "complete",
                "sourceResourceId": None if missing else resource,
                "accessRulesVersion": None if missing or partial else "1",
                "observedAt": None if missing else TIME, "items": None if missing or partial else [],
                "nextLink": None, "evidence": [],
            }
        return result

    observations = {}
    evidence_links = {}
    for scene in ("desired", "unknown", "breached", "pending"):
        observation = observation_for(scene)
        complete = scene in {"desired", "breached"}
        evidence = put(f"{scene}-evidence", {
            **metadata("evidence-reference", f"EVIDENCE-NSP-{scene.upper()}-V3", "1.0.0"),
            "origin": "fixture", "evidenceState": "fresh" if complete else "partial",
            "collector": {"collectorId": "COLLECTOR-NSP-AGGREGATE-FIXTURE", "version": "3.0.0"},
            "observedAt": TIME, "retrievedAt": TIME, "validUntil": "2026-09-13T02:05:00Z",
            "eligibility": "ineligible", "sourceChecksum": semantic_checksum(observation),
            "completeness": "complete" if complete else "partial",
            "supportedAssertionIds": list(scenario["cp01Verifier"]["assertionIds"]),
        })
        evidence_link = {"reference": link("E01", evidence), "origin": "fixture"}
        for slot in observation.values():
            if slot["observedAt"] is not None:
                slot["evidence"] = [deepcopy(evidence_link)]
        observations[scene] = observation
        evidence_links[scene] = evidence_link
    operation = put("baseline-operation", {
        **metadata("sandbox-operation-receipt", "ART-OPERATION-NSP-FIXTURE-V3"),
        "operationId": "OPERATION-NSP-FIXTURE-V3", "operation": "deploy-baseline", "result": "acknowledged",
        "generationManifest": generation, "applicationReceipt": application, "desiredStateChecksum": scenario["desiredStateChecksum"],
        "deployedResources": {"storageId": STORAGE, "perimeterId": PERIMETER, "profileId": PROFILE, "associationId": ASSOCIATION},
        "providerOperationId": "fixture-only-no-provider-operation", "operatorConsentId": None,
        "actor": {"kind": "system", "actorId": "SYSTEM-NSP-FIXTURE"}, "startedAt": TIME, "completedAt": TIME,
        "evidence": [evidence_links["desired"]], "correlationId": "CORRELATION-NSP-FIXTURE-V3",
    })
    binding = put("binding-established-fixture", {
        **metadata("runtime-binding", "ART-BINDING-NSP-FIXTURE-V3"),
        "bindingId": "BINDING-NSP-FIXTURE-V3", "componentId": "CMP-CLAIMS-STORE", "bindingState": "bound",
        "resources": {"storageId": STORAGE, "perimeterId": PERIMETER, "profileId": PROFILE, "associationId": ASSOCIATION, "configurationId": CONFIGURATION, "perimeterGuid": GUID},
        "operationReceipt": link("D13", operation), "generationManifest": generation, "applicationReceipt": application,
        "desiredStateChecksum": scenario["desiredStateChecksum"], "boundAt": TIME, "gaps": [],
    })
    unknown_binding = put("binding-unknown", {
        **metadata("runtime-binding", "ART-BINDING-UNKNOWN-V3"),
        "bindingId": "BINDING-UNKNOWN-V3", "componentId": "CMP-CLAIMS-STORE", "bindingState": "unknown",
        "resources": {key: None for key in binding["resources"]},
        "operationReceipt": None, "generationManifest": None, "applicationReceipt": None,
        "desiredStateChecksum": None, "boundAt": None, "gaps": ["nsp-binding-unavailable"],
    })
    snapshots = {}
    evaluations = {}
    for scene in ("desired", "unknown", "breached", "pending"):
        source_binding = unknown_binding if scene == "unknown" else binding
        snapshot = put(f"{scene}-snapshot", {
            **metadata("runtime-snapshot", f"ART-SNAPSHOT-NSP-{scene.upper()}-V3"),
            "snapshotId": f"SNAPSHOT-NSP-{scene.upper()}-V3", "binding": link("D14", source_binding),
            "collectedAt": TIME, "evidenceWindow": {"from": TIME, "to": TIME},
            "completeness": "complete" if scene in {"desired", "breached"} else "partial",
            "observation": observations[scene], "evidence": [evidence_links[scene]],
            "missingEvidenceKinds": scenario["cp01Verifier"]["requiredEvidenceKinds"][1:] if scene == "unknown" else [],
            "collectionErrors": ["nsp-relationship-evidence-missing"] if scene == "unknown" else [],
        })
        snapshots[scene] = snapshot
        # Authored outputs, not a runtime evaluator. Even the desired fixture is unassessed.
        status = "breached" if scene == "breached" else "unknown"
        reason = {
            "desired": "fixture-not-evaluated", "unknown": "nsp-relationship-evidence-missing",
            "breached": "association-mode-not-enforced", "pending": "nsp-configuration-pending",
        }[scene]
        evaluation = put(f"{scene}-evaluation", {
            **metadata("promise-evaluation", f"ART-EVALUATION-NSP-{scene.upper()}-V3"),
            "evaluationId": f"EVALUATION-NSP-{scene.upper()}-V3", "promiseId": "CP-01", "phase": "runtime",
            "status": status, "reasonCode": reason, "evaluatedAt": TIME, "evidenceWindow": {"from": TIME, "to": TIME},
            "promiseContract": link("D03", promises), "binding": link("D14", source_binding), "runtimeSnapshot": link("D15", snapshot),
            "verifier": {"verifierId": scenario["cp01Verifier"]["verifierId"], "version": "3.0.0", "checksum": scenario["verifierChecksum"]},
            "predicateResults": [
                {"predicateId": "PRED-NSP-ENFORCED-ASSOCIATION", "result": "fail", "reasonCode": reason, "evidence": [evidence_links[scene]]}
            ] if scene == "breached" else [],
            "evidence": [evidence_links[scene]], "findingId": "FINDING-NSP-FIXTURE-V3" if scene == "breached" else None,
            "notApplicableDecision": None, "boundaryEvidence": None,
            "assuranceScope": "observed-management-plane-configuration-only",
        })
        evaluations[scene] = evaluation
    finding = put("breached-finding", {
        **metadata("drift-finding", "ART-FINDING-NSP-FIXTURE-V3"),
        "findingId": "FINDING-NSP-FIXTURE-V3", "promiseId": "CP-01", "ruleId": scenario["cp01Verifier"]["verifierId"],
        "componentId": "CMP-CLAIMS-STORE", "resourceId": STORAGE, "severity": "high", "status": "open",
        "reasonCode": "association-mode-not-enforced", "customerImpact": scenario["promises"][0]["customerImpact"],
        "baseline": link("D14", binding), "runtimeSnapshot": link("D15", snapshots["breached"]), "evaluation": link("D17", evaluations["breached"]),
        "proposedCorrection": None, "restorationOperation": None, "evidence": [evidence_links["breached"]],
        "firstObservedAt": TIME, "lastObservedAt": TIME, "correlationId": "CORRELATION-NSP-FIXTURE-V3",
    })

    def projection(kind, artifact_id, evidence):
        return {
            **metadata(kind, artifact_id), "logicalRevision": 0, "asOf": TIME, "scenarioOrigin": "fixture",
            "evidence": deepcopy(evidence), "currentWork": [], "allowedActions": [], "blockers": [], "artifactRefs": [],
        }

    for scene in ("desired", "unknown", "breached", "pending"):
        snapshot = snapshots[scene]
        evaluation = evaluations[scene]
        ev = [evidence_links[scene]]
        risk = put(f"{scene}-operations", {
            **projection("operations-risk", f"ART-OPERATIONS-NSP-{scene.upper()}-V3", ev),
            "riskState": "known-risk" if scene == "breached" else "verification-pending" if scene == "pending" else "unknown",
            "headline": {
                "desired": "Desired NSP configuration fixture; not evaluated as live proof",
                "unknown": "SecuredByPerimeter alone does not establish the NSP boundary",
                "breached": "The observed association does not match Enforced mode",
                "pending": "Effective NSP configuration and complete rules are pending",
            }[scene],
            "customerImpact": scenario["promises"][0]["customerImpact"],
            "binding": snapshot["binding"], "snapshot": link("D15", snapshot),
            "findingRefs": [link("D16", finding)] if scene == "breached" else [],
            "evaluationRefs": [link("D17", evaluation)],
            "restoration": {"status": "not-requested", "operationReceipt": None, "verificationEvaluation": None},
        })
        nodes = [
            {"nodeId": "NODE-INTENT", "nodeType": "intent", "label": "Claims intent",
             "source": {"kind": "scenario", "scenario": deepcopy(identity), "entityId": scenario["intentId"]}},
            {"nodeId": "NODE-CP01", "nodeType": "promise", "label": "NSP-protected claims storage",
             "source": {"kind": "scenario", "scenario": deepcopy(identity), "entityId": "CP-01"}},
            {"nodeId": "NODE-EVALUATION", "nodeType": "evaluation", "label": "Fixture CP-01 assessment",
             "source": {"kind": "artifact", "reference": link("D17", evaluation)}},
        ]
        for member in ("storage", "perimeter", "profile", "association", "configuration"):
            slot = snapshot["observation"][member]
            source = {
                "kind": "nsp-observation", "snapshot": link("D15", snapshot), "member": member,
                "observationState": slot["observationState"],
            } if slot["observationState"] == "complete" and slot["value"] is not None else {
                "kind": "gap", "expectedMember": member, "reasonCode": "nsp-member-not-established",
            }
            nodes.append({"nodeId": "NODE-" + member.upper(), "nodeType": member, "label": "NSP " + member, "source": source})
        edges = [
            {"edgeId": "EDGE-INTENT-PROMISE", "fromNodeId": "NODE-INTENT", "toNodeId": "NODE-CP01", "relation": "defines", "status": "supported",
             "support": {"kind": "scenario-link", "scenario": deepcopy(identity), "fromEntityId": scenario["intentId"], "toEntityId": "CP-01"}},
            {"edgeId": "EDGE-EVALUATION-PROMISE", "fromNodeId": "NODE-EVALUATION", "toNodeId": "NODE-CP01", "relation": "evaluates", "status": "broken" if scene == "breached" else "gap",
             "support": {"kind": "evaluation", "reference": link("D17", evaluation), "promiseId": "CP-01"}},
        ]
        node_sources = {node["nodeType"]: node["source"] for node in nodes}
        for first, second, relation in (
            ("association", "storage", "associated-storage"), ("association", "profile", "associated-profile"),
            ("profile", "perimeter", "profile-of"), ("configuration", "storage", "configuration-for"),
            ("configuration", "association", "effective-association"), ("configuration", "profile", "effective-profile"),
        ):
            gap = node_sources[first]["kind"] == "gap" or node_sources[second]["kind"] == "gap"
            edges.append({
                "edgeId": "EDGE-" + relation.upper(), "fromNodeId": "NODE-" + first.upper(), "toNodeId": "NODE-" + second.upper(),
                "relation": relation, "status": ("pending" if scene == "pending" else "gap") if gap else "supported",
                "support": {"kind": "gap", "reasonCode": "nsp-member-not-established"} if gap else {
                    "kind": "nsp-relationship", "snapshot": link("D15", snapshot), "fromMember": first, "toMember": second,
                },
            })
        graph = put(f"{scene}-graph", {
            **projection("intent-continuity-graph", f"ART-GRAPH-NSP-{scene.upper()}-V3", ev),
            "nodes": nodes, "edges": edges,
            "listEntries": [
                {"nodeId": node["nodeId"], "relatedEdgeIds": [edge["edgeId"] for edge in edges if node["nodeId"] in {edge["fromNodeId"], edge["toNodeId"]}]}
                for node in nodes
            ],
        })
        overview = projection("experience-overview", f"ART-OVERVIEW-NSP-{scene.upper()}-V3", ev)
        overview.update(
            businessGoal=scenario["businessIntent"],
            coverage={
                "phase": "runtime", "assessmentState": "partial", "verifiedCount": None, "applicableCount": None,
                "rows": [
                    {"promiseId": pid, "confirmed": False, "status": evaluation["status"] if pid == "CP-01" else "unknown",
                     "reasonCode": evaluation["reasonCode"] if pid == "CP-01" else "evidence-not-collected",
                     "evaluation": link("D17", evaluation) if pid == "CP-01" else None}
                    for pid in promise_ids
                ],
            },
            operationsRisk=deepcopy(risk), continuityGraph=deepcopy(graph),
            artifactRefs=[link("P05", risk), link("P06", graph)],
        )
        put(f"{scene}-overview", overview)

    module = {"moduleId": "MODULE-NSP-FIXTURE-V3", "version": "3.0.0", "checksum": semantic_checksum({"fixture": "NSP template descriptor, not deployed bytes"})}
    component_ids = scenario["boundaryComponentIds"]
    components = []
    for kind, resource_type in (
        ("storage", "Microsoft.Storage/storageAccounts"),
        ("perimeter", "Microsoft.Network/networkSecurityPerimeters"),
        ("profile", "Microsoft.Network/networkSecurityPerimeters/profiles"),
        ("association", "Microsoft.Network/networkSecurityPerimeters/resourceAssociations"),
    ):
        components.append({
            "componentId": component_ids[kind], "kind": kind, "resourceType": resource_type,
            "parentComponentId": component_ids["perimeter"] if kind in {"profile", "association"} else None,
            "storageComponentId": component_ids["storage"] if kind == "association" else None,
            "profileComponentId": component_ids["profile"] if kind == "association" else None,
            "storageConfiguration": deepcopy(scenario["desiredStorageConfiguration"]) if kind == "storage" else None,
            "nspConfiguration": deepcopy(scenario["desiredNspConfiguration"]) if kind in {"profile", "association"} else None,
            "module": deepcopy(module), "promiseIds": promise_ids if kind == "storage" else ["CP-01"],
            "requirementIds": requirement_ids if kind == "storage" else ["REQ-CLAIMS-ACCESS"],
        })
    options = [
        {
            "optionId": "OPTION-" + candidate["candidateId"], "title": "V3 catalog candidate " + candidate["candidateId"],
            "summary": "Synthetic catalog facts; RPO and human decisions remain unconfirmed.",
            "catalogFacts": deepcopy(candidate), "components": deepcopy(components),
            "relationships": [
                {"fromComponentId": component_ids["association"], "toComponentId": component_ids["storage"], "relation": "associated-storage"},
                {"fromComponentId": component_ids["association"], "toComponentId": component_ids["profile"], "relation": "associated-profile"},
                {"fromComponentId": component_ids["profile"], "toComponentId": component_ids["perimeter"], "relation": "profile-of"},
            ], "assumptions": [], "unresolvedItems": ["Actual RPO confirmation and approved resource binding are still required."],
        }
        for candidate in scenario["candidates"]
    ]
    proposal = put("architecture-proposal", {
        **metadata("architecture-proposal", "ART-PROPOSAL-NSP-V3"), "proposalId": "PROPOSAL-NSP-V3",
        "authority": "proposal-only", "producer": {"kind": "agent", "actorId": "AGENT-NSP-FIXTURE"},
        "origin": "fixture", "invocationReceipt": None,
        "catalog": {"catalogId": scenario["catalog"]["catalogId"], "version": "3.0.0", "checksum": semantic_checksum({"catalog": scenario["catalog"], "candidates": scenario["candidates"]})},
        "options": options, "recommendedOptionId": None, "rationale": "Fixture proposal only; no eligibility or approval is computed.",
    }, {"requirements": bare(requirements), "promiseContract": link("D03", promises)})
    review = {
        **metadata("review-gate-evaluation", "ART-REVIEW-NSP-V3"), "subjectContractId": "D04",
        "review": {
            "reviewId": "REVIEW-NSP-V3", "deterministicStatus": "blocked", "inferenceStatus": "blocked",
            "findings": [], "optionAssessments": [],
        },
        "gate": {"gateId": "design-ready", "version": "1.0.0", "effectiveStatus": "blocked", "approvalStatus": "pending", "approval": None, "evaluatedAt": TIME, "expectedRevision": 0, "boundChecksums": {"scenario": scenario["stateChecksum"]}},
    }
    review = put("review-pending", review, {"subject": bare(proposal), "requirements": bare(requirements), "promiseContract": link("D03", promises)})
    model = put("architecture-model", {
        **metadata("architecture-model", "ART-MODEL-NSP-V3"), "architectureId": "MODEL-NSP-V3", "status": "blocked",
        "options": deepcopy(options), "recommendedOptionId": None, "selectedOptionId": None, "decision": None,
    }, {"sourceProposal": bare(proposal), "review": bare(review), "promiseContract": link("D03", promises)})
    adr = put("adr-proposed", {
        **metadata("architecture-decision-record", "ART-ADR-NSP-V3"), "adrId": "ADR-NSP-V3", "status": "proposed",
        "title": "NSP-protected claims storage", "context": "No actual option selection or product approval has occurred.",
        "consideredOptionIds": ["OPTION-A", "OPTION-B"], "decisionReceipt": None,
    }, {"architecture": bare(model), "review": bare(review), "requirements": bare(requirements), "promiseContract": link("D03", promises)})
    put("approval-pending", {
        **metadata("approval", "ART-APPROVAL-PENDING-NSP-V3"), "approvalId": "APPROVAL-PENDING-FIXTURE-V3",
        "approvalClass": "design", "status": "pending",
        "binding": {"subjectContractId": "D06", "subject": bare(adr), "capability": "approve-design", "actionId": "approve-design-v3", "expectedRevision": 0, "gateId": "design-ready", "boundChecksums": {"decision": adr["stateChecksum"]}},
        "issuedAt": TIME, "expiresAt": "2026-09-13T03:00:00Z", "decidedAt": None, "decisionId": None, "actor": None, "attentionEvent": None,
    }, {"gateEvaluation": bare(review)})
    put("generation-draft", {
        **metadata("generation-contract", "ART-GENERATION-DRAFT-NSP-V3"), "generationId": "GENERATION-DRAFT-NSP-V3",
        "status": "draft", "selectedOptionId": "OPTION-B", "renderMode": "approved-templates-only", "outputRootId": "ROOT-NSP-DRAFT-FIXTURE",
        "modules": [module], "outputs": [{"relativePath": "infra/nsp.bicep", "kind": "bicep", "template": module, "componentIds": list(component_ids.values()), "promiseIds": promise_ids}],
        "desiredStorageConfiguration": deepcopy(scenario["desiredStorageConfiguration"]),
        "desiredNspConfiguration": deepcopy(scenario["desiredNspConfiguration"]), "desiredStateChecksum": scenario["desiredStateChecksum"],
    }, {"requirements": bare(requirements), "promiseContract": link("D03", promises), "architecture": bare(model), "decision": bare(adr), "gateEvaluation": bare(review), "approval": None})
    validate_v3_reference_integrity(records.values(), {run["runId"]: run}, scenario, external)
    return {
        "exampleOrigin": "fixture", "schemaProfile": "2.0.0",
        "description": "New V3 contract fixtures only: no live IDs, provider reads/deployments, approvals, or relabelled V2 evidence. Desired sources are not automatically evaluated.",
        "scenario": identity, "runManifest": run, "asOf": TIME, "externalReferences": external,
        "records": [{"name": name, "contractId": identify_contract(value, schema_version=value["schemaVersion"]), "schemaVersion": value["schemaVersion"], "value": value} for name, value in records.items()],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = (json.dumps(build_examples(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != data:
            print("V3 fixture bytes differ", file=sys.stderr)
            return 1
        print("V3 scenario, versioned references, normalized observations and fixture bytes match.")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(data)
        print(f"Wrote fixture-only V3 records: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
