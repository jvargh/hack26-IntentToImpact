"""Structural checksum, scenario and reference integrity; no predicate evaluation or policy."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Any, Iterable

from .validate import fragment_validator, identify_contract, validate_contract


class ReferenceIntegrityError(ValueError):
    pass


def semantic_checksum(value: dict[str, Any]) -> str:
    payload = {key: item for key, item in value.items() if key != "stateChecksum"}
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n"
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def scenario_identity(scenario: dict[str, Any]) -> dict[str, str]:
    return {
        "scenarioId": scenario["scenarioId"],
        "scenarioVersion": scenario["scenarioVersion"],
        "scenarioHash": scenario["stateChecksum"],
    }


def assert_scenario_identity_unchanged(old: dict[str, Any], new: dict[str, Any]) -> None:
    fragment_validator("scenario", "ScenarioIdentity").validate(old)
    fragment_validator("scenario", "ScenarioIdentity").validate(new)
    if old != new:
        raise ReferenceIntegrityError("Scenario ID/version/hash mismatch; create a new scenario-bound run")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReferenceIntegrityError(message)


def validate_scenario(value: dict[str, Any]) -> None:
    validate_contract(value, "SCENARIO-V2")
    _require(value["stateChecksum"] == semantic_checksum(value), "Scenario content checksum mismatch")
    desired_hash = semantic_checksum(value["desiredStorageConfiguration"])
    for declared in (
        value["desiredStateChecksum"],
        value["baselineCriteria"]["desiredStateChecksum"],
        value["restorationCriteria"]["desiredStateChecksum"],
    ):
        _require(declared == desired_hash, "Desired-state checksum mismatch")
    predicates = value["cp01Verifier"]["predicates"]
    properties = [item["property"] for item in predicates]
    _require(
        len(set(properties)) == 4 and set(properties) == set(value["desiredStorageConfiguration"]),
        "CP-01 must reference each desired property exactly once",
    )
    cp01 = next(item for item in value["promises"] if item["promiseId"] == "CP-01")
    _require(cp01["verifierIds"] == [value["cp01Verifier"]["verifierId"]], "CP-01 verifier linkage mismatch")
    _require(cp01["componentIds"] == [value["componentId"]], "CP-01 component linkage mismatch")
    _require(cp01["requiredEvidenceKinds"] == value["cp01Verifier"]["requiredEvidenceKinds"], "CP-01 evidence-kind linkage mismatch")


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _is_link(value: dict[str, Any]) -> bool:
    return set(value) == {"contractId", "artifact", "scenario"}


def _key(reference: dict[str, Any]) -> tuple[str, str]:
    return reference["contractId"], reference["artifact"]["artifactId"]


def validate_reference_integrity(
    documents: Iterable[dict[str, Any]],
    runs: dict[str, dict[str, Any]],
    scenario: dict[str, Any],
    external_references: Iterable[dict[str, Any]] = (),
) -> None:
    """Validate a closed set of records against trusted run/artifact inputs.

    External D10/D11/D12 references are opaque facts validated by their future owning
    engines. They cannot serve as graph-node proof here without a loaded canonical
    record. Inputs being structurally valid does not authenticate their producer.
    """
    validate_scenario(scenario)
    expected = scenario_identity(scenario)
    records = list(documents)
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for document in records:
        contract_id = identify_contract(document)
        validate_contract(document, contract_id)
        key = contract_id, document["artifactId"]
        _require(key not in index, f"Duplicate artifact: {key}")
        index[key] = document
        _require(document["stateChecksum"] == semantic_checksum(document), f"Artifact checksum mismatch: {key}")
        run_id = document["runId"]
        _require(run_id in runs, f"Missing trusted run manifest: {run_id}")
        run = runs[run_id]
        validate_contract(run, "D22")
        _require(run["runId"] == run_id, "Run manifest index mismatch")
        _require(run["stateChecksum"] == semantic_checksum(run), "Run manifest checksum mismatch")
        actual_identity = {name: run[name] for name in ("scenarioId", "scenarioVersion", "scenarioHash")}
        assert_scenario_identity_unchanged(actual_identity, expected)
        for field in ("caseId", "scope"):
            _require(document[field] == run[field], f"Artifact/run {field} mismatch")
        if "scenario" in document:
            assert_scenario_identity_unchanged(document["scenario"], expected)
            _require(document["runMode"] == run["runMode"], "Artifact/run mode mismatch")
            _require(document["purpose"] == run["purpose"], "Artifact/run purpose mismatch")

    external = {}
    for reference in external_references:
        fragment_validator("risk", "ArtifactLink").validate(reference)
        _require(reference["contractId"] in {"D10", "D11", "D12"}, "Only undispatched D10/D11/D12 may be opaque external references")
        assert_scenario_identity_unchanged(reference["scenario"], expected)
        _require(_key(reference) not in external, "Duplicate external reference")
        external[_key(reference)] = reference

    def resolve(reference: dict[str, Any], *, loaded: bool = False) -> dict[str, Any] | None:
        fragment_validator("risk", "ArtifactLink").validate(reference)
        assert_scenario_identity_unchanged(reference["scenario"], expected)
        key = _key(reference)
        if key not in index:
            _require(not loaded and external.get(key) == reference, f"Unresolved artifact reference: {key}")
            return None
        document = index[key]
        _require(document["stateChecksum"] == reference["artifact"]["checksum"], f"Reference checksum mismatch: {key}")
        return document

    for document in records:
        for value in _walk(document):
            if _is_link(value):
                target = resolve(value)
                if target is not None:
                    for field in ("runId", "caseId", "scope"):
                        _require(target[field] == document[field], f"Cross-context reference {field} mismatch")
            if set(value) == {"reference", "origin"}:
                evidence = resolve(value["reference"], loaded=True)
                _require(evidence["origin"] == value["origin"], "Evidence origin mismatch")
            if "evidenceWindow" in value:
                window = value["evidenceWindow"]
                _require(
                    datetime.fromisoformat(window["from"]) <= datetime.fromisoformat(window["to"]),
                    "Evidence window is reversed",
                )
            if value.get("artifactType") in {"operations-risk", "intent-continuity-graph"}:
                _require(value["stateChecksum"] == semantic_checksum(value), "Embedded projection checksum mismatch")
                for field in ("runId", "caseId", "scope", "scenario", "runMode", "purpose"):
                    _require(value[field] == document[field], f"Embedded projection {field} mismatch")
        kind = document["artifactType"]
        if kind == "customer-promise-contract":
            canonical = {item["promiseId"]: item for item in scenario["promises"]}
            for promise in document["promises"]:
                source = canonical[promise["promiseId"]]
                for field in ("requirementIds", "componentIds", "verifierIds", "requiredEvidenceKinds"):
                    _require(promise[field] == source[field], f"Promise {field} linkage mismatch")
        elif kind == "runtime-binding" and document["bindingState"] == "bound":
            operation = resolve(document["operationReceipt"], loaded=True)
            _require(operation["result"] == "acknowledged", "Bound baseline must reference an acknowledged operation")
            _require(operation["operation"] in {"deploy-baseline", "restore"}, "Seed is not a deployed baseline")
            for field in ("generationManifest", "applicationReceipt", "desiredStateChecksum"):
                _require(document[field] == operation[field], f"Baseline {field} mismatch")
            _require(document["desiredStateChecksum"] == scenario["desiredStateChecksum"], "Baseline desired-state does not match scenario")
            _require(document["resourceId"] in operation["resourceIds"], "Baseline resource mismatch")
        elif kind == "runtime-snapshot":
            binding = resolve(document["binding"], loaded=True) if document["binding"] else None
            for observation in document["observations"]:
                if binding:
                    for field in ("resourceId", "componentId"):
                        _require(observation[field] == binding[field], f"Observation/baseline {field} mismatch")
                _require(all(item in document["evidence"] for item in observation["evidence"]), "Observation references unlisted snapshot evidence")
        elif kind == "promise-evaluation":
            promises = resolve(document["promiseContract"], loaded=True)
            promise = next(item for item in promises["promises"] if item["promiseId"] == document["promiseId"])
            _require(document["verifier"]["verifierId"] in promise["verifierIds"], "Evaluation verifier is not linked to its promise")
            if document["binding"]:
                binding = resolve(document["binding"], loaded=True)
                _require(binding["componentId"] in promise["componentIds"], "Evaluation baseline is not linked to its promise component")
            if document["promiseId"] == "CP-01":
                verifier = scenario["cp01Verifier"]
                _require(
                    document["verifier"]["version"] == verifier["version"]
                    and document["verifier"]["checksum"] == semantic_checksum(verifier),
                    "CP-01 verifier version/checksum mismatch",
                )
                predicate_ids = [item["predicateId"] for item in document["predicateResults"]]
                _require(
                    len(set(predicate_ids)) == len(predicate_ids)
                    and set(predicate_ids) <= {item["predicateId"] for item in verifier["predicates"]},
                    "CP-01 predicate linkage mismatch",
                )
            if document["runtimeSnapshot"]:
                snapshot = resolve(document["runtimeSnapshot"], loaded=True)
                _require(snapshot["binding"] == document["binding"], "Evaluation/snapshot baseline mismatch")
                _require(all(item in snapshot["evidence"] for item in document["evidence"]), "Evaluation references unlisted snapshot evidence")
            for predicate in document["predicateResults"]:
                _require(all(item in document["evidence"] for item in predicate["evidence"]), "Predicate references unlisted evaluation evidence")
                for item in predicate["evidence"]:
                    evidence = resolve(item["reference"], loaded=True)
                    _require(predicate["predicateId"] in evidence["supportedAssertionIds"], "Predicate evidence does not support its assertion ID")
        elif kind == "drift-finding" and document["evaluation"]:
            evaluation = resolve(document["evaluation"], loaded=True)
            _require(evaluation["promiseId"] == document["promiseId"], "Finding/evaluation promise mismatch")
            _require(evaluation["findingId"] in {None, document["findingId"]}, "Finding/evaluation stable ID mismatch")
            _require(evaluation["runtimeSnapshot"] == document["runtimeSnapshot"], "Finding/evaluation snapshot mismatch")
            _require(evaluation["binding"] == document["baseline"], "Finding/evaluation baseline mismatch")
        elif kind == "human-attention-event":
            event = resolve(document["sourceEvent"], loaded=True)
            human = event["actor"] if event["actor"]["kind"] == "human" else event.get("humanInitiator")
            _require(human is not None and human["actorId"] == document["actor"]["actorId"], "Human attention has no matching human source attribution")

        for value in _walk(document):
            if value.get("artifactType") == "intent-continuity-graph":
                _validate_graph(value, scenario, resolve)
            elif value.get("artifactType") == "operations-risk":
                restoration = value["restoration"]
                if restoration["status"] == "verified":
                    _require(restoration["verificationEvaluation"] is not None, "Restoration label requires an evaluation reference")
                    evaluation = resolve(restoration["verificationEvaluation"], loaded=True)
                    _require(evaluation["phase"] == "runtime" and evaluation["status"] == "verified", "Restoration label disagrees with its evaluation source")
            elif value.get("artifactType") == "experience-overview":
                rows = value["coverage"]["rows"]
                _require(len({row["promiseId"] for row in rows}) == len(rows), "Duplicate coverage promise")
                for row in rows:
                    if row["evaluation"]:
                        evaluation = resolve(row["evaluation"], loaded=True)
                        _require(evaluation["promiseId"] == row["promiseId"] and evaluation["status"] == row["status"] and evaluation["phase"] == "runtime", "Coverage row disagrees with its evaluation source")
                    else:
                        _require(row["status"] == "unknown", "Coverage success/risk label has no source evaluation")


def _validate_graph(graph, scenario, resolve) -> None:
    expected = scenario_identity(scenario)
    entities = {scenario["intentId"]: "intent"}
    pairs = set()
    for promise in scenario["promises"]:
        entities[promise["promiseId"]] = "promise"
        pairs.add((scenario["intentId"], promise["promiseId"], "defines"))
        for component in promise["componentIds"]:
            entities[component] = "component"
            pairs.add((promise["promiseId"], component, "implemented-by"))
    nodes = {node["nodeId"]: node for node in graph["nodes"]}
    _require(len(nodes) == len(graph["nodes"]), "Duplicate graph node ID")
    artifact_types = {
        "D03": {"promise"}, "D13": {"baseline"}, "D14": {"baseline"},
        "D15": {"runtime-snapshot"}, "D16": {"finding"}, "D17": {"evaluation"},
        "E01": {"evidence"}, "D11": {"correction"},
    }
    for node in nodes.values():
        source = node["source"]
        if source["kind"] == "scenario":
            assert_scenario_identity_unchanged(source["scenario"], expected)
            _require(entities.get(source["entityId"]) == node["nodeType"], "Unknown or mismatched scenario graph node")
        elif source["kind"] == "artifact":
            resolve(source["reference"], loaded=True)
            _require(node["nodeType"] in artifact_types.get(source["reference"]["contractId"], set()), "Graph node type disagrees with artifact source")
        else:
            _require(node["nodeType"] in artifact_types.get(source["expectedContractId"], set()), "Gap node type disagrees with expected contract")
    edges = {edge["edgeId"]: edge for edge in graph["edges"]}
    _require(len(edges) == len(graph["edges"]), "Duplicate graph edge ID")
    for edge in edges.values():
        _require(edge["fromNodeId"] in nodes and edge["toNodeId"] in nodes, "Graph edge has an unknown endpoint")
        source = nodes[edge["fromNodeId"]]["source"]
        target = nodes[edge["toNodeId"]]["source"]
        support = edge["support"]
        kind = support["kind"]
        if kind == "scenario-link":
            assert_scenario_identity_unchanged(support["scenario"], expected)
            _require(source["kind"] == target["kind"] == "scenario", "Scenario edge needs scenario endpoints")
            _require(source["entityId"] == support["fromEntityId"] and target["entityId"] == support["toEntityId"], "Scenario edge endpoint mismatch")
            _require((source["entityId"], target["entityId"], edge["relation"]) in pairs and edge["status"] == "supported", "Unsupported scenario graph link")
        elif kind == "artifact-link":
            _require(source["kind"] == target["kind"] == "artifact", "Artifact edge needs artifact endpoints")
            _require(source["reference"] == support["source"] and target["reference"] == support["target"], "Artifact edge endpoint mismatch")
            record = resolve(support["source"], loaded=True)
            _require(any(value == support["target"] for value in _walk(record) if _is_link(value)), "Graph source does not reference graph target")
            _require(edge["relation"] == "references" and edge["status"] == "supported", "Artifact reference edge cannot invent evaluation status")
        elif kind == "evaluation":
            _require(source["kind"] == "artifact" and source["reference"] == support["reference"], "Evaluation graph source mismatch")
            evaluation = resolve(support["reference"], loaded=True)
            _require(target["kind"] == "scenario" and target["entityId"] == support["promiseId"] == evaluation["promiseId"], "Evaluation graph promise mismatch")
            statuses = {
                "breached": "broken", "contradicted": "broken", "unknown": "gap", "stale": "gap",
                "verified": "supported", "design-supported": "supported", "implementation-validated": "supported",
                "not-applicable": "gap",
            }
            _require(edge["relation"] == "evaluates" and edge["status"] == statuses[evaluation["status"]], "Graph edge disagrees with source evaluation")
        else:
            _require(source["kind"] == "gap" or target["kind"] == "gap", "Missing-evidence edge needs an explicit gap endpoint")
            _require(edge["status"] in {"gap", "pending"} and edge["relation"] in {"references", "evaluates"}, "Gap edge cannot claim supported or broken proof")
    entries = {entry["nodeId"]: entry for entry in graph["listEntries"]}
    _require(len(entries) == len(graph["listEntries"]) and set(entries) == set(nodes), "Graph/list node mismatch")
    for node_id, entry in entries.items():
        incident = {edge["edgeId"] for edge in edges.values() if node_id in (edge["fromNodeId"], edge["toNodeId"])}
        _require(set(entry["relatedEdgeIds"]) == incident, "Graph/list edge mismatch")
