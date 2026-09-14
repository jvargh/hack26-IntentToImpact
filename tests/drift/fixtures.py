"""Fresh, labelled local test evidence derived from frozen contract examples."""

from copy import deepcopy
from dataclasses import replace
import json

from bootstrap import ROOT
from engines.drift import EvaluationInput
from state.case_store import seal
from tools.contracts.integrity import scenario_identity

AS_OF = "2026-09-12T17:05:00Z"


def link(contract_id, document, scenario):
    return {
        "contractId": contract_id,
        "artifact": {"artifactId": document["artifactId"], "checksum": document["stateChecksum"]},
        "scenario": scenario_identity(scenario),
    }


def refresh(inputs):
    """Rehash only test-owned values and update their exact reference chain."""
    scenario = inputs.scenario
    run = seal(inputs.run)
    evidence_values = deepcopy(inputs.evidence)
    if inputs.snapshot:
        source_hash = seal({
            "observations": [
                {key: value for key, value in observation.items() if key != "evidence"}
                for observation in inputs.snapshot["observations"]
            ],
        })["stateChecksum"]
        observed_ids = {
            item["reference"]["artifact"]["artifactId"]
            for item in inputs.snapshot["evidence"]
        }
        for item in evidence_values:
            if item["artifactId"] in observed_ids:
                item["sourceChecksum"] = source_hash
    evidence = tuple(seal(item) for item in evidence_values)
    evidence_by_id = {item["artifactId"]: item for item in evidence}

    def evidence_links(links):
        return [
            {"reference": link("E01", evidence_by_id[item["reference"]["artifact"]["artifactId"]], scenario),
             "origin": evidence_by_id[item["reference"]["artifact"]["artifactId"]]["origin"]}
            for item in links
        ]

    operations = []
    for item in inputs.operations:
        item = deepcopy(item)
        item["evidence"] = evidence_links(item["evidence"])
        operations.append(seal(item))
    binding = deepcopy(inputs.binding)
    if binding:
        if binding["operationReceipt"]:
            operation = next(item for item in operations if item["artifactId"] == binding["operationReceipt"]["artifact"]["artifactId"])
            binding["operationReceipt"] = link("D13", operation, scenario)
        binding = seal(binding)
    snapshot = deepcopy(inputs.snapshot)
    if snapshot:
        snapshot["binding"] = link("D14", binding, scenario) if binding else None
        snapshot["evidence"] = evidence_links(snapshot["evidence"])
        for observation in snapshot["observations"]:
            observation["evidence"] = evidence_links(observation["evidence"])
        snapshot = seal(snapshot)
    trusted = tuple(
        [link("E01", item, scenario) for item in evidence]
        + ([link("D15", snapshot, scenario)] if snapshot else [])
    )
    return replace(
        inputs, run=run, promise_contract=seal(inputs.promise_contract),
        binding=binding, snapshot=snapshot, evidence=evidence,
        operations=tuple(operations), trusted_sources=trusted,
    )


def fixture_input():
    examples = json.loads((ROOT / "contracts" / "examples" / "1.0.0" / "risk-examples.json").read_text())
    named = {record["name"]: record["value"] for record in examples["records"]}
    scenario = json.loads((ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json").read_text())
    snapshot = named["risk-snapshot"]
    snapshot["observations"][0]["properties"] = deepcopy(scenario["desiredStorageConfiguration"])
    evidence = [named["evidence-baseline"], named["evidence-breach"]]
    for item in evidence:
        # New test-owned source, never provider evidence or a change to the examples.
        item["eligibility"] = "eligible"
        item["collector"] = {"collectorId": "COLLECTOR-DRIFT-UNIT-FIXTURE", "version": "1.0.0"}
        item["sourceChecksum"] = seal({"properties": snapshot["observations"][0]["properties"]})["stateChecksum"]
    return refresh(EvaluationInput(
        run=examples["runManifest"], scenario=scenario,
        promise_contract=named["promise-contract"], binding=named["runtime-binding"],
        snapshot=snapshot, evidence=tuple(evidence),
        operations=(named["baseline-operation"],),
        external_references=tuple(examples["externalReferences"]),
    ))


def unicode_fixture_input():
    inputs = fixture_input()
    old_resource = inputs.binding["resourceId"]
    group = "rg-caf\u00e9-\u6f22"
    resource = old_resource.replace(
        f"/resourceGroups/{inputs.run['scope']['resourceGroup']}/",
        f"/resourceGroups/{group}/",
    )
    scope = {
        **inputs.run["scope"], "scopeId": "SCOPE-DRIFT-UNICODE",
        "resourceGroup": group, "resourceIds": [resource],
    }
    for document in (inputs.run, inputs.promise_contract, inputs.binding,
                     inputs.snapshot, *inputs.operations, *inputs.evidence):
        document.update(
            runId="RUN-DRIFT-UNICODE", caseId="CASE-DRIFT-UNICODE",
            scope=deepcopy(scope),
        )
    inputs.run["artifactId"] = "ART-RUN-DRIFT-UNICODE"
    inputs.promise_contract["promises"][0]["statement"] += " Contexte caf\u00e9 / \u6f22."
    inputs.binding["resourceId"] = resource
    for operation in inputs.operations:
        operation["resourceIds"] = [resource]
    for observation in inputs.snapshot["observations"]:
        observation["resourceId"] = resource
    return refresh(inputs)


def evaluate_arguments(**overrides):
    return {
        "as_of": AS_OF, "artifact_id": "ART-EVALUATION-DRIFT-UNIT",
        "evaluation_id": "EVALUATION-DRIFT-UNIT", "logical_revision": 0, **overrides,
    }
