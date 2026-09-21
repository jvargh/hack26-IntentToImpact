"""Local fixture inputs only; no policy result constitutes live provider evidence."""

import copy
import hashlib
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))

from policy import ApprovalBinding, Policy, PolicyConfigurationError, same_origin
from policy.guard import REGISTRY_PATH, _Entry, _Facts
from tools.contracts.validate import validate_contract

CHECKSUMS = {"manifest": "sha256:" + "a" * 64}
REGISTRY = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["capabilities"]


def run(mode="live"):
    value = json.loads((ROOT / "contracts" / "examples" / "1.0.0" / "run-manifest.json").read_text())
    value["runMode"] = mode
    if mode == "replay":
        value["sourceRunId"] = "RUN-SOURCE-EXAMPLE"
    return value


def policy_for(value):
    return Policy(value, scope=value["scope"], root_id=value["rootId"], config_id=value["configId"],
                  enabled_capabilities=list(REGISTRY))


def request(capability="apply-local-change"):
    return {"capability": capability, "expectedRevision": 3, "actionId": "issued-action-r3",
            "subjectId": "CHANGE-EXAMPLE", "boundChecksums": copy.deepcopy(CHECKSUMS)}


def approval(capability="apply-local-change"):
    return ApprovalBinding(
        approval_id="APPROVAL-EXAMPLE", actor_id="demo-human", capability=capability,
        action_id="issued-action-r3", subject_id="CHANGE-EXAMPLE", revision=3,
        checksums=copy.deepcopy(CHECKSUMS), gate_id="delivery-ready", current=True,
    )


def facts(policy, capability="apply-local-change", **overrides):
    values = dict(current_revision=3, capability=capability, action_id="issued-action-r3",
                  subject_id="CHANGE-EXAMPLE", checksums=copy.deepcopy(CHECKSUMS),
                  gate_id="delivery-ready", gate_passed=True, approval=approval(capability))
    values.update(overrides)
    return policy.engine_facts(**values)


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.run = run()
        self.policy = policy_for(self.run)
        self.human = self.policy.human_entry("browser", capabilities=list(REGISTRY))
        self.operator = self.policy.human_entry("harness", capabilities=list(REGISTRY))
        self.model = self.policy.agent_entry("AGENT-PROBE", capabilities=list(REGISTRY),
                                            human_initiated=True)
        self.worker = self.policy.system_entry("worker", "SYSTEM-POLICYTEST",
                                               capabilities=list(REGISTRY), human_initiated=True)

    def decide(self, entry=None, payload=None, **kwargs):
        return self.policy.authorize(self.human if entry is None else entry,
                                     {"capability": "read-case"} if payload is None else payload,
                                     current_run=kwargs.pop("current_run", self.run), **kwargs)

    def assertDenied(self, result, reason):
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, reason)
        validate_contract(result.error, "E07")
        if result.authorization_context is not None:
            validate_contract(result.authorization_context, "E08")

    def test_read_builds_real_e08_fixed_human(self):
        result = self.decide()
        self.assertTrue(result.allowed)
        validate_contract(result.authorization_context, "E08")
        self.assertEqual(result.authorization_context["caller"]["actor"],
                         {"kind": "human", "actorId": "demo-human", "identityAssurance": "local-demo"})
        self.assertEqual(result.activity_class, "product-workflow")

    def test_authorization_checksum_uses_shared_trailing_newline_convention(self):
        value = copy.deepcopy(self.decide().authorization_context)
        recorded = value.pop("stateChecksum")
        canonical = (
            json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        ).encode("utf-8")
        self.assertEqual(recorded, "sha256:" + hashlib.sha256(canonical).hexdigest())

    def test_case_context_capabilities_require_a_human_and_current_engine_gate(self):
        for capability in ("create-case", "acknowledge-run-context"):
            with self.subTest(capability=capability):
                self.assertEqual(REGISTRY[capability], {
                    "profile": "human", "activityClass": "product-workflow",
                })
                payload = request(capability)
                current = facts(self.policy, capability, approval=None)
                result = self.decide(payload=payload, facts=current)
                self.assertTrue(result.allowed)
                self.assertEqual(result.activity_class, "product-workflow")
                for entry in (self.model, self.worker):
                    self.assertDenied(self.decide(entry=entry, payload=payload, facts=current),
                                      "caller-not-allowed")
                self.assertDenied(self.decide(payload=payload), "engine-facts-required")
                self.assertDenied(self.decide(
                    payload=payload,
                    facts=facts(self.policy, capability, approval=None, gate_passed=False),
                ), "gate-required")
                self.assertDenied(self.decide(
                    payload={**payload, "expectedRevision": 2}, facts=current,
                ), "stale-revision")
                self.assertDenied(self.decide(
                    payload={**payload, "boundChecksums": {"manifest": "sha256:" + "b" * 64}},
                    facts=current,
                ), "action-binding-mismatch")

    def test_case_context_capabilities_need_explicit_entry_grants(self):
        read_only = self.policy.human_entry("browser", capabilities=["read-case"])
        for capability in ("create-case", "acknowledge-run-context"):
            with self.subTest(capability=capability):
                self.assertDenied(self.decide(
                    entry=read_only, payload=request(capability),
                    facts=facts(self.policy, capability, approval=None),
                ), "capability-not-granted")

    def test_raw_e08_and_forged_handle_are_not_authority(self):
        e08 = self.decide().authorization_context
        for forged in (e08, _Entry(), {"callerClass": "human"}, "human"):
            with self.subTest(forged=type(forged).__name__):
                self.assertDenied(self.decide(entry=forged), "untrusted-entry")

    def test_handle_from_another_policy_denied(self):
        other = policy_for(self.run)
        handle = other.human_entry("browser", capabilities=["read-case"])
        self.assertDenied(self.decide(entry=handle), "untrusted-entry")

    def test_model_forged_human_and_transport_denied(self):
        for field, value in (
            ("actorId", "demo-human"), ("caller", {"callerClass": "human"}),
            ("transport", "browser"), ("channel", "harness"),
            ("authorizationContext", self.decide().authorization_context),
            ("activityClass", "product-workflow"), ("permittedCapabilities", ["apply-local-change"]),
        ):
            with self.subTest(field=field):
                self.assertDenied(self.decide(entry=self.model, payload={"capability": "read-case", field: value}),
                                  "client-authority-forbidden")

    def test_model_cannot_approve_materialize_deploy_seed_reset_verify(self):
        for capability in ("approve-design", "approve-local-delivery", "apply-local-change",
                           "deploy-approved-sandbox", "seed-approved-drift", "reset-demo", "verify-sandbox"):
            with self.subTest(capability=capability):
                self.assertDenied(self.decide(entry=self.model, payload=request(capability),
                                              facts=facts(self.policy, capability)), "caller-not-allowed")

    def test_human_initiator_never_turns_worker_into_human(self):
        result = self.decide(entry=self.worker, payload=request(), facts=facts(self.policy))
        self.assertDenied(result, "caller-not-allowed")
        self.assertEqual(result.authorization_context["caller"]["callerClass"], "system")
        self.assertEqual(result.authorization_context["humanInitiator"]["actorId"], "demo-human")

    def test_unknown_action_denied(self):
        for value in ("approve", "materialize", "shell", "unregistered", None, [], True):
            with self.subTest(value=value):
                self.assertDenied(self.decide(payload={"capability": value}), "unknown-capability")

    def test_unknown_channel_or_invalid_executor_fails_constructor(self):
        for create in (
            lambda: self.policy.human_entry("model"),
            lambda: self.policy.human_entry("unknown"),
            lambda: self.policy.agent_entry("demo-human"),
            lambda: self.policy.system_entry("browser", "SYSTEM-POLICYTEST"),
        ):
            with self.assertRaises(PolicyConfigurationError) as caught:
                create()
            validate_contract(caught.exception.error, "E07")
            self.assertNotIn("runId", caught.exception.error)

    def test_malformed_requests_fail_closed(self):
        for payload in ([], "", {}, {"capability": "read-case", "unexpected": 1},
                        {"capability": "read-case", "expectedRevision": True},
                        {"capability": "read-case", "boundChecksums": {"x": "invalid"}}):
            with self.subTest(payload=payload):
                self.assertDenied(self.decide(payload=payload), "malformed-request")
        self.assertDenied(self.policy.authorize(self.human, None, current_run=self.run), "malformed-request")

    def test_missing_grants_deny_by_default(self):
        value = run()
        policy = Policy(value, scope=value["scope"], root_id=value["rootId"], config_id=value["configId"])
        handle = policy.human_entry("browser")
        result = policy.authorize(handle, {"capability": "read-case"}, current_run=value)
        self.assertDenied(result, "capability-not-granted")

    def test_stored_context_and_config_are_detached(self):
        original = copy.deepcopy(self.run)
        self.run["scope"]["scopeId"] = "SCOPE-CHANGED"
        self.assertTrue(self.decide(current_run=original).allowed)
        self.assertDenied(self.decide(), "run-context-changed")

    def test_each_immutable_field_change_denies(self):
        modifications = {
            "runMode": "fixture", "purpose": "rehearsal", "rootId": "ROOT-CHANGED",
            "configId": "CONFIG-CHANGED", "runId": "RUN-CHANGED", "caseId": "CASE-CHANGED",
            "scenarioId": "SCENARIO-CHANGED", "scenarioVersion": "2.0.0",
            "scenarioHash": "sha256:" + "f" * 64,
            "scope": {**self.run["scope"], "resourceGroup": "not-approved"},
        }
        for key, value in modifications.items():
            changed = {**self.run, key: value}
            with self.subTest(key=key):
                self.assertDenied(self.decide(current_run=changed), "run-context-changed")

    def test_payload_context_overrides_denied_even_when_equal(self):
        for key in ("runMode", "purpose", "scope", "rootId", "configId"):
            self.assertDenied(self.decide(payload={"capability": "read-case", key: self.run[key]}),
                              "client-authority-forbidden")

    def test_invalid_run_shape_denied(self):
        self.assertDenied(self.decide(current_run={}), "invalid-run-context")

    def test_fixture_and_replay_cannot_live_provider_or_proof(self):
        for mode in ("fixture", "replay"):
            value = run(mode)
            policy = policy_for(value)
            worker = policy.system_entry("worker", "SYSTEM-TEST", capabilities=list(REGISTRY))
            human = policy.human_entry("harness", capabilities=list(REGISTRY))
            for capability in ("invoke-foundry-model", "observe-azure", "collect-live-proof",
                               "deploy-approved-sandbox", "seed-approved-drift", "verify-sandbox"):
                entry = worker if REGISTRY[capability]["profile"] == "provider" else human
                result = policy.authorize(entry, request(capability), current_run=value,
                                          facts=facts(policy, capability, execution_authorized=True,
                                                      operator_consent=True))
                self.assertDenied(result, "live-mode-required")
                self.assertNotIn(capability, result.authorization_context["permittedCapabilities"])

    def test_materialization_requires_matching_current_engine_approval(self):
        handle = facts(self.policy)
        self.assertTrue(self.decide(payload=request(), facts=handle).allowed)
        self.assertDenied(self.decide(payload=request()), "engine-facts-required")
        self.assertDenied(self.decide(payload=request(), facts=_Facts()), "engine-facts-required")
        self.assertDenied(self.decide(payload=request(), facts={"approval": True}), "engine-facts-required")
        for changed in (
            None, replace(approval(), current=False), replace(approval(), revision=2),
            replace(approval(), capability="approve-local-delivery"),
            replace(approval(), action_id="other-action"), replace(approval(), subject_id="CHANGE-OTHER"),
            replace(approval(), checksums={"manifest": "sha256:" + "b" * 64}),
            replace(approval(), gate_id="other-gate"),
        ):
            with self.subTest(changed=changed):
                self.assertDenied(self.decide(payload=request(), facts=facts(self.policy, approval=changed)),
                                  "approval-required")

    def test_materialization_requires_current_passed_gate(self):
        for change in ({"gate_passed": False}, {"gate_id": None}):
            self.assertDenied(self.decide(payload=request(), facts=facts(self.policy, **change)), "gate-required")

    def test_stale_revision_has_contract_error_details(self):
        result = self.decide(payload={**request(), "expectedRevision": 2}, facts=facts(self.policy))
        self.assertDenied(result, "stale-revision")
        self.assertEqual((result.error["expectedRevision"], result.error["actualRevision"]), (2, 3))

    def test_action_subject_checksums_must_match_engine(self):
        for change in ({"actionId": "other-action"}, {"subjectId": "CHANGE-OTHER"},
                       {"boundChecksums": {}}, {"boundChecksums": {"manifest": "sha256:" + "f" * 64}}):
            self.assertDenied(self.decide(payload={**request(), **change}, facts=facts(self.policy)),
                              "action-binding-mismatch")

    def test_policy_success_is_not_engine_approval(self):
        result = self.decide()
        with self.assertRaises(PolicyConfigurationError):
            facts(self.policy, approval=result)
        self.assertDenied(self.decide(payload=request(), facts=facts(self.policy, approval=None)),
                          "approval-required")

    def test_current_facts_are_detached_from_mutable_approval(self):
        bound = approval()
        handle = facts(self.policy, approval=bound)
        bound.checksums["manifest"] = "sha256:" + "c" * 64
        self.assertTrue(self.decide(payload=request(), facts=handle).allowed)

    def test_model_can_request_controlled_local_work_not_provider(self):
        cap = "request-generation"
        self.assertTrue(self.decide(entry=self.model, payload=request(cap),
                                    facts=facts(self.policy, cap, approval=None)).allowed)
        cap = "invoke-foundry-model"
        self.assertDenied(self.decide(entry=self.model, payload=request(cap),
                                     facts=facts(self.policy, cap, execution_authorized=True)), "caller-not-allowed")

    def test_worker_live_call_requires_engine_authorization(self):
        cap = "invoke-foundry-model"
        self.assertDenied(self.decide(entry=self.worker, payload=request(cap), facts=facts(self.policy, cap)),
                          "engine-execution-required")
        self.assertTrue(self.decide(entry=self.worker, payload=request(cap),
                                    facts=facts(self.policy, cap, execution_authorized=True)).allowed)

    def test_human_approval_action_does_not_require_previous_approval(self):
        cap = "approve-local-delivery"
        self.assertTrue(self.decide(payload=request(cap), facts=facts(self.policy, cap, approval=None)).allowed)

    def test_operator_actions_harness_only_explicit_consent(self):
        cap = "deploy-approved-sandbox"
        self.assertDenied(self.decide(payload=request(cap), facts=facts(self.policy, cap, operator_consent=True)),
                          "caller-not-allowed")
        self.assertDenied(self.decide(entry=self.operator, payload=request(cap), facts=facts(self.policy, cap)),
                          "operator-consent-required")
        result = self.decide(entry=self.operator, payload=request(cap),
                             facts=facts(self.policy, cap, operator_consent=True))
        self.assertTrue(result.allowed)
        self.assertEqual(result.activity_class, "demo-operator")

    def test_activity_class_is_registry_owned(self):
        result = self.decide(payload={"capability": "validate-contracts"})
        self.assertEqual(result.activity_class, "demo-operator")
        self.assertDenied(self.decide(payload={"capability": "validate-contracts", "activityClass": "product-workflow"}),
                          "client-authority-forbidden")

    def test_invalid_engine_facts_and_registry_fail_closed(self):
        for kwargs in ({"current_revision": True}, {"current_revision": -1},
                       {"current_revision": 3, "gate_passed": "yes"},
                       {"current_revision": 3, "approval": {"approved": True}}):
            with self.assertRaises(PolicyConfigurationError):
                self.policy.engine_facts(**kwargs)
        for content in ("{", "{}", '{"version":"1.0.0","capabilities":{"foo":{"profile":"unknown","activityClass":"product-workflow"}}}'):
            with patch("policy.guard.REGISTRY_PATH") as path, self.assertRaises(PolicyConfigurationError):
                path.read_text.return_value = content
                policy_for(self.run)

    def test_mismatched_server_scope_rejected_before_context(self):
        with self.assertRaises(PolicyConfigurationError) as caught:
            Policy(self.run, scope={**self.run["scope"], "scopeId": "SCOPE-OTHER"},
                   root_id=self.run["rootId"], config_id=self.run["configId"])
        self.assertNotIn("runId", caught.exception.error)

    def test_guard_has_no_network_or_process_effects(self):
        with patch("socket.socket", side_effect=AssertionError("No network")), \
                patch("subprocess.run", side_effect=AssertionError("No processes")):
            self.assertTrue(self.decide().allowed)
            self.assertDenied(self.decide(entry=self.model, payload=request()), "caller-not-allowed")

    def test_exact_origin_host_helper(self):
        expected = "http://127.0.0.1:8765"
        self.assertTrue(same_origin(expected, "127.0.0.1:8765", expected_origin=expected))
        for origin, host in (("null", "127.0.0.1:8765"), ("http://localhost:8765", "127.0.0.1:8765"),
                             (expected, "attacker.example"), (expected + "/", "127.0.0.1:8765"),
                             ("http://127.0.0.1:8765.attacker.example", "127.0.0.1:8765")):
            self.assertFalse(same_origin(origin, host, expected_origin=expected))
        self.assertFalse(same_origin(None, None, expected_origin=expected))


if __name__ == "__main__":
    unittest.main()
