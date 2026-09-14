"""Fixture work inputs; real local filesystem/restart/failure validation only."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "apps" / "control-plane"
sys.path.insert(0, str(SOURCE))

from policy import Policy
from state.case_store import CaseStore, StoreError, canonical_bytes, seal
from tools.contracts.validate import SCHEMA, validate_contract
from work import WorkCoordinator, WorkError

OUTPUT = ROOT / ".intent-to-impact" / "spikes" / "FND-04-01"
CAPABILITIES = ["read-case", "request-generation", "validate-contracts",
                "apply-local-change", "deploy-approved-sandbox", "invoke-foundry-model"]


class WorkTests(unittest.TestCase):
    def setUp(self):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="test-work-", dir=OUTPUT)
        self.addCleanup(self.temporary.cleanup)
        self.store = CaseStore(Path(self.temporary.name) / "runs")
        manifest = json.loads((ROOT / "contracts" / "examples" / "1.0.0" / "run-manifest.json").read_text())
        manifest.update(scenarioId="DEMO-CASE-CLAIMS-V2", scenarioVersion="2.0.0", runMode="fixture", purpose="test")
        self.run = self.store.create_run(manifest)
        self.run_id = self.run["runId"]
        case = self.store.create_case(self.run_id)
        self.input_ref = self.artifact("ART-INPUT", {"text": "synthetic work input"})
        case["sections"]["requirements"] = self.input_ref
        self.store.commit(self.run_id, 0, case)
        self.policy = Policy(self.run, scope=self.run["scope"], root_id=self.run["rootId"],
                             config_id=self.run["configId"], enabled_capabilities=CAPABILITIES)
        self.human = self.policy.human_entry("harness", capabilities=CAPABILITIES)
        self.agent = self.policy.agent_entry("AGENT-LOCALPROPOSER", capabilities=CAPABILITIES)
        self.worker = self.policy.system_entry("worker", "SYSTEM-WORKER", capabilities=CAPABILITIES)
        self.other_worker = self.policy.system_entry("worker", "SYSTEM-OTHER", capabilities=CAPABILITIES)
        self.coordinator = WorkCoordinator(self.store, self.policy, self.run_id)

    def case(self):
        return self.store.read_case(self.run_id)

    def artifact(self, identifier="ART-RESULT", content=None):
        return self.store.put_artifact(self.run_id, {
            "artifactId": identifier, "runId": self.run_id, "caseId": self.run["caseId"],
            "scope": self.run["scope"], "artifactType": "local-test-artifact",
            "origin": "fixture", "content": content or {"result": "synthetic"},
        })

    def request(self, capability="request-generation", revision=None):
        return {
            "capability": capability, "expectedRevision": self.case()["logicalRevision"] if revision is None else revision,
            "actionId": "issued-work-request", "subjectId": "SUBJECT-EXAMPLE",
            "boundChecksums": {"requirements": self.input_ref["checksum"]},
        }

    def facts(self, capability="request-generation", revision=None):
        request = self.request(capability, revision)
        return self.policy.engine_facts(
            current_revision=request["expectedRevision"], capability=capability,
            action_id=request["actionId"], subject_id=request["subjectId"], checksums=request["boundChecksums"],
        )

    def enqueue(self, *, entry=None, key="client-request", capability="request-generation", payload=None):
        return self.coordinator.enqueue(
            self.agent if entry is None else entry, self.request(capability),
            idempotency_key=key, payload=payload or {"instruction": "synthetic local work"},
            dependencies={"requirements": self.input_ref}, facts=self.facts(capability),
        )

    def claim(self, queued):
        return self.coordinator.claim(self.worker, queued.work_id,
                                      expected_revision=self.case()["logicalRevision"], facts=self.facts())

    def complete(self, claimed, *, result_ref=None, revision=None):
        revision = self.case()["logicalRevision"] if revision is None else revision
        return self.coordinator.complete(
            self.worker, claimed.work_id, claimed.claim_id, expected_revision=revision,
            result_ref=result_ref or self.artifact(), facts=self.facts(revision=revision),
        )

    def test_enqueue_idempotency_same_receipt_despite_original_stale_revision(self):
        request = self.request()
        facts = self.facts()
        first = self.coordinator.enqueue(self.agent, request, idempotency_key="request",
                                         payload={"x": 1}, dependencies={"requirements": self.input_ref}, facts=facts)
        before = self.case()
        again = self.coordinator.enqueue(self.agent, request, idempotency_key="request",
                                         payload={"x": 1}, dependencies={"requirements": self.input_ref}, facts=facts)
        self.assertTrue(again.reused)
        self.assertEqual(first.receipt_ref, again.receipt_ref)
        self.assertEqual(first.work_id, again.work_id)
        self.assertEqual(self.case(), before)
        validate_contract(self.store.read_artifact(self.run_id, first.receipt_ref), "E03")

    def test_changed_duplicate_payload_conflicts(self):
        self.enqueue(payload={"x": 1})
        before = self.case()
        with self.assertRaises(WorkError) as caught:
            self.enqueue(payload={"x": 2})
        self.assertEqual(caught.exception.code, "idempotency-conflict")
        self.assertEqual(self.case(), before)

    def test_agent_cannot_schedule_human_operator_action_or_supply_attribution(self):
        for capability in ("apply-local-change", "deploy-approved-sandbox", "invoke-foundry-model"):
            with self.subTest(capability=capability), self.assertRaises(WorkError):
                self.enqueue(capability=capability)
        for field in ("actor", "activityClass", "caller", "transport"):
            with self.subTest(field=field), self.assertRaises(WorkError):
                self.enqueue(payload={field: "human"})
        self.assertEqual(self.case()["work"], [])

    def test_human_actions_are_not_silently_background_system_work(self):
        with self.assertRaises(WorkError) as caught:
            self.enqueue(entry=self.human, capability="apply-local-change")
        self.assertEqual(caught.exception.reason, "human-and-operator-actions-are-not-background-work")

    def test_schema_checksums_events_actual_executor_and_human_initiator(self):
        queued = self.enqueue(entry=self.human)
        claimed = self.claim(queued)
        self.complete(claimed)
        case = self.case()
        validate_contract(case, "D01")
        self.assertEqual([e["sequence"] for e in case["events"]], [1, 2, 3])
        self.assertEqual(len({e["eventId"] for e in case["events"]}), 3)
        self.assertEqual(case["events"][0]["actor"]["kind"], "human")
        self.assertEqual(case["events"][1]["actor"], {"kind": "system", "actorId": "SYSTEM-WORKER"})
        self.assertEqual(case["events"][2]["humanInitiator"]["actorId"], "demo-human")
        for event in case["events"]:
            validate_contract(event, "E04")
            self.assertEqual(event["stateChecksum"], seal(event)["stateChecksum"])
            for reference in event["payloadRefs"]:
                artifact = self.store.read_artifact(self.run_id, reference)
                self.assertEqual(artifact["stateChecksum"], seal(artifact)["stateChecksum"])
                if artifact["artifactType"] == "authorization-context":
                    validate_contract(artifact, "E08")
        validate_contract(case["work"][0], "E03")

    def test_agent_event_keeps_agent_attribution(self):
        self.enqueue()
        event = self.case()["events"][0]
        self.assertEqual(event["actor"], {"kind": "agent", "actorId": "AGENT-LOCALPROPOSER"})
        self.assertNotIn("humanInitiator", event)

    def test_registry_owns_product_and_operator_activity(self):
        self.enqueue()
        self.enqueue(entry=self.human, key="validate", capability="validate-contracts")
        classes = []
        for event in self.case()["events"]:
            data = self.store.read_artifact(self.run_id, event["payloadRefs"][0])
            classes.append(data["activityClass"])
        self.assertEqual(classes, ["product-workflow", "demo-operator"])

    def test_restart_preserves_queued_and_running_without_execution(self):
        queued = self.enqueue(key="queued")
        running = self.claim(self.enqueue(key="running"))
        code = (
            "import sys,json; from pathlib import Path;"
            f"sys.path.insert(0,{str(SOURCE)!r});"
            "from state.case_store import CaseStore;"
            f"c=CaseStore(Path({str(self.store.root)!r})).read_case({self.run_id!r});"
            "print(json.dumps({w['workId']:w['status'] for w in c['work']}))"
        )
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT,
                                capture_output=True, text=True, check=True)
        statuses = json.loads(result.stdout)
        self.assertEqual(statuses, {queued.work_id: "queued", running.work_id: "running"})
        restarted = WorkCoordinator(CaseStore(self.store.root), self.policy, self.run_id)
        self.assertEqual(restarted.read_work(self.worker, running.work_id)["status"], "running")

    def test_running_work_reconcile_is_uncertain_never_automatically_requeued(self):
        claimed = self.claim(self.enqueue())
        result = self.coordinator.reconcile(self.worker, claimed.work_id,
                                            expected_revision=self.case()["logicalRevision"])
        self.assertEqual(result.status, "recovery-required")
        before = self.case()
        self.assertIsNone(self.coordinator.reconcile(self.worker, claimed.work_id,
                                                     expected_revision=before["logicalRevision"]))
        self.assertEqual(self.case(), before)
        with self.assertRaises(WorkError):
            self.coordinator.claim(self.worker, claimed.work_id,
                                   expected_revision=self.case()["logicalRevision"], facts=self.facts())
        with self.assertRaises(WorkError):
            self.complete(claimed)

    def test_fresh_queued_work_reconcile_is_noop(self):
        queued = self.enqueue()
        before = self.case()
        self.assertIsNone(self.coordinator.reconcile(self.worker, queued.work_id,
                                                     expected_revision=before["logicalRevision"]))
        self.assertEqual(self.case(), before)

    def test_stale_revision_visible_then_unrelated_fresh_retry_succeeds(self):
        claimed = self.claim(self.enqueue())
        revision = self.case()["logicalRevision"]
        unrelated = self.case()
        unrelated["lifecycleState"] = "Discovering"
        self.store.commit(self.run_id, revision, unrelated)
        with self.assertRaises(WorkError) as caught:
            self.complete(claimed, revision=revision)
        self.assertEqual(caught.exception.code, "stale-revision")
        self.assertEqual(self.coordinator.read_work(self.worker, claimed.work_id)["status"], "running")
        self.assertEqual(self.complete(claimed).status, "succeeded")
        self.assertEqual(len(self.case()["events"]), 3)

    def test_commit_race_never_silently_retries(self):
        claimed = self.claim(self.enqueue())
        real_commit = self.store.commit
        def raced(run_id, revision, proposal):
            unrelated = self.case()
            unrelated["lifecycleState"] = "Discovering"
            real_commit(run_id, revision, unrelated)
            return real_commit(run_id, revision, proposal)
        with patch.object(self.store, "commit", side_effect=raced), self.assertRaises(StoreError) as caught:
            self.complete(claimed)
        self.assertEqual(caught.exception.code, "stale-revision")
        self.assertEqual(self.coordinator.read_work(self.worker, claimed.work_id)["status"], "running")
        self.assertEqual(self.complete(claimed).status, "succeeded")

    def test_changed_dependency_invalidates_completion_and_queued_reconciliation(self):
        claimed = self.claim(self.enqueue())
        queued = self.enqueue(key="second")
        changed = self.case()
        changed["sections"]["requirements"] = self.artifact("ART-NEW-INPUT", {"changed": True})
        self.store.commit(self.run_id, changed["logicalRevision"], changed)
        with self.assertRaises(WorkError) as caught:
            self.complete(claimed)
        self.assertEqual(caught.exception.code, "stale-input")
        reconciled = self.coordinator.reconcile(self.worker, queued.work_id,
                                                expected_revision=self.case()["logicalRevision"])
        self.assertEqual(reconciled.status, "stale")

    def test_omitted_dependency_cannot_bypass_bound_input_change_detection(self):
        with self.assertRaises(WorkError) as caught:
            self.coordinator.enqueue(self.agent, self.request(), idempotency_key="missing-dependency",
                                     payload={}, dependencies={}, facts=self.facts())
        self.assertEqual(caught.exception.code, "stale-input")

    def test_duplicate_completion_reuses_receipt_and_does_not_inflate_events(self):
        claimed = self.claim(self.enqueue())
        result_ref = self.artifact()
        first = self.complete(claimed, result_ref=result_ref)
        before = self.case()
        duplicate = self.complete(claimed, result_ref=result_ref, revision=0)
        self.assertTrue(duplicate.reused)
        self.assertEqual(first.receipt_ref, duplicate.receipt_ref)
        self.assertEqual(self.case(), before)
        with self.assertRaises(WorkError) as caught:
            self.complete(claimed, result_ref=self.artifact("ART-OTHER-RESULT"))
        self.assertEqual(caught.exception.code, "idempotency-conflict")

    def test_claim_cannot_be_reissued_or_completed_by_another_executor(self):
        claimed = self.claim(self.enqueue())
        with self.assertRaises(WorkError):
            self.coordinator.claim(self.worker, claimed.work_id,
                                   expected_revision=self.case()["logicalRevision"], facts=self.facts())
        with self.assertRaises(WorkError) as caught:
            self.coordinator.complete(self.other_worker, claimed.work_id, claimed.claim_id,
                                      expected_revision=self.case()["logicalRevision"],
                                      result_ref=self.artifact(), facts=self.facts())
        self.assertEqual(caught.exception.reason, "claim-owner-mismatch")

    def test_failed_capture_preserves_running_state(self):
        claimed = self.claim(self.enqueue())
        reference = self.artifact()
        before = self.case()
        with patch.object(self.store, "put_artifact", side_effect=OSError("capture-failed")), self.assertRaises(OSError):
            self.complete(claimed, result_ref=reference)
        self.assertEqual(self.case(), before)
        self.assertEqual(self.coordinator.reconcile(self.worker, claimed.work_id,
                                                   expected_revision=before["logicalRevision"]).status,
                         "recovery-required")

    def test_failed_commit_preserves_canonical_case(self):
        claimed = self.claim(self.enqueue())
        before = self.case()
        with patch.object(self.store, "commit", side_effect=OSError("before-case-replace")), self.assertRaises(OSError):
            self.complete(claimed)
        self.assertEqual(self.case(), before)

    def test_lost_commit_response_resolves_by_idempotency_not_reexecution(self):
        claimed = self.claim(self.enqueue())
        reference = self.artifact()
        real_commit = self.store.commit
        def lost_response(run_id, revision, proposal):
            real_commit(run_id, revision, proposal)
            raise OSError("response-lost-after-commit")
        with patch.object(self.store, "commit", side_effect=lost_response), self.assertRaises(OSError):
            self.complete(claimed, result_ref=reference)
        before = self.case()
        receipt = self.complete(claimed, result_ref=reference, revision=0)
        self.assertTrue(receipt.reused)
        self.assertEqual(self.case(), before)

    def test_interrupted_derived_export_does_not_lose_canonical_events(self):
        claimed = self.claim(self.enqueue())
        real_replace = self.store._replace
        def fail_export(path, data):
            if path.name == "events.ndjson":
                raise OSError("projection-only")
            return real_replace(path, data)
        with patch.object(self.store, "_replace", side_effect=fail_export), self.assertLogs("state.case_store"):
            result = self.complete(claimed)
        self.assertEqual(result.status, "succeeded")
        case = self.case()
        self.assertEqual(len(case["events"]), 3)
        self.store.rebuild_event_projection(self.run_id)
        path = self.store.root / self.run_id / "cases" / self.run["caseId"] / "events.ndjson"
        self.assertEqual(path.read_bytes(), b"".join(canonical_bytes(e) for e in case["events"]))

    def test_fail_requires_real_stored_e07_and_preserves_actual_actor(self):
        claimed = self.claim(self.enqueue())
        error = json.loads((ROOT / "contracts" / "examples" / "1.0.0" / "pre-context-error.json").read_text())
        error.update(artifactId="ART-ERROR", runId=self.run_id, caseId=self.run["caseId"], scope=self.run["scope"],
                     code="command-failed", message="Synthetic local failure.")
        error_ref = self.store.put_artifact(self.run_id, error)
        result = self.coordinator.fail(self.worker, claimed.work_id, claimed.claim_id,
                                       expected_revision=self.case()["logicalRevision"], error_ref=error_ref,
                                       facts=self.facts())
        self.assertEqual(result.status, "failed")
        self.assertEqual(self.case()["events"][-1]["actor"]["actorId"], "SYSTEM-WORKER")

    def test_record_caps_reject_without_pruning(self):
        case = self.case()
        for field, additions in (("work", {"work": 1}), ("events", {}), ("idempotencyRecords", {})):
            limit = SCHEMA["definitions"]["CaseState"]["properties"][field]["maxItems"]
            bounded = deepcopy(case)
            bounded[field] = [None] * limit
            with self.subTest(field=field), self.assertRaises(WorkError) as caught:
                self.coordinator._capacity(bounded, **additions)
            self.assertEqual(caught.exception.reason, f"{field}-capacity-exceeded")
            self.assertEqual(len(bounded[field]), limit)
        self.assertEqual(self.case(), case)

    def test_persisted_idempotency_cap_rejects_enqueue_without_state_change(self):
        case = self.case()
        case["idempotencyRecords"] = [
            {"idempotencyKey": f"other-{i}", "commandId": "read-case",
             "inputChecksum": self.input_ref["checksum"], "result": self.input_ref}
            for i in range(1000)
        ]
        before = self.store.commit(self.run_id, case["logicalRevision"], case)
        with self.assertRaises(WorkError) as caught:
            self.enqueue()
        self.assertEqual(caught.exception.reason, "idempotencyRecords-capacity-exceeded")
        self.assertEqual(self.case(), before)

    def test_fixture_worker_cannot_queue_live_provider_work(self):
        with self.assertRaises(WorkError):
            self.enqueue(entry=self.worker, capability="invoke-foundry-model")
        self.assertEqual(self.case()["work"], [])

    def test_run_mode_purpose_scope_changes_rejected(self):
        for key, value in (("runMode", "live"), ("purpose", "hero"),
                           ("scope", {**self.run["scope"], "scopeId": "SCOPE-OTHER"})):
            original = self.coordinator.manifest
            self.coordinator.manifest = {**original, key: value}
            with self.subTest(key=key), self.assertRaises(StoreError):
                self.enqueue()
            self.coordinator.manifest = original
        self.assertEqual(self.case()["work"], [])

    def test_presentation_is_idempotent_metadata_not_attention_or_approval(self):
        queued = self.enqueue()
        before_status = self.coordinator.read_work(self.worker, queued.work_id)["status"]
        result = self.coordinator.acknowledge_presentation(
            self.human, queued.work_id, presentation_id="PRESENTATION-EXAMPLE", seen_sequence=1,
            expected_revision=self.case()["logicalRevision"],
        )
        before = self.case()
        again = self.coordinator.acknowledge_presentation(
            self.human, queued.work_id, presentation_id="PRESENTATION-EXAMPLE", seen_sequence=1,
            expected_revision=0,
        )
        self.assertEqual(result.receipt_ref, again.receipt_ref)
        self.assertTrue(again.reused)
        self.assertEqual(self.case(), before)
        self.assertEqual(before_status, self.coordinator.read_work(self.worker, queued.work_id)["status"])
        self.assertNotIn("activityClass", before["events"][-1])
        with self.assertRaises(WorkError):
            self.coordinator.acknowledge_presentation(self.agent, queued.work_id,
                                                      presentation_id="PRESENTATION-OTHER", seen_sequence=1,
                                                      expected_revision=before["logicalRevision"])

    def test_reserved_keys_and_missing_results_fail_explicitly(self):
        with self.assertRaises(WorkError):
            self.enqueue(key="claim:WORK-OTHER")
        claimed = self.claim(self.enqueue())
        before = self.case()
        with self.assertRaises(FileNotFoundError):
            self.complete(claimed, result_ref={"artifactId": "ART-MISSING", "checksum": "sha256:" + "f" * 64})
        self.assertEqual(self.case(), before)

    def test_no_model_or_network_execution(self):
        with patch("socket.socket", side_effect=AssertionError("No provider/network calls")):
            claimed = self.claim(self.enqueue())
            self.complete(claimed)


if __name__ == "__main__":
    unittest.main()
