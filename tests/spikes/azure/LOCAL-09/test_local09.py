"""Unit examples are fixtures; compiled tests use actual retained Bicep output."""

import copy
import os
from pathlib import Path
import subprocess
import sys
import unittest

from evidence import (
    ASSOCIATION, ASSOCIATION_ID, DECISION, NSP_ID, PLANNED_IDS, PROFILE, PROFILE_ID,
    OWNED, ROOT, SOURCE, STORAGE_ID, ReadOnlyRun, load,
)
from guards import (
    ASSOCIATION_TYPE, PROFILE_TYPE, STORAGE_PROPERTIES, STORAGE_TYPE, absence_guard,
    decision_guard, final_confirmation_guard, observation_guard, plan_guard, preview_guard, template_guard,
)
from prepare import condition_known, effect_override_value, permitted


def fixture_observation():
    return {
        "evidenceOrigin": "fixture",
        "storage": {"id": STORAGE_ID, "properties": {**copy.deepcopy(STORAGE_PROPERTIES), "provisioningState": "Succeeded"}},
        "nsp": {"id": NSP_ID, "properties": {"provisioningState": "Succeeded", "perimeterGuid": "fixture-perimeter-generation"}},
        "profile": {"id": PROFILE_ID, "properties": {"accessRulesVersion": "0"}},
        "association": {"id": ASSOCIATION_ID, "properties": {
            "provisioningState": "Succeeded", "hasProvisioningIssues": "no", "accessMode": "Enforced",
            "privateLinkResource": {"id": STORAGE_ID}, "profile": {"id": PROFILE_ID}}},
        "profileRules": {"value": []},
        "storageConfigurations": {"value": [{"properties": {
            "provisioningState": "Succeeded", "provisioningIssues": [],
            "networkSecurityPerimeter": {"id": NSP_ID, "perimeterGuid": "fixture-perimeter-generation"},
            "resourceAssociation": {"name": ASSOCIATION, "accessMode": "Enforced"},
            "profile": {"name": PROFILE, "accessRules": [], "accessRulesVersion": 0.0}}}]},
    }


class GuardTests(unittest.TestCase):
    def test_exact_local09_and_parameters(self):
        decision_guard(load(DECISION), load(ROOT / "infra" / "main.parameters.json"))

    def test_plan_matches_candidate_and_pending_authorization(self):
        plan = load(ROOT / ".azure" / "infrastructure-plan.json")
        plan_guard(plan)
        for mutation in ["extra", "cycle", "approved"]:
            changed = copy.deepcopy(plan)
            if mutation == "extra":
                changed["plan"]["resources"].append({"name": "extra"})
            elif mutation == "cycle":
                changed["plan"]["resources"][0]["dependencies"] = [ASSOCIATION]
            else:
                changed["meta"]["status"] = "approved"
            with self.assertRaises(ValueError):
                plan_guard(changed)

    def test_old_approval_does_not_authorize_nsp(self):
        old = load(ROOT / ".intent-to-impact" / "execution" / "decisions" / "APPROVAL-SANDBOX-CREATE-001.json")
        with self.assertRaises(ValueError):
            final_confirmation_guard(old, "compiled", "parameters", "decision")
        with self.assertRaises(ValueError):
            final_confirmation_guard({}, "compiled", "parameters", "decision")

    def test_changed_hashes_scope_or_missing_risk_ack_rejected(self):
        fixture = {"decisionId": "LOCAL-09", "recordType": "explicit-risk-acknowledged-deployment-consent",
                   "acknowledgedRisks": True, "compiledSha256": "c", "parametersSha256": "p",
                   "decisionSha256": "d", "plannedResourceIds": PLANNED_IDS,
                   "seedApproved": False, "cleanupApproved": False}
        final_confirmation_guard(fixture, "c", "p", "d")
        for key, value in [("compiledSha256", "changed"), ("parametersSha256", "changed"),
                           ("decisionSha256", "changed"), ("acknowledgedRisks", False),
                           ("plannedResourceIds", []), ("seedApproved", True)]:
            changed = copy.deepcopy(fixture)
            changed[key] = value
            with self.assertRaises(ValueError):
                final_confirmation_guard(changed, "c", "p", "d")

    def test_rules_transition_learning_enabled_and_wrong_scope_rejected(self):
        for key, value in [("inboundAccessRules", ["0.0.0.0/0"]), ("outboundAccessRules", ["*.example.com"]),
                           ("associationAccessMode", "Learning"), ("associationAccessMode", "Transition"),
                           ("desiredPublicNetworkAccess", "Enabled"), ("resourceGroupName", "another-group")]:
            decision = load(DECISION)
            decision["target"][key] = value
            with self.assertRaises(ValueError):
                decision_guard(decision, load(ROOT / "infra" / "main.parameters.json"))

    def test_existing_or_unknown_target_rejected(self):
        absence_guard(False, {"nameAvailable": True})
        for exists, available in [(True, True), (None, True), (False, False), (False, None)]:
            with self.assertRaises(ValueError):
                absence_guard(exists, {"nameAvailable": available})

    def test_readonly_transport_has_no_mutation_path(self):
        run = object.__new__(ReadOnlyRun)
        for args in [["deployment", "sub", "create"], ["group", "create"], ["storage", "account", "update"],
                     ["provider", "register"], ["role", "assignment", "create"], ["tag", "update"],
                     ["policy", "exemption", "create"], ["rest", "--method", "put"]]:
            with self.assertRaises(ValueError):
                run.command("forbidden", args)

    def test_cli_rejects_mutation_flags_before_execution(self):
        for flag in ["--execute-approved", "--seed", "--delete", "--allow-rule", "--adopt"]:
            result = subprocess.run([sys.executable, "-B", str(SOURCE / "prepare.py"), flag],
                                    capture_output=True, timeout=15, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"unrecognized arguments", result.stderr)

    def test_secured_by_perimeter_alone_cannot_pass(self):
        with self.assertRaises(KeyError):
            observation_guard({"storage": fixture_observation()["storage"]})

    def test_fixture_complete_configuration_is_not_dataplane_proof(self):
        result = observation_guard(fixture_observation())
        self.assertTrue(result["technicalConfigurationComplete"])
        self.assertFalse(result["dataPlaneBlockingTestPerformed"])
        self.assertIsNone(result["canonicalScenarioBinding"])

    def test_missing_or_wrong_real_association_profile_rejected(self):
        for key, value in [("accessMode", "Learning"), ("accessMode", "Transition"),
                           ("profile", {"id": "wrong-profile"}), ("privateLinkResource", {"id": "wrong-storage"}),
                           ("hasProvisioningIssues", "yes"), ("provisioningState", "Failed")]:
            observation = fixture_observation()
            observation["association"]["properties"][key] = value
            with self.assertRaises(ValueError):
                observation_guard(observation)
        observation = fixture_observation()
        del observation["association"]["properties"]["accessMode"]
        with self.assertRaises(KeyError):
            observation_guard(observation)

    def test_configuration_sync_failure_or_stale_rules_rejected(self):
        for change in ["failed", "issues", "version", "effective-rules", "missing", "wrong-perimeter"]:
            observation = fixture_observation()
            config = observation["storageConfigurations"]["value"][0]["properties"]
            if change == "failed":
                config["provisioningState"] = "Updating"
            elif change == "issues":
                config["provisioningIssues"] = [{"name": "ConfigurationPropagationFailure"}]
            elif change == "version":
                config["profile"]["accessRulesVersion"] = 9
            elif change == "effective-rules":
                config["profile"]["accessRules"] = [{"direction": "Inbound"}]
            elif change == "missing":
                observation["storageConfigurations"]["value"] = []
            else:
                config["networkSecurityPerimeter"]["id"] = "wrong"
            with self.assertRaises(ValueError):
                observation_guard(observation)

    def test_access_rules_and_partial_inventory_rejected(self):
        for listing in [{"value": [{"name": "rule"}]}, {"value": [], "nextLink": "more"}]:
            observation = fixture_observation()
            observation["profileRules"] = listing
            with self.assertRaises(ValueError):
                observation_guard(observation)

    def test_policy_exclusion_uses_secured_state_not_old_v2(self):
        clause = {"allOf": [
            {"field": "type", "equals": STORAGE_TYPE},
            {"field": STORAGE_TYPE + "/publicNetworkAccess", "notEquals": "Disabled"},
            {"field": STORAGE_TYPE + "/publicNetworkAccess", "notEquals": "SecuredByPerimeter"}]}
        self.assertIs(condition_known(clause, STORAGE_TYPE), False)
        self.assertIsNone(condition_known({"field": "tags[unknown]", "equals": "x"}, STORAGE_TYPE))
        vm_only = {"anyOf": [
            {"allOf": [{"field": "type", "equals": "Microsoft.Compute/virtualMachines"},
                       {"field": "Microsoft.Compute/virtualMachines/osDisk.uri", "exists": "True"}]},
            {"field": "type", "equals": "Microsoft.Compute/VirtualMachineScaleSets"}]}
        for resource_type in [STORAGE_TYPE, "Microsoft.Network/networkSecurityPerimeters", PROFILE_TYPE, ASSOCIATION_TYPE]:
            self.assertIs(condition_known(vm_only, resource_type), False)

    def test_permissions_not_actions_are_honored(self):
        permission = {"value": [{"actions": ["Microsoft.Network/*"], "notActions": ["*/write"]}]}
        self.assertTrue(permitted(permission, "Microsoft.Network/networkSecurityPerimeters/read"))
        self.assertFalse(permitted(permission, "Microsoft.Network/networkSecurityPerimeters/write"))

    def test_only_unconditional_nonmutating_policy_override_is_accepted(self):
        self.assertEqual(effect_override_value([{"kind": "policyEffect", "value": "Deny"}]), "Deny")
        for value in [[{"kind": "policyEffect", "value": "modify"}],
                      [{"kind": "policyEffect", "value": "Deny", "selectors": []}]]:
            with self.assertRaises(ValueError):
                effect_override_value(value)


@unittest.skipUnless(os.environ.get("SPK_LOCAL09_ARTIFACTS"), "Use prepare.py to test actual compiled artifacts")
class CompiledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts = Path(os.environ["SPK_LOCAL09_ARTIFACTS"])
        cls.template = load(cls.artifacts / "main.arm.json")

    def test_actual_repeatable_compile_and_exact_resource_graph(self):
        template_guard(self.template)
        self.assertEqual((self.artifacts / "main.arm.json").read_bytes(), (self.artifacts / "main.repeat.arm.json").read_bytes())

    def test_extra_rule_iam_or_resource_rejected(self):
        for kind in [PROFILE_TYPE + "/accessRules", "Microsoft.Authorization/roleAssignments", "Microsoft.KeyVault/vaults"]:
            template = copy.deepcopy(self.template)
            template["resources"][1]["properties"]["template"]["resources"].append({"type": kind})
            with self.assertRaises(ValueError):
                template_guard(template)

    def test_unsafe_mode_public_state_exclusion_and_order_rejected(self):
        for mutation in ["mode", "enabled", "exclusion", "order", "numeric-boolean"]:
            template = copy.deepcopy(self.template)
            by_type = {r["type"]: r for r in template["resources"][1]["properties"]["template"]["resources"]}
            if mutation == "mode":
                by_type[ASSOCIATION_TYPE]["properties"]["accessMode"] = "Learning"
            elif mutation == "enabled":
                by_type[STORAGE_TYPE]["properties"]["publicNetworkAccess"] = "Enabled"
            elif mutation == "exclusion":
                by_type[STORAGE_TYPE]["tags"]["SecurityControl"] = "Ignore"
            elif mutation == "numeric-boolean":
                by_type[STORAGE_TYPE]["properties"]["allowBlobPublicAccess"] = 0
            else:
                by_type[ASSOCIATION_TYPE]["dependsOn"] = []
            with self.assertRaises(ValueError):
                template_guard(template)

    def test_failed_partial_or_update_preview_rejected(self):
        with self.assertRaises(ValueError):
            preview_guard({"changes": []})
        for result in [{"error": {"code": "Failure"}}, {"changes": [{"resourceId": PLANNED_IDS[0], "changeType": "Modify"}]},
                       {"changes": [{"resourceId": "wrong", "changeType": "Create"}]}]:
            with self.assertRaises(ValueError):
                preview_guard(result)

    @unittest.skipUnless((OWNED / "candidate-20260913T012617540781Z" / "full-what-if.stdout.txt").is_file(),
                         "No retained live what-if evidence in a fresh workspace")
    def test_actual_retained_preview_properties_and_bindings(self):
        preview = load(OWNED / "candidate-20260913T012617540781Z" / "full-what-if.stdout.txt")
        preview_guard(preview)
        for mutation in ["https", "missing", "association", "tag"]:
            changed = copy.deepcopy(preview)
            storage = next(c["after"] for c in changed["changes"] if c["resourceId"].lower() == STORAGE_ID.lower())
            if mutation == "https":
                storage["properties"]["supportsHttpsTrafficOnly"] = False
            elif mutation == "missing":
                del storage["properties"]["allowBlobPublicAccess"]
            elif mutation == "tag":
                storage["tags"]["SecurityControl"] = "Ignore"
            else:
                association = next(c["after"] for c in changed["changes"] if c["resourceId"].lower() == ASSOCIATION_ID.lower())
                association["properties"]["profile"]["id"] = "wrong"
            with self.assertRaises(ValueError):
                preview_guard(changed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
