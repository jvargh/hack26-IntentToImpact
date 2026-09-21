"""Design contract reference/comparison checks, not an approval or evaluation engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from .integrity import (
    ReferenceIntegrityError, assert_scenario_identity_unchanged, scenario_identity,
    semantic_checksum, validate_reference_integrity, validate_scenario,
)
from .validate import fragment_validator, identify_contract, validate_contract


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReferenceIntegrityError(message)


def artifact_reference(value: dict[str, Any]) -> dict[str, str]:
    return {"artifactId": value["artifactId"], "checksum": value["stateChecksum"]}


def catalog_checksum(scenario: dict[str, Any]) -> str:
    return semantic_checksum({"catalog": scenario["catalog"], "candidates": scenario["candidates"]})


def _bare(reference: dict[str, Any]) -> dict[str, str]:
    return reference["artifact"] if "contractId" in reference else reference


def assert_current_inputs(document: dict[str, Any], expected_inputs: dict[str, dict[str, Any]], *, schema_version="1.0.0") -> None:
    """Compare against caller-supplied current references, never derive 'current' from the proposal."""
    validate_contract(document, identify_contract(document, schema_version=schema_version), schema_version=schema_version)
    for name, reference in expected_inputs.items():
        fragment_validator("core", "ArtifactReference").validate(_bare(reference))
        _require(document.get(name) == reference, f"stale-input: {name}")
        _require(document["derivedFrom"].get(name) == _bare(reference)["checksum"], f"Input checksum mismatch: {name}")


def _check_human_event(record, event, reference, *, action_id, decision_id, kinds):
    validate_contract(event, "E05")
    _require(event["stateChecksum"] == semantic_checksum(event), "Human event body checksum mismatch")
    _require(reference["artifact"] == artifact_reference(event), "Human event reference mismatch")
    _require(reference["scenario"] == event["scenario"], "Human event reference scenario mismatch")
    _require(event["actor"] == record["actor"], "Human event actor mismatch")
    _require(event["actionId"] == action_id and event["decisionId"] == decision_id, "Human event action/decision binding mismatch")
    _require(event["attentionKind"] in kinds, "Human event does not record the required explicit response")


def assert_current_approval_binding(
    approval: dict[str, Any],
    expected_binding: dict[str, Any],
    as_of: str,
    *,
    attention_event: dict[str, Any],
    schema_version="1.0.0",
) -> None:
    """Reject unusable D07 evidence against trusted current facts; never grant a capability."""
    validate_contract(approval, "D07", schema_version=schema_version)
    fragment_validator("design", "ApprovalSubjectBinding").validate(expected_binding)
    fragment_validator("core", "Timestamp").validate(as_of)
    _require(approval["stateChecksum"] == semantic_checksum(approval), "Approval body checksum mismatch")
    _require(approval["status"] == "approved", "Approval is not currently approved")
    _require(approval["binding"] == expected_binding, "Approval current binding mismatch")
    when = datetime.fromisoformat(as_of)
    issued = datetime.fromisoformat(approval["issuedAt"])
    decided = datetime.fromisoformat(approval["decidedAt"])
    expires = datetime.fromisoformat(approval["expiresAt"])
    _require(issued <= decided <= when < expires, "Approval is expired, not yet decided, or has invalid chronology")
    _check_human_event(
        approval, attention_event, approval["attentionEvent"],
        action_id=expected_binding["actionId"], decision_id=approval["decisionId"], kinds={"approved"},
    )
    for field in ("runId", "caseId", "scope", "scenario", "runMode", "purpose"):
        _require(attention_event[field] == approval[field], f"Approval/event {field} mismatch")
    _require(datetime.fromisoformat(attention_event["occurredAt"]) == decided, "Approval/event decision time mismatch")


def validate_design_references(
    documents: Iterable[dict[str, Any]],
    runs: dict[str, dict[str, Any]],
    scenario: dict[str, Any],
    *,
    current_bindings: dict[str, dict[str, Any]] | None = None,
    as_of: str | None = None,
) -> None:
    """Validate a closed fixture/engine input set and its explicitly declared relationships."""
    validate_scenario(scenario)
    expected_scenario = scenario_identity(scenario)
    values = list(documents)
    index = {}
    for value in values:
        contract_id = identify_contract(value)
        validate_contract(value, contract_id)
        key = contract_id, value["artifactId"]
        _require(key not in index, f"Duplicate design artifact: {key}")
        index[key] = value
        _require(value["stateChecksum"] == semantic_checksum(value), f"Artifact checksum mismatch: {key}")
        _require(value["runId"] in runs, "Missing trusted run")
        run = runs[value["runId"]]
        validate_contract(run, "D22")
        _require(run["stateChecksum"] == semantic_checksum(run), "Run checksum mismatch")
        _require(run["runId"] == value["runId"], "Run index mismatch")
        for field in ("caseId", "scope"):
            _require(value[field] == run[field], f"Artifact/run {field} mismatch")
        assert_scenario_identity_unchanged(
            {key: run[key] for key in ("scenarioId", "scenarioVersion", "scenarioHash")}, expected_scenario,
        )
        if "scenario" in value:
            assert_scenario_identity_unchanged(value["scenario"], expected_scenario)
            for field in ("runMode", "purpose"):
                _require(value[field] == run[field], f"Artifact/run {field} mismatch")

    legacy = [value for (kind, _), value in index.items() if kind in {"D03", "E04", "E05"}]
    validate_reference_integrity(legacy, runs, scenario)

    def resolve(reference, contract_id, owner):
        bare = _bare(reference)
        fragment_validator("core", "ArtifactReference").validate(bare)
        if "contractId" in reference:
            _require(reference["contractId"] == contract_id, "Reference contract mismatch")
            assert_scenario_identity_unchanged(reference["scenario"], expected_scenario)
        key = contract_id, bare["artifactId"]
        _require(key in index, f"Unresolved design reference: {key}")
        target = index[key]
        _require(target["stateChecksum"] == bare["checksum"], f"Reference checksum mismatch: {key}")
        for field in ("runId", "caseId", "scope"):
            _require(target[field] == owner[field], f"Cross-context design reference: {field}")
        return target

    def inputs(owner, roles):
        result = {}
        for field, kind in roles.items():
            reference = owner[field]
            if reference is not None:
                result[field] = resolve(reference, kind, owner)
                _require(owner["derivedFrom"].get(field) == _bare(reference)["checksum"], f"Input checksum mismatch: {field}")
        _require(owner["derivedFrom"].get("scenario") == scenario["stateChecksum"], "Scenario input checksum mismatch")
        return result

    def options(owner):
        rows = owner["options"]
        _require(len({item["optionId"] for item in rows}) == len(rows), "Duplicate option ID")
        canonical = {item["candidateId"]: item for item in scenario["candidates"]}
        _require({item["catalogFacts"]["candidateId"] for item in rows} == set(canonical), "Options must represent both catalog candidates")
        for option in rows:
            _require(option["catalogFacts"] == canonical[option["catalogFacts"]["candidateId"]], "Option catalog facts mismatch")
            component_ids = {item["componentId"] for item in option["components"]}
            _require(len(component_ids) == len(option["components"]), "Duplicate option component")
            for component in option["components"]:
                _require(component["componentId"] == scenario["componentId"], "Unknown V2 component")
                _require(component["storageConfiguration"] == scenario["desiredStorageConfiguration"], "Option storage configuration mismatch")
                _require(set(component["promiseIds"]) <= {p["promiseId"] for p in scenario["promises"]}, "Unknown component promise")
            for relationship in option["relationships"]:
                _require(relationship["fromComponentId"] in component_ids and relationship["toComponentId"] in component_ids, "Relationship endpoint missing")
        return {item["optionId"]: item for item in rows}

    for (kind, _), value in index.items():
        if kind == "D02":
            _require(value["derivedFrom"].get("scenario") == scenario["stateChecksum"], "Requirements scenario checksum mismatch")
            expected_ids = {rid for promise in scenario["promises"] for rid in promise["requirementIds"]}
            _require(set(value["requirementIds"]) == expected_ids, "Requirements linkage mismatch")
            _require(set(value["promiseIds"]) == {p["promiseId"] for p in scenario["promises"]}, "Requirement promise linkage mismatch")
            question = value["rpoQuestion"]
            if question["status"] == "answered":
                confirmation = question["confirmation"]
                event = resolve(confirmation["attentionEvent"], "E05", value)
                _check_human_event(
                    confirmation, event, confirmation["attentionEvent"],
                    action_id=confirmation["actionId"], decision_id=confirmation["decisionId"], kinds={"answered", "confirmed"},
                )
                _require(event["questionId"] == question["questionId"], "RPO confirmation question mismatch")
                _require(datetime.fromisoformat(event["occurredAt"]) == datetime.fromisoformat(confirmation["confirmedAt"]), "RPO confirmation time mismatch")
        elif kind == "D03":
            matching = [
                item for (contract_id, _), item in index.items()
                if contract_id == "D02" and item["stateChecksum"] == value["requirementChecksum"]
            ]
            _require(len(matching) == 1, "Promise requirement checksum has no unique loaded D02")
            if "CP-05" in value["confirmedPromiseIds"]:
                _require(matching[0]["rpoQuestion"]["status"] == "answered", "Unknown RPO cannot be confirmed in D03")
            if value["status"] == "confirmed":
                _require(
                    set(value["confirmedPromiseIds"]) == {item["promiseId"] for item in value["promises"]}
                    and matching[0]["status"] == "confirmed",
                    "Confirmed promise contract disagrees with requirements confirmation",
                )
        elif kind == "D04":
            bound = inputs(value, {"requirements": "D02", "promiseContract": "D03"})
            requirements = bound["requirements"]
            promises = bound["promiseContract"]
            _require(promises["requirementChecksum"] == requirements["stateChecksum"], "Promise/requirements checksum mismatch")
            if "CP-05" in promises["confirmedPromiseIds"]:
                _require(requirements["rpoQuestion"]["status"] == "answered", "Unknown RPO cannot be confirmed in D03")
            catalog = value["catalog"]
            _require(catalog["version"] == scenario["catalog"]["catalogVersion"] and catalog["checksum"] == catalog_checksum(scenario), "Catalog version/checksum mismatch")
            available = options(value)
            _require(value["recommendedOptionId"] is None or value["recommendedOptionId"] in available, "Proposal recommendation has no option")
        elif kind == "D08":
            bound = inputs(value, {"subject": value["subjectContractId"], "requirements": "D02", "promiseContract": "D03"})
            _require(value["gate"]["boundChecksums"] == value["derivedFrom"], "Gate input checksums mismatch")
            subject = bound["subject"]
            available = {item["optionId"] for item in subject.get("options", [])}
            assessments = value["review"]["optionAssessments"]
            _require(len({item["optionId"] for item in assessments}) == len(assessments), "Duplicate option assessment")
            for assessment in assessments:
                _require(assessment["optionId"] in available, "Assessment option is not in the reviewed subject")
                if assessment["eligibility"] == "eligible":
                    _require(not any(item["mandatory"] and item["status"] != "pass" for item in assessment["ruleResults"]), "Eligible label contradicts reported mandatory checks")
            for finding in value["review"]["findings"]:
                _require(finding["optionId"] is None or finding["optionId"] in available, "Finding option is not in the reviewed subject")
            if value["gate"]["approval"] is not None:
                approval = resolve(value["gate"]["approval"], "D07", value)
                expected_status = "stale" if approval["status"] == "expired" else approval["status"]
                _require(value["gate"]["approvalStatus"] == expected_status, "Gate approval snapshot disagrees with its source")
        elif kind == "D05":
            bound = inputs(value, {"sourceProposal": "D04", "review": "D08", "promiseContract": "D03"})
            available = options(value)
            original = {item["optionId"]: item for item in bound["sourceProposal"]["options"]}
            _require(set(available) == set(original), "Model/proposal option mismatch")
            for option_id, option in available.items():
                _require(option["catalogFacts"] == original[option_id]["catalogFacts"], "Model rewrites proposal catalog facts")
            _require(bound["review"]["subject"] == artifact_reference(bound["sourceProposal"]), "Model review binds a different proposal")
            if value["recommendedOptionId"] is not None:
                assessments = {item["optionId"]: item for item in bound["review"]["review"]["optionAssessments"]}
                _require(value["recommendedOptionId"] in assessments and assessments[value["recommendedOptionId"]]["eligibility"] == "eligible", "Model recommendation has no eligible assessment source")
            if value["decision"] is not None:
                decision = resolve(value["decision"], "D06", value)
                _require(decision["decisionReceipt"] is not None and decision["decisionReceipt"]["selectedOptionId"] == value["selectedOptionId"], "Model selection has no matching decision")
        elif kind == "D06":
            bound = inputs(value, {"architecture": "D05", "review": "D08", "requirements": "D02", "promiseContract": "D03"})
            available = {item["optionId"] for item in bound["architecture"]["options"]}
            _require(set(value["consideredOptionIds"]) <= available, "ADR references unknown option")
            decision = value["decisionReceipt"]
            if decision is not None:
                _require(decision["boundChecksums"] == value["derivedFrom"], "Decision input checksums mismatch")
                event = resolve(decision["attentionEvent"], "E05", value)
                _check_human_event(
                    decision, event, decision["attentionEvent"], action_id=decision["actionId"],
                    decision_id=decision["decisionId"], kinds={"confirmed"} if decision["outcome"] == "selected" else {"rejected"},
                )
                if decision["outcome"] == "selected":
                    _require(decision["selectedOptionId"] in available, "Decision selects an unknown option")
                    assessments = {item["optionId"]: item for item in bound["review"]["review"]["optionAssessments"]}
                    _require(decision["selectedOptionId"] in assessments and assessments[decision["selectedOptionId"]]["eligibility"] == "eligible", "Selection contradicts referenced eligibility")
        elif kind == "D07":
            bound = inputs(value, {"gateEvaluation": "D08"})
            subject = resolve(value["binding"]["subject"], value["binding"]["subjectContractId"], value)
            if value["binding"]["subjectContractId"] == "D06":
                for field, checksum in {**subject["derivedFrom"], "decision": subject["stateChecksum"]}.items():
                    _require(value["binding"]["boundChecksums"].get(field) == checksum, f"Approval subject input checksum mismatch: {field}")
            _require(value["binding"]["gateId"] == bound["gateEvaluation"]["gate"]["gateId"], "Approval gate ID mismatch")
            _require(datetime.fromisoformat(value["issuedAt"]) < datetime.fromisoformat(value["expiresAt"]), "Approval expiry precedes issue")
            if value["attentionEvent"] is not None:
                event = resolve(value["attentionEvent"], "E05", value)
                if value["status"] in {"approved", "rejected"}:
                    _check_human_event(
                        value, event, value["attentionEvent"], action_id=value["binding"]["actionId"],
                        decision_id=value["decisionId"], kinds={value["status"]},
                    )
        elif kind == "D09":
            bound = inputs(value, {"requirements": "D02", "promiseContract": "D03", "architecture": "D05", "decision": "D06", "gateEvaluation": "D08", "approval": "D07"})
            decision = bound["decision"]["decisionReceipt"]
            _require(decision is not None and decision["selectedOptionId"] == value["selectedOptionId"], "Generation selection/decision mismatch")
            for field in ("architecture", "requirements", "promiseContract"):
                _require(value[field] == bound["decision"][field], f"Generation/decision {field} binding mismatch")
            _require(value["desiredStateChecksum"] == scenario["desiredStateChecksum"], "Generation desired-state checksum mismatch")
            paths = [output["relativePath"] for output in value["outputs"]]
            _require(len({path.casefold() for path in paths}) == len(paths), "Duplicate generation output path")
            available = {item["componentId"] for option in bound["architecture"]["options"] if option["optionId"] == value["selectedOptionId"] for item in option["components"]}
            modules = {item["moduleId"]: item for item in value["modules"]}
            _require(len(modules) == len(value["modules"]), "Duplicate generation module")
            for output in value["outputs"]:
                _require(set(output["componentIds"]) <= available, "Output component is not in selected option")
                _require(modules.get(output["template"]["moduleId"]) == output["template"], "Output template/version is not in the pinned plan")
            if value["status"] == "ready":
                _require(bound["gateEvaluation"]["gate"]["gateId"] == "generation-ready", "Ready plan references the wrong gate")
                _require(bound["gateEvaluation"]["gate"]["effectiveStatus"] in {"pass", "pass-with-warnings"}, "Ready plan references unacceptable checks")
                approval = bound["approval"]
                _require(approval["approvalClass"] == "design" and approval["binding"]["subjectContractId"] == "D06" and approval["binding"]["subject"] == value["decision"], "Generation approval binds a different design decision")
                _require(current_bindings is not None and approval["artifactId"] in current_bindings and as_of is not None, "Current approval comparison facts are required")
                attention = resolve(approval["attentionEvent"], "E05", approval) if approval["attentionEvent"] else {}
                assert_current_approval_binding(
                    approval, current_bindings[approval["artifactId"]], as_of, attention_event=attention,
                )
