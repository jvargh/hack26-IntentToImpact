"""CaseStore is the sole writer; this module never executes work or providers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from policy import Policy
from state.case_store import CaseStore, StoreError, canonical_bytes, seal
from tools.contracts.validate import SCHEMA, validate_contract

VERSION = "1.0.0"
REGISTRY_PATH = Path(__file__).parents[1] / "policy" / "capabilities.v1.json"
SUPPORTED_PROFILES = {"read", "propose", "provider"}
TERMINAL = {"succeeded", "failed", "stale", "blocked", "recovery-required", "cancelled"}
RESERVED = {"actor", "actorId", "caller", "callerClass", "humanInitiator", "activityClass",
            "transport", "runMode", "purpose", "scope", "rootId", "configId", "permittedCapabilities"}


class WorkError(StoreError):
    def __init__(self, code, reason):
        self.reason = reason
        super().__init__(code, reason)


@dataclass(frozen=True)
class TransitionReceipt:
    work_id: str
    receipt_ref: dict
    status: str
    reused: bool
    claim_id: str | None = None


def _validate(value, definition):
    Draft202012Validator(
        {"$ref": f"#/definitions/{definition}", "definitions": SCHEMA["definitions"]},
        format_checker=FormatChecker(),
    ).validate(value)


def _now():
    return datetime.now(timezone.utc).isoformat()


class WorkCoordinator:
    def __init__(self, store: CaseStore, policy: Policy, run_id: str):
        self.store, self.policy, self.run_id = store, policy, run_id
        self.manifest = store.read_run(run_id)
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if registry.get("version") != VERSION:
            raise WorkError("invalid-artifact", "unsupported-capability-registry")
        self.registry = registry["capabilities"]

    def _snapshot(self):
        self.store.check_run_context(self.run_id, self.manifest)
        case = self.store.read_case(self.run_id)
        if ([e["sequence"] for e in case["events"]] != list(range(1, len(case["events"]) + 1))
                or len({e["eventId"] for e in case["events"]}) != len(case["events"])
                or len({w["workId"] for w in case["work"]}) != len(case["work"])
                or len({r["idempotencyKey"] for r in case["idempotencyRecords"]}) != len(case["idempotencyRecords"])):
            raise WorkError("invalid-artifact", "duplicate-or-unordered-records")
        return case

    def _read_auth(self, entry):
        result = self.policy.authorize(entry, {"capability": "read-case"},
                                       current_run=self.store.read_run(self.run_id))
        if not result.allowed:
            raise WorkError(result.error["code"], result.reason)
        validate_contract(result.authorization_context, "E08")
        return result.authorization_context

    def _authorize(self, entry, request, facts, revision):
        result = self.policy.authorize(entry, request, current_run=self.store.read_run(self.run_id), facts=facts)
        if not result.allowed:
            raise WorkError(result.error["code"], result.reason)
        if result.authorization_context["caseRevisionAtWrite"] != revision:
            raise WorkError("stale-revision", "engine-facts-revision-mismatch")
        expected_class = self.registry[request["capability"]]["activityClass"]
        if result.activity_class != expected_class:
            raise WorkError("not-authorized", "registry-activity-mismatch")
        return result.authorization_context

    @staticmethod
    def _revision(case, expected):
        if type(expected) is not int or expected < 0 or case["logicalRevision"] != expected:
            raise WorkError("stale-revision", "reload-work-status-and-input-hashes")

    def _capability(self, auth, capability):
        row = self.registry.get(capability)
        if not row or capability not in auth["permittedCapabilities"]:
            raise WorkError("not-authorized", "work-capability-not-granted")
        if row["profile"] not in SUPPORTED_PROFILES:
            raise WorkError("not-authorized", "human-and-operator-actions-are-not-background-work")
        return row

    @staticmethod
    def _executor(auth):
        caller = auth["caller"]
        if caller["callerClass"] != "system" or caller["channel"] != "worker":
            raise WorkError("not-authorized", "trusted-system-worker-required")

    def _envelope(self, artifact_type, revision, *, artifact_id=None, created_at=None, derived=None):
        at = _now()
        return {
            "schemaVersion": VERSION, "artifactType": artifact_type,
            "artifactId": artifact_id or f"ART-{uuid4().hex}",
            "runId": self.run_id, "caseId": self.manifest["caseId"],
            "scope": deepcopy(self.manifest["scope"]), "caseRevisionAtWrite": revision,
            "createdAt": created_at or at, "updatedAt": at,
            "derivedFrom": derived or {"runManifest": self.manifest["stateChecksum"]},
        }

    def _put(self, artifact_type, revision, data):
        return self.store.put_artifact(self.run_id, {**self._envelope(artifact_type, revision), **data})

    def _dependency_refs(self, case, refs):
        if type(refs) is not dict:
            raise WorkError("invalid-artifact", "dependencies-must-be-section-references")
        for section, reference in refs.items():
            _validate(section, "ActionId")
            _validate(reference, "ArtifactReference")
            if case["sections"].get(section) != reference:
                raise WorkError("stale-input", "dependency-section-changed")
            self.store.read_artifact(self.run_id, reference)

    @staticmethod
    def _key(key):
        if type(key) is not str or not 1 <= len(key) <= 128:
            raise WorkError("invalid-artifact", "invalid-idempotency-key")

    def _existing(self, case, key, command, checksum):
        self._key(key)
        record = next((r for r in case["idempotencyRecords"] if r["idempotencyKey"] == key), None)
        if record is None:
            return None
        if record["commandId"] != command or record["inputChecksum"] != checksum:
            raise WorkError("idempotency-conflict", "same-key-different-input")
        saved = self.store.read_artifact(self.run_id, record["result"])
        validate_contract(saved, "E03")
        return TransitionReceipt(saved["workId"], deepcopy(record["result"]), saved["status"], True)

    def _capacity(self, case, *, work=0, events=1, records=1):
        limits = SCHEMA["definitions"]["CaseState"]["properties"]
        for field, increment in (("work", work), ("events", events), ("idempotencyRecords", records)):
            if len(case[field]) + increment > limits[field]["maxItems"]:
                raise WorkError("invalid-artifact", f"{field}-capacity-exceeded")

    @staticmethod
    def _work(case, work_id):
        _validate(work_id, "WorkId")
        work = next((w for w in case["work"] if w["workId"] == work_id), None)
        if work is None:
            raise WorkError("invalid-artifact", "work-not-found")
        return work

    def _metadata(self, work):
        if (not work["checkpoints"] or not work["checkpoints"][0]["artifacts"]
                or work["commandId"] not in self.registry):
            raise WorkError("invalid-artifact", "missing-work-metadata")
        checkpoint = work["checkpoints"][0]
        metadata = self.store.read_artifact(self.run_id, checkpoint["artifacts"][0])
        if (metadata.get("artifactType") != "local-work-metadata"
                or metadata.get("workId") != work["workId"] or metadata.get("commandId") != work["commandId"]
                or metadata.get("activityClass") != self.registry[work["commandId"]]["activityClass"]):
            raise WorkError("invalid-artifact", "invalid-work-metadata")
        auth = self.store.read_artifact(self.run_id, metadata["authorizationRef"])
        validate_contract(auth, "E08")
        return metadata, auth

    def _claim(self, work):
        for checkpoint in reversed(work["checkpoints"]):
            for reference in checkpoint["artifacts"]:
                item = self.store.read_artifact(self.run_id, reference)
                if item.get("artifactType") == "local-work-claim":
                    return item
        raise WorkError("recovery-required", "missing-durable-claim")

    def _event(self, case, work, operation, auth, metadata, payload_refs, reason=None):
        original_auth = self.store.read_artifact(self.run_id, metadata["authorizationRef"])
        initiator = original_auth.get("humanInitiator")
        if original_auth["caller"]["callerClass"] == "human":
            initiator = {k: original_auth["caller"]["actor"][k] for k in ("actorId", "identityAssurance")}
        event_metadata = self._put("local-work-event-metadata", case["logicalRevision"] + 1, {
            "operation": operation, "status": work["status"], "activityClass": metadata["activityClass"],
            "reason": reason, "metadataVersion": VERSION,
        })
        auth_ref = self.store.put_artifact(self.run_id, auth)
        refs = [event_metadata, auth_ref, *payload_refs]
        for reference in refs:
            self.store.read_artifact(self.run_id, reference)
        event = seal({
            **self._envelope("domain-event", case["logicalRevision"] + 1),
            "eventId": f"EVENT-{uuid4().hex}", "sequence": len(case["events"]) + 1,
            "eventType": f"work-{operation}", "correlationId": work["correlationId"],
            "workId": work["workId"], "actor": deepcopy(auth["caller"]["actor"]), "payloadRefs": refs,
            **({"humanInitiator": deepcopy(initiator)} if initiator else {}),
        })
        if any(existing["eventId"] == event["eventId"] for existing in case["events"]):
            raise WorkError("invalid-artifact", "generated-event-id-collision")
        validate_contract(event, "E04")
        case["events"].append(event)

    def _commit(self, case, work, *, operation, auth, metadata, refs, key, checksum, reason=None):
        self._capacity(case)
        self._key(key)
        if any(record["idempotencyKey"] == key for record in case["idempotencyRecords"]):
            raise WorkError("idempotency-conflict", "coordination-key-already-used")
        revision = case["logicalRevision"]
        work.update(caseRevisionAtWrite=revision + 1, updatedAt=_now(), expectedRevision=revision)
        sealed_work = seal(work)
        validate_contract(sealed_work, "E03")
        for checkpoint in sealed_work["checkpoints"]:
            for reference in checkpoint["artifacts"]:
                self.store.read_artifact(self.run_id, reference)
        receipt_ref = self.store.put_artifact(self.run_id, sealed_work)
        case["work"] = [sealed_work if row["workId"] == work["workId"] else row for row in case["work"]]
        self._event(case, sealed_work, operation, auth, metadata, [receipt_ref, *refs], reason)
        case["idempotencyRecords"].append({
            "idempotencyKey": key, "commandId": work["commandId"],
            "inputChecksum": checksum, "result": receipt_ref,
        })
        self.store.commit(self.run_id, revision, case)
        return TransitionReceipt(work["workId"], receipt_ref, work["status"], False)

    def enqueue(self, entry, request, *, idempotency_key, payload, dependencies, facts=None):
        case = self._snapshot()
        read_auth = self._read_auth(entry)
        self._key(idempotency_key)
        if idempotency_key.startswith(("claim:", "finish:", "reconcile:", "presentation:")):
            raise WorkError("invalid-artifact", "reserved-idempotency-key")
        if type(request) is not dict or type(request.get("capability")) is not str:
            raise WorkError("invalid-artifact", "invalid-work-request")
        profile = self._capability(read_auth, request["capability"])
        if type(payload) is not dict or set(payload) & RESERVED:
            raise WorkError("invalid-artifact", "payload-cannot-supply-authority")
        try:
            if len(canonical_bytes(payload)) > 65536:
                raise WorkError("invalid-artifact", "work-payload-too-large")
            original = {k: v for k, v in request.items() if k != "expectedRevision"}
            checksum = seal({"request": original, "payload": payload, "dependencies": dependencies,
                             "caller": read_auth["caller"], "humanInitiator": read_auth.get("humanInitiator")})["stateChecksum"]
        except (ValueError, TypeError, RecursionError) as exc:
            raise WorkError("invalid-artifact", "payload-must-be-bounded-json") from exc
        existing = self._existing(case, idempotency_key, request["capability"], checksum)
        if existing:
            return existing
        self._revision(case, request.get("expectedRevision"))
        self._dependency_refs(case, dependencies)
        if profile["profile"] != "read" and request.get("boundChecksums") != {
            section: reference["checksum"] for section, reference in dependencies.items()
        }:
            raise WorkError("stale-input", "all-bound-inputs-must-be-pinned-section-references")
        auth = self._authorize(entry, request, facts, case["logicalRevision"])
        self._capacity(case, work=1)
        auth_ref = self.store.put_artifact(self.run_id, auth)
        work_id = f"WORK-{uuid4().hex}"
        if any(work["workId"] == work_id for work in case["work"]):
            raise WorkError("invalid-artifact", "generated-work-id-collision")
        metadata_ref = self._put("local-work-metadata", case["logicalRevision"] + 1, {
            "metadataVersion": VERSION, "workId": work_id, "commandId": request["capability"],
            "activityClass": profile["activityClass"], "profile": profile["profile"],
            "request": original, "payload": deepcopy(payload), "dependencies": deepcopy(dependencies),
            "authorizationRef": auth_ref, "inputChecksum": checksum,
        })
        metadata = self.store.read_artifact(self.run_id, metadata_ref)
        work = seal({
            **self._envelope("work-envelope", case["logicalRevision"] + 1),
            "workId": work_id, "attempt": 1, "commandId": request["capability"],
            "expectedRevision": case["logicalRevision"], "status": "queued",
            "checkpoints": [{"checkpointId": f"CHECKPOINT-{uuid4().hex}", "createdAt": _now(),
                             "artifacts": [metadata_ref]}],
            "correlationId": auth["correlationId"],
        })
        case["work"].append(work)
        return self._commit(case, work, operation="enqueued", auth=auth, metadata=metadata,
                            refs=[metadata_ref], key=idempotency_key, checksum=checksum)

    def read_work(self, entry, work_id):
        case = self._snapshot()
        auth = self._read_auth(entry)
        work = self._work(case, work_id)
        self._capability(auth, work["commandId"])
        self._metadata(work)
        return deepcopy(work)

    def _transition(self, entry, work_id, expected_revision, facts, *, allow_changed_dependencies=False):
        case = self._snapshot()
        self._revision(case, expected_revision)
        auth = self._read_auth(entry)
        self._executor(auth)
        work = self._work(case, work_id)
        metadata, _ = self._metadata(work)
        self._capability(auth, work["commandId"])
        if not allow_changed_dependencies:
            self._dependency_refs(case, metadata["dependencies"])
            request = {**metadata["request"], "expectedRevision": case["logicalRevision"]}
            auth = self._authorize(entry, request, facts, case["logicalRevision"])
        return case, work, metadata, auth

    def claim(self, entry, work_id, *, expected_revision, facts=None):
        case, work, metadata, auth = self._transition(entry, work_id, expected_revision, facts)
        if work["status"] != "queued":
            raise WorkError("recovery-required", "work-is-not-queued-do-not-reexecute")
        self._capacity(case)
        claim_id = f"CLAIM-{uuid4().hex}"
        claim_ref = self._put("local-work-claim", case["logicalRevision"] + 1, {
            "claimId": claim_id, "workId": work_id, "actor": auth["caller"]["actor"],
            "outcome": "not-yet-captured",
        })
        work["status"] = "running"
        work["checkpoints"].append({"checkpointId": f"CHECKPOINT-{uuid4().hex}", "createdAt": _now(),
                                    "artifacts": [claim_ref]})
        result = self._commit(case, work, operation="claimed", auth=auth, metadata=metadata,
                              refs=[claim_ref], key=f"claim:{work_id}",
                              checksum=seal({"claimId": claim_id})["stateChecksum"])
        return TransitionReceipt(result.work_id, result.receipt_ref, result.status, False, claim_id)

    def _finish(self, entry, work_id, claim_id, expected_revision, result_ref, facts, status):
        _validate(result_ref, "ArtifactReference")
        _validate(claim_id, "Identifier")
        case = self._snapshot()
        auth = self._read_auth(entry)
        self._executor(auth)
        work = self._work(case, work_id)
        metadata, _ = self._metadata(work)
        self._capability(auth, work["commandId"])
        claim = self._claim(work)
        if claim["claimId"] != claim_id or claim["actor"] != auth["caller"]["actor"]:
            raise WorkError("not-authorized", "claim-owner-mismatch")
        if status == "failed":
            validate_contract(self.store.read_artifact(self.run_id, result_ref), "E07")
        checksum = seal({"claimId": claim_id, "status": status, "resultRef": result_ref})["stateChecksum"]
        key = f"finish:{work_id}"
        prior = self._existing(case, key, work["commandId"], checksum)
        if prior:
            self.store.read_artifact(self.run_id, result_ref)
            return prior
        self._revision(case, expected_revision)
        if work["status"] != "running":
            raise WorkError("recovery-required", "work-not-running-outcome-requires-review")
        self._dependency_refs(case, metadata["dependencies"])
        auth = self._authorize(entry, {**metadata["request"], "expectedRevision": expected_revision},
                               facts, expected_revision)
        self.store.read_artifact(self.run_id, result_ref)
        self._capacity(case)
        work["status"] = status
        work["checkpoints"].append({"checkpointId": f"CHECKPOINT-{uuid4().hex}", "createdAt": _now(),
                                    "artifacts": [result_ref]})
        return self._commit(case, work, operation=status, auth=auth, metadata=metadata,
                            refs=[result_ref], key=key, checksum=checksum)

    def complete(self, entry, work_id, claim_id, *, expected_revision, result_ref, facts=None):
        return self._finish(entry, work_id, claim_id, expected_revision, result_ref, facts, "succeeded")

    def fail(self, entry, work_id, claim_id, *, expected_revision, error_ref, facts=None):
        return self._finish(entry, work_id, claim_id, expected_revision, error_ref, facts, "failed")

    def reconcile(self, entry, work_id, *, expected_revision):
        case, work, metadata, auth = self._transition(
            entry, work_id, expected_revision, None, allow_changed_dependencies=True,
        )
        if work["status"] in TERMINAL:
            return None
        if work["status"] == "running":
            work["status"], reason = "recovery-required", "uncertain-outcome-no-automatic-reexecution"
        elif work["status"] == "queued":
            try:
                self._dependency_refs(case, metadata["dependencies"])
            except WorkError as exc:
                if exc.code != "stale-input":
                    raise
                work["status"], reason = "stale", "dependency-section-changed"
            else:
                return None
        else:
            return None
        return self._commit(case, work, operation="reconciled", auth=auth, metadata=metadata,
                            refs=[], key=f"reconcile:{work_id}",
                            checksum=seal({"workId": work_id, "status": work["status"]})["stateChecksum"],
                            reason=reason)

    def acknowledge_presentation(self, entry, work_id, *, presentation_id, seen_sequence, expected_revision):
        """Local E04-linked acknowledgement only; not E05 Human Attention or an approval."""
        _validate(presentation_id, "Identifier")
        case = self._snapshot()
        auth = self._read_auth(entry)
        if auth["caller"]["callerClass"] != "human":
            raise WorkError("not-authorized", "human-presentation-adapter-required")
        work = self._work(case, work_id)
        metadata, _ = self._metadata(work)
        self._capability(auth, work["commandId"])
        if type(seen_sequence) is not int or not 1 <= seen_sequence <= len(case["events"]):
            raise WorkError("invalid-artifact", "seen-sequence-not-in-case")
        if case["events"][seen_sequence - 1]["workId"] != work_id:
            raise WorkError("invalid-artifact", "seen-sequence-belongs-to-another-work")
        data = {"presentationId": presentation_id, "workId": work_id, "seenSequence": seen_sequence}
        key = f"presentation:{presentation_id}"
        checksum = seal(data)["stateChecksum"]
        prior = self._existing(case, key, work["commandId"], checksum)
        if prior:
            return prior
        self._revision(case, expected_revision)
        self._capacity(case)
        reference = self._put("local-work-presentation", expected_revision + 1, {
            **data, "metadataVersion": VERSION, "notCanonicalHumanAttention": True,
        })
        return self._commit(case, work, operation="presentation-acknowledged", auth=auth, metadata=metadata,
                            refs=[reference], key=key, checksum=checksum)
