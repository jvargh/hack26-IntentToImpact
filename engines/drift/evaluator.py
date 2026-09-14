"""Pure runtime decisions over normalized, caller-authenticated contract inputs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from core import LocalRunManifest
from projections import CoverageRow, CoverageSummary
from risk import (
    ArtifactLink,
    CustomerPromiseContract,
    EvidenceReference,
    PromiseEvaluation,
    RuntimeBinding,
    RuntimeSnapshot,
    SandboxOperationReceipt,
)
from scenario import ClaimsScenarioV2
from state.case_store import canonical_bytes, seal
from tools.contracts.integrity import (
    ReferenceIntegrityError,
    scenario_identity,
    semantic_checksum,
    validate_reference_integrity,
)
from tools.contracts.validate import fragment_validator, validate_contract

Phase = Literal["design", "delivery", "runtime"]


@dataclass(frozen=True)
class EvaluationInput:
    """Generated v1.0.0 types; no alternate persisted models.

    trusted_sources pins exact D15/E01 records authenticated by the caller, not by
    JSON validation. Empty pins are deliberately safe. D10/D12 opaque references
    and D13 receipts are needed only to resolve the selected D14 baseline.
    """

    run: LocalRunManifest
    scenario: ClaimsScenarioV2
    promise_contract: CustomerPromiseContract
    binding: RuntimeBinding | None = None
    snapshot: RuntimeSnapshot | None = None
    evidence: tuple[EvidenceReference, ...] = ()
    operations: tuple[SandboxOperationReceipt, ...] = ()
    external_references: tuple[ArtifactLink, ...] = ()
    trusted_sources: tuple[ArtifactLink, ...] = ()


def _link(contract_id: str, document: dict, scenario: dict) -> dict:
    return {
        "contractId": contract_id,
        "artifact": {
            "artifactId": document["artifactId"],
            "checksum": document["stateChecksum"],
        },
        "scenario": scenario_identity(scenario),
    }


def _time(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("An explicit timezone is required")
    return result


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReferenceIntegrityError(message)


def _documents(inputs: EvaluationInput) -> list[dict]:
    return [
        inputs.promise_contract,
        *([inputs.binding] if inputs.binding is not None else []),
        *([inputs.snapshot] if inputs.snapshot is not None else []),
        *inputs.evidence,
        *inputs.operations,
    ]


def _validate(inputs: EvaluationInput) -> list[dict]:
    records = _documents(inputs)
    validate_reference_integrity(
        records, {inputs.run["runId"]: inputs.run},
        inputs.scenario, inputs.external_references,
    )
    if inputs.binding:
        _require(
            inputs.binding["componentId"] == inputs.scenario["componentId"],
            "Selected binding component differs from CP-01",
        )
        _require(
            inputs.binding["resourceId"] in inputs.run["scope"]["resourceIds"],
            "Selected resource is not in the trusted run scope",
        )
    if inputs.snapshot:
        expected = _link("D14", inputs.binding, inputs.scenario) if inputs.binding else None
        _require(inputs.snapshot["binding"] == expected, "Selected snapshot/binding mismatch")
    possible = [
        *([_link("D15", inputs.snapshot, inputs.scenario)] if inputs.snapshot else []),
        *[_link("E01", item, inputs.scenario) for item in inputs.evidence],
    ]
    for reference in inputs.trusted_sources:
        fragment_validator("risk", "ArtifactLink").validate(reference)
        _require(reference in possible, "Trusted source reference is missing or mismatched")
    return records


def _confirmed(contract: CustomerPromiseContract, promise_id: str) -> bool:
    return (
        contract["status"] in {"confirmed", "partially-confirmed"}
        and contract["confirmationDecisionId"] is not None
        and promise_id in contract["confirmedPromiseIds"]
    )


def _source_state(
    inputs: EvaluationInput, evidence: EvidenceReference, now: datetime
) -> str:
    if _link("E01", evidence, inputs.scenario) not in inputs.trusted_sources:
        return "untrusted-evidence"
    allowed_origins = {
        "live": {"live-external"},
        "fixture": {"fixture", "ux-mock"},
        "replay": {"replayed"},
    }
    if evidence["origin"] not in allowed_origins[inputs.run["runMode"]]:
        return "mode-ineligible"
    if evidence["eligibility"] != "eligible":
        return "evidence-ineligible"
    if evidence["completeness"] != "complete" or evidence["evidenceState"] not in {"fresh", "stale"}:
        return "evidence-incomplete"
    observed, retrieved = _time(evidence["observedAt"]), _time(evidence["retrievedAt"])
    snapshot = inputs.snapshot
    start, end = (_time(snapshot["evidenceWindow"][key]) for key in ("from", "to"))
    if not start <= observed <= end or not observed <= retrieved <= _time(snapshot["collectedAt"]) <= now:
        return "evidence-time-ineligible"
    if inputs.binding["boundAt"] is None or observed < _time(inputs.binding["boundAt"]):
        return "evidence-predates-binding"
    expires = _time(evidence["validUntil"]) if evidence["validUntil"] else None
    if expires is not None and expires < observed:
        return "evidence-time-ineligible"
    if (
        evidence["evidenceState"] == "stale"
        or (expires is not None and now >= expires)
        or (now - observed).total_seconds() > inputs.scenario["cp01Verifier"]["maxEvidenceAgeSeconds"]
    ):
        return "stale-evidence"
    return "eligible"


def _predicates(inputs: EvaluationInput, now: datetime, gate: str | None) -> tuple[list, bool]:
    results = []
    stale_proof = []
    evidence_index = {item["artifactId"]: item for item in inputs.evidence}
    for predicate in inputs.scenario["cp01Verifier"]["predicates"]:
        result = {
            "predicateId": predicate["predicateId"], "result": "unknown",
            "reasonCode": gate or "missing-property", "evidence": [],
        }
        fresh_values, old_values, reasons = [], [], []
        if gate is None:
            for observation in inputs.snapshot["observations"]:
                if predicate["property"] not in observation["properties"]:
                    reasons.append("missing-property")
                    continue
                value = observation["properties"][predicate["property"]]
                if value is None:
                    reasons.append("null-property")
                    continue
                for link in observation["evidence"]:
                    evidence = evidence_index[link["reference"]["artifact"]["artifactId"]]
                    if predicate["predicateId"] not in evidence["supportedAssertionIds"]:
                        reasons.append("unsupported-assertion")
                        continue
                    state = _source_state(inputs, evidence, now)
                    # JSON booleans must never compare equal to Python integers.
                    matches = type(value) is type(predicate["expected"]) and value == predicate["expected"]
                    if state == "eligible":
                        fresh_values.append((matches, link))
                    elif state == "stale-evidence":
                        old_values.append((matches, link))
                    reasons.append(state)
            if fresh_values:
                matches = {item[0] for item in fresh_values}
                if len(matches) > 1:
                    result["reasonCode"] = "conflicting-observations"
                else:
                    passed = next(iter(matches))
                    result.update(
                        result="pass" if passed else "fail",
                        reasonCode="property-matches" if passed else "property-mismatch",
                        evidence=_unique_links([item[1] for item in fresh_values]),
                    )
            elif reasons:
                result["reasonCode"] = sorted(set(reasons))[0]
                if old_values:
                    result["evidence"] = _unique_links([item[1] for item in old_values])
        stale_proof.append(
            result["result"] == "pass"
            or (not fresh_values and bool(old_values) and all(item[0] for item in old_values))
        )
        results.append(result)
    return results, all(stale_proof) and bool(stale_proof)


def _unique_links(links: list[dict]) -> list[dict]:
    return [value for _, value in sorted({canonical_bytes(value): value for value in links}.items())]


def evaluate_cp01(
    inputs: EvaluationInput, *, as_of: str, artifact_id: str,
    evaluation_id: str, logical_revision: int, phase: Phase = "runtime",
) -> PromiseEvaluation:
    """Produce D17 without clocks, generated IDs, network, authorization or writes."""
    if phase not in {"design", "delivery", "runtime"}:
        raise ValueError("Unsupported evaluation phase")
    if type(logical_revision) is not int or logical_revision < 0:
        raise ValueError("logical_revision must be a nonnegative integer")
    now = _time(as_of)
    records = _validate(inputs)
    verifier = inputs.scenario["cp01Verifier"]
    _require(
        all(
            predicate["operator"] == "equals"
            and type(predicate["expected"]) is type(inputs.scenario["desiredStorageConfiguration"][predicate["property"]])
            and predicate["expected"] == inputs.scenario["desiredStorageConfiguration"][predicate["property"]]
            for predicate in verifier["predicates"]
        ),
        "Verifier predicates contradict desired storage configuration",
    )
    gate = None
    if phase != "runtime":
        gate = "unsupported-phase"
    elif not _confirmed(inputs.promise_contract, "CP-01"):
        gate = "promise-unconfirmed"
    elif inputs.binding is None or inputs.binding["bindingState"] != "bound":
        gate = "binding-unavailable"
    elif inputs.binding["gaps"]:
        gate = "binding-incomplete"
    elif inputs.snapshot is None or inputs.snapshot["completeness"] in {"missing", "failed"}:
        gate = "snapshot-unavailable"
    elif _link("D15", inputs.snapshot, inputs.scenario) not in inputs.trusted_sources:
        gate = "untrusted-snapshot"
    elif _time(inputs.snapshot["collectedAt"]) > now or _time(inputs.snapshot["evidenceWindow"]["to"]) > now:
        gate = "snapshot-time-ineligible"
    results, expired_proof = _predicates(inputs, now, gate)
    status, reason = "unknown", gate or "evidence-incomplete"
    if gate is None:
        if any(item["result"] == "fail" for item in results):
            status, reason = "breached", "current-property-mismatch"
        elif (
            inputs.snapshot["completeness"] == "complete"
            and not inputs.snapshot["missingEvidenceKinds"]
            and not inputs.snapshot["collectionErrors"]
        ):
            if all(item["result"] == "pass" for item in results):
                status, reason = "verified", "all-predicates-pass"
            elif expired_proof:
                status, reason = "stale", "prior-proof-expired"
    snapshot = inputs.snapshot
    binding = inputs.binding
    output = seal({
        "schemaVersion": "1.0.0", "artifactType": "promise-evaluation",
        "artifactId": artifact_id, "evaluationId": evaluation_id,
        "runId": inputs.run["runId"], "caseId": inputs.run["caseId"],
        "scope": deepcopy(inputs.run["scope"]), "caseRevisionAtWrite": logical_revision,
        "createdAt": as_of, "updatedAt": as_of,
        "derivedFrom": {
            **{record["artifactId"]: record["stateChecksum"] for record in records},
            "scenario": inputs.scenario["stateChecksum"],
            "run": inputs.run["stateChecksum"],
        },
        "scenario": scenario_identity(inputs.scenario),
        "runMode": inputs.run["runMode"], "purpose": inputs.run["purpose"],
        "promiseId": "CP-01", "phase": phase, "status": status, "reasonCode": reason,
        "evaluatedAt": as_of,
        "evidenceWindow": deepcopy(snapshot["evidenceWindow"]) if snapshot else {"from": as_of, "to": as_of},
        "promiseContract": _link("D03", inputs.promise_contract, inputs.scenario),
        "binding": _link("D14", binding, inputs.scenario) if binding else None,
        "runtimeSnapshot": _link("D15", snapshot, inputs.scenario) if snapshot else None,
        "verifier": {
            "verifierId": verifier["verifierId"], "version": verifier["version"],
            "checksum": semantic_checksum(verifier),
        },
        "predicateResults": results,
        "evidence": _unique_links([link for result in results for link in result["evidence"]]),
        "findingId": None, "notApplicableDecision": None,
    })
    _require(output["stateChecksum"] == semantic_checksum(output), "State/risk canonicalization disagreement")
    validate_contract(output, "D17")
    validate_reference_integrity(
        [*records, output], {inputs.run["runId"]: inputs.run},
        inputs.scenario, inputs.external_references,
    )
    return output


def reduce_coverage(rows: list[CoverageRow]) -> CoverageSummary:
    """Reduce already trusted runtime rows; never authorize an applicability exception.

    Callers own source evaluation integrity and approved not-applicable decisions.
    For untrusted records use project_coverage, which generates every row itself.
    """
    _require(len({row["promiseId"] for row in rows}) == len(rows), "Duplicate coverage promise")
    for row in rows:
        fragment_validator("projections", "CoverageRow").validate(row)
        _require(
            row["status"] == "unknown" or row["evaluation"] is not None,
            "Coverage verdict requires its source evaluation",
        )
        _require(row["status"] != "verified" or row["confirmed"], "Unconfirmed promise cannot be verified")
    applicable = [row for row in rows if row["status"] != "not-applicable"]
    result = {
        "phase": "runtime",
        "assessmentState": (
            "not-assessed" if not applicable
            else "partial" if any(row["status"] in {"unknown", "stale"} for row in applicable)
            else "assessed"
        ),
        "verifiedCount": sum(row["status"] == "verified" for row in applicable),
        "applicableCount": len(applicable),
        "rows": deepcopy(rows),
    }
    fragment_validator("projections", "CoverageSummary").validate(result)
    return result


def project_coverage(inputs: EvaluationInput, evaluation: PromiseEvaluation | None) -> CoverageSummary:
    """Build the P01 coverage fragment; unsupported promises stay unknown.

    A supplied CP-01 evaluation is recomputed to prevent shape-only success. The
    caller chooses the explicit cutoff by creating that evaluation; this does not
    claim freshness at some later implicit wall clock.
    """
    _validate(inputs)
    if evaluation is not None:
        validate_contract(evaluation, "D17")
        expected = evaluate_cp01(
            inputs, as_of=evaluation["evaluatedAt"], artifact_id=evaluation["artifactId"],
            evaluation_id=evaluation["evaluationId"], logical_revision=evaluation["caseRevisionAtWrite"],
            phase=evaluation["phase"],
        )
        _require(evaluation == expected, "Coverage evaluation is not the deterministic result of these inputs")
    rows = []
    for promise in inputs.promise_contract["promises"]:
        selected = evaluation if promise["promiseId"] == "CP-01" and evaluation and evaluation["phase"] == "runtime" else None
        confirmed = _confirmed(inputs.promise_contract, promise["promiseId"])
        rows.append({
            "promiseId": promise["promiseId"], "confirmed": confirmed,
            "status": selected["status"] if selected else "unknown",
            "reasonCode": selected["reasonCode"] if selected else (
                "promise-unconfirmed" if not confirmed else "verifier-unavailable"
            ),
            "evaluation": _link("D17", selected, inputs.scenario) if selected else None,
        })
    return reduce_coverage(rows)
