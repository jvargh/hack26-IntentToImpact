"""Project a focused lineage graph from trusted, already evaluated artifacts."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from tools.contracts.integrity import (
    ReferenceIntegrityError,
    scenario_identity,
    semantic_checksum,
    validate_reference_integrity,
    validate_scenario,
)
from tools.contracts.validate import identify_contract, validate_contract


EVALUATION_EDGE_STATUS = {
    "breached": "broken",
    "contradicted": "broken",
    "unknown": "gap",
    "stale": "gap",
    "verified": "supported",
    "design-supported": "supported",
    "implementation-validated": "supported",
    "not-applicable": "gap",
}
NODE_TYPES = {
    "D03": "promise",
    "D13": "baseline",
    "D14": "baseline",
    "D15": "runtime-snapshot",
    "D16": "finding",
    "D17": "evaluation",
    "E01": "evidence",
}


def build_graph(
    *,
    run: dict[str, Any],
    scenario: dict[str, Any],
    documents: list[dict[str, Any]],
    promise_id: str,
    logical_revision: int,
    as_of: str,
    evaluation_id: str | None = None,
    restoration_pending: bool = False,
    external_references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """No I/O or predicate evaluation; caller supplies authorized source records."""
    validate_contract(run, "D22")
    validate_scenario(scenario)
    if type(logical_revision) is not int or logical_revision < 0:
        raise ValueError("logical_revision must be a nonnegative integer")
    if type(restoration_pending) is not bool:
        raise ValueError("restoration_pending must be an explicit boolean")
    timestamp = datetime.fromisoformat(as_of)
    if timestamp.tzinfo is None:
        raise ValueError("as_of must include a timezone")
    identity = scenario_identity(scenario)
    if {key: run[key] for key in identity} != identity:
        raise ReferenceIntegrityError("Run and scenario do not match")
    if run["stateChecksum"] != semantic_checksum(run):
        raise ReferenceIntegrityError("Run checksum does not match")
    promises = {item["promiseId"]: item for item in scenario["promises"]}
    if promise_id not in promises:
        raise ValueError("Promise does not exist in the current scenario")
    promise = promises[promise_id]
    if len(promise["componentIds"]) != 1:
        raise ValueError("This focused projection requires one declared component")
    records = deepcopy(documents)
    external = deepcopy(external_references or [])
    runs = {run["runId"]: run}
    validate_reference_integrity(records, runs, scenario, external)
    index = {(identify_contract(record), record["artifactId"]): record for record in records}
    selected = None
    if evaluation_id is not None:
        selected = index.get(("D17", evaluation_id))
        if selected is None or selected["promiseId"] != promise_id:
            raise ReferenceIntegrityError("Selected evaluation is missing or belongs to another promise")
        if timestamp < datetime.fromisoformat(selected["evaluatedAt"]):
            raise ReferenceIntegrityError("Projection cutoff predates the selected evaluation")
        if selected["phase"] == "runtime" and selected["status"] == "verified" and (
            selected["binding"] is None
            or selected["runtimeSnapshot"] is None
            or not selected["evidence"]
        ):
            raise ReferenceIntegrityError("A verified runtime graph requires its supporting references")
    if restoration_pending and (
        selected is None or selected["phase"] != "runtime" or selected["status"] != "breached"
    ):
        raise ValueError("Pending restoration requires an existing runtime breach")

    def reference(contract_id: str, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "contractId": contract_id,
            "artifact": {"artifactId": record["artifactId"], "checksum": record["stateChecksum"]},
            "scenario": deepcopy(identity),
        }

    def scenario_node(node_id: str, node_type: str, entity_id: str, label: str) -> dict[str, Any]:
        return {
            "nodeId": node_id, "nodeType": node_type, "label": label,
            "source": {"kind": "scenario", "scenario": deepcopy(identity), "entityId": entity_id},
        }

    nodes = [
        scenario_node("NODE-INTENT", "intent", scenario["intentId"], "Customer intent (scenario)"),
        scenario_node("NODE-PROMISE", "promise", promise_id, f"{promise_id}: customer promise"),
        scenario_node(
            "NODE-COMPONENT", "component", promise["componentIds"][0],
            "Planned component: claims storage",
        ),
    ]
    edges = [
        {
            "edgeId": "EDGE-INTENT-PROMISE", "fromNodeId": "NODE-INTENT",
            "toNodeId": "NODE-PROMISE", "relation": "defines", "status": "supported",
            "support": {
                "kind": "scenario-link", "scenario": deepcopy(identity),
                "fromEntityId": scenario["intentId"], "toEntityId": promise_id,
            },
        },
        {
            "edgeId": "EDGE-PROMISE-COMPONENT", "fromNodeId": "NODE-PROMISE",
            "toNodeId": "NODE-COMPONENT", "relation": "implemented-by", "status": "supported",
            "support": {
                "kind": "scenario-link", "scenario": deepcopy(identity),
                "fromEntityId": promise_id, "toEntityId": promise["componentIds"][0],
            },
        },
    ]
    node_refs: dict[str, dict[str, Any]] = {}

    def artifact_node(node_id: str, link: dict[str, Any], label: str) -> dict[str, Any]:
        key = link["contractId"], link["artifact"]["artifactId"]
        document = index.get(key)
        if document is None:
            raise ReferenceIntegrityError("Supported graph nodes require loaded canonical records")
        node_type = NODE_TYPES.get(link["contractId"])
        if node_type is None:
            raise ValueError("Unsupported focused graph source type")
        nodes.append({
            "nodeId": node_id, "nodeType": node_type, "label": label[:240],
            "source": {"kind": "artifact", "reference": deepcopy(link)},
        })
        node_refs[node_id] = deepcopy(link)
        return document

    def artifact_edge(edge_id: str, from_id: str, to_id: str) -> None:
        edges.append({
            "edgeId": edge_id, "fromNodeId": from_id, "toNodeId": to_id,
            "relation": "references", "status": "supported",
            "support": {
                "kind": "artifact-link", "source": node_refs[from_id], "target": node_refs[to_id],
            },
        })

    def gap(node_id: str, contract: str, label: str, reason: str, from_id: str, pending: bool = False) -> None:
        nodes.append({
            "nodeId": node_id, "nodeType": NODE_TYPES[contract], "label": label,
            "source": {"kind": "gap", "expectedContractId": contract, "reasonCode": reason},
        })
        edges.append({
            "edgeId": f"EDGE-{node_id}", "fromNodeId": from_id, "toNodeId": node_id,
            "relation": "references", "status": "pending" if pending else "gap",
            "support": {"kind": "gap", "reasonCode": reason},
        })

    evidence = deepcopy(selected["evidence"]) if selected is not None else []
    artifact_refs: list[dict[str, Any]] = []
    blockers = []
    if selected is None:
        gap(
            "NODE-EVALUATION-GAP", "D17", "Runtime evaluation unavailable",
            "evaluation-missing", "NODE-PROMISE",
        )
        gap(
            "NODE-BASELINE-GAP", "D14", "Deployment binding unavailable",
            "binding-missing", "NODE-COMPONENT",
        )
        blockers.append({"code": "evaluation-missing", "message": "No evaluation supplied; runtime status is not inferred."})
    else:
        property_by_id = {
            item["predicateId"]: item["property"] for item in scenario["cp01Verifier"]["predicates"]
        }
        failed = [
            property_by_id[result["predicateId"]]
            for result in selected["predicateResults"]
            if result["result"] == "fail" and result["predicateId"] in property_by_id
        ]
        label = f"{promise_id}: {selected['status']}"
        if failed:
            label += " - " + ", ".join(failed)
        selected_ref = reference("D17", selected)
        artifact_node("NODE-EVALUATION", selected_ref, label)
        edges.append({
            "edgeId": "EDGE-EVALUATION-PROMISE", "fromNodeId": "NODE-EVALUATION",
            "toNodeId": "NODE-PROMISE", "relation": "evaluates",
            "status": EVALUATION_EDGE_STATUS[selected["status"]],
            "support": {"kind": "evaluation", "reference": selected_ref, "promiseId": promise_id},
        })
        artifact_refs.append(selected_ref)
        if selected["runtimeSnapshot"] is not None:
            snapshot = artifact_node(
                "NODE-SNAPSHOT", selected["runtimeSnapshot"], "Observed configuration snapshot"
            )
            artifact_edge("EDGE-EVALUATION-SNAPSHOT", "NODE-EVALUATION", "NODE-SNAPSHOT")
            if snapshot["binding"] is not None:
                artifact_node("NODE-BASELINE", snapshot["binding"], "Acknowledged deployment binding")
                artifact_edge("EDGE-SNAPSHOT-BASELINE", "NODE-SNAPSHOT", "NODE-BASELINE")
            else:
                gap("NODE-BASELINE-GAP", "D14", "Deployment binding unavailable", "binding-missing", "NODE-SNAPSHOT")
        else:
            gap("NODE-SNAPSHOT-GAP", "D15", "Runtime observation unavailable", "snapshot-missing", "NODE-EVALUATION")
        for position, link in enumerate(evidence):
            node_id = f"NODE-EVIDENCE-{position + 1}"
            artifact_node(node_id, link["reference"], f"Configuration evidence ({link['origin']})")
            artifact_edge(f"EDGE-EVALUATION-EVIDENCE-{position + 1}", "NODE-EVALUATION", node_id)
        if selected["status"] in ("unknown", "stale"):
            blockers.append({"code": selected["reasonCode"], "message": "The source evaluation is not verified."})
        if restoration_pending:
            gap(
                "NODE-RESTORATION-PENDING", "D17", "Fresh restoration verification pending",
                "fresh-evidence-required", "NODE-PROMISE", pending=True,
            )
    context = {
        "runId": run["runId"], "caseId": run["caseId"], "logicalRevision": logical_revision,
        "promiseId": promise_id, "evaluationId": evaluation_id, "asOf": as_of,
        "restorationPending": restoration_pending,
    }
    graph = {
        "schemaVersion": "1.0.0", "artifactType": "intent-continuity-graph",
        "artifactId": "GRAPH-" + semantic_checksum(context).split(":", 1)[1][:24],
        "runId": run["runId"], "caseId": run["caseId"], "scope": deepcopy(run["scope"]),
        "caseRevisionAtWrite": logical_revision, "logicalRevision": logical_revision,
        "createdAt": as_of, "updatedAt": as_of, "asOf": as_of,
        "derivedFrom": {
            "runManifest": run["stateChecksum"], "scenario": scenario["stateChecksum"],
            **({"evaluation": selected["stateChecksum"]} if selected is not None else {}),
        },
        "scenario": identity, "runMode": run["runMode"], "purpose": run["purpose"],
        "scenarioOrigin": scenario["scenarioOrigin"], "evidence": evidence,
        "currentWork": [], "allowedActions": [], "blockers": blockers, "artifactRefs": artifact_refs,
        "nodes": nodes, "edges": edges,
        "listEntries": [
            {
                "nodeId": node["nodeId"],
                "relatedEdgeIds": [
                    edge["edgeId"] for edge in edges
                    if node["nodeId"] in (edge["fromNodeId"], edge["toNodeId"])
                ],
            }
            for node in nodes
        ],
    }
    graph["stateChecksum"] = semantic_checksum(graph)
    validate_contract(graph, "P06")
    validate_reference_integrity([*records, graph], runs, scenario, external)
    return graph
