"""These tests never call Azure or mutate approval/source fixtures."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock

from bootstrap import (
    ACCOUNT_ID, APPROVAL_FILE, FOUR, GROUP_ID, PARAMETERS, SCENARIO_FILE, SOURCE,
    Run, inspect_template, inspect_what_if, load, normalize, policy_type_condition, require_absent, validate_inputs,
)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.approval = load(APPROVAL_FILE)
        self.scenario = load(SCENARIO_FILE)
        self.parameters = load(SOURCE / "main.parameters.json")

    def test_exact_real_approval_and_canonical_v2(self):
        validate_inputs(self.approval, self.scenario, self.parameters)

    def test_missing_or_unapproved_consent_rejected(self):
        for change in [{}, {**self.approval, "status": "approval-required"},
                       {**self.approval, "userResponse": "no"}]:
            with self.assertRaises(ValueError):
                validate_inputs(change, self.scenario, self.parameters)

    def test_wrong_approval_scope_settings_or_parameters_rejected(self):
        for field in ["subscriptionId", "resourceGroup", "location", "storageAccountName"]:
            changed = copy.deepcopy(self.approval)
            changed["scope"][field] = "not-approved"
            with self.assertRaises(ValueError):
                validate_inputs(changed, self.scenario, self.parameters)
        for field, value in [("supportsHttpsTrafficOnly", False), ("allowBlobPublicAccess", True)]:
            changed = copy.deepcopy(self.approval)
            changed["storageSettings"][field] = value
            with self.assertRaises(ValueError):
                validate_inputs(changed, self.scenario, self.parameters)
        changed = copy.deepcopy(self.parameters)
        changed["parameters"]["storageAccountName"]["value"] = "unapprovedaccount"
        with self.assertRaises(ValueError):
            validate_inputs(self.approval, self.scenario, changed)

    def test_scenario_mutation_cannot_be_relabelled_v2_proof(self):
        changed = copy.deepcopy(self.scenario)
        changed["desiredStorageConfiguration"]["publicNetworkAccess"] = "Disabled"
        with self.assertRaises(ValueError):
            validate_inputs(self.approval, changed, self.parameters)

    def test_existing_or_unknown_name_scope_rejected(self):
        require_absent(False, {"nameAvailable": True})
        for exists, available in [(True, True), (None, True), (False, False), (False, None)]:
            with self.assertRaises(ValueError):
                require_absent(exists, {"nameAvailable": available})

    def test_no_create_without_preflight_and_execution_flag(self):
        run = object.__new__(Run)
        run.execute = False
        run.receipt = {}
        run.command = Mock()
        with self.assertRaises(ValueError):
            run.create()
        run.command.assert_not_called()

    def test_seed_extra_resource_and_delete_flags_rejected_before_runner(self):
        for flag in ["--seed", "--delete", "--role", "--storage-account-name=other", "--extra-resource=vm"]:
            result = subprocess.run([sys.executable, "-B", str(SOURCE / "bootstrap.py"), flag],
                                    capture_output=True, timeout=15, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"unrecognized arguments", result.stderr)

    def test_cli_and_arm_https_aliases_normalize_without_defaults(self):
        arm = {"properties": copy.deepcopy(FOUR)}
        cli = copy.deepcopy(FOUR)
        cli["enableHttpsTrafficOnly"] = cli.pop("supportsHttpsTrafficOnly")
        self.assertEqual(normalize(arm)["properties"], normalize(cli)["properties"])
        self.assertEqual(normalize(cli)["sourcePropertyNames"]["supportsHttpsTrafficOnly"], ["enableHttpsTrafficOnly"])
        cli["enableHttpsTrafficOnly"] = False
        self.assertFalse(normalize(cli)["matchesDesired"])

    def test_missing_null_conflicting_or_wrong_type_properties_rejected(self):
        for value in [None, "true", 1]:
            raw = copy.deepcopy(FOUR)
            raw["supportsHttpsTrafficOnly"] = value
            with self.assertRaises(ValueError):
                normalize(raw)
        raw = copy.deepcopy(FOUR)
        del raw["supportsHttpsTrafficOnly"]
        with self.assertRaises(ValueError):
            normalize(raw)
        raw = copy.deepcopy(FOUR)
        raw["enableHttpsTrafficOnly"] = False
        with self.assertRaises(ValueError):
            normalize(raw)

    def test_what_if_allows_only_two_exact_creates(self):
        preview = {"changes": [{"resourceId": GROUP_ID, "changeType": "Create"},
                               {"resourceId": ACCOUNT_ID, "changeType": "Create"}]}
        inspect_what_if(preview)
        for change_type in ["Modify", "Delete", "Ignore", "NoChange"]:
            changed = copy.deepcopy(preview)
            changed["changes"][1]["changeType"] = change_type
            with self.assertRaises(ValueError):
                inspect_what_if(changed)

        changed = copy.deepcopy(preview)
        changed["changes"].append({"resourceId": ACCOUNT_ID + "/forbidden", "changeType": "Create"})
        with self.assertRaises(ValueError):
            inspect_what_if(changed)

    def test_policy_type_exclusion_never_guesses_unknown_conditions(self):
        storage = "Microsoft.Storage/storageAccounts"
        self.assertIs(policy_type_condition({"allOf": [{"field": "type", "equals": "Microsoft.Resources/subscriptions"}]}, storage), False)
        self.assertIsNone(policy_type_condition({"field": "tags[owner]", "equals": "someone"}, storage))
        self.assertIsNone(policy_type_condition({"anyOf": [
            {"field": "type", "equals": "Microsoft.Resources/subscriptions"},
            {"field": "tags[owner]", "equals": "someone"}]}, storage))
        self.assertIs(policy_type_condition({"field": "type", "equals": storage}, storage), True)
        blob = "Microsoft.Storage/storageAccounts/allowBlobPublicAccess"
        self.assertIs(policy_type_condition({"anyOf": [
            {"field": blob, "exists": "false"}, {"field": blob, "equals": "true"}]}, storage), False)
        self.assertIsNone(policy_type_condition({"field": "Microsoft.Storage/storageAccounts/undeclared", "exists": "false"}, storage))
        self.assertIs(policy_type_condition({"allof": [
            {"field": "type", "equals": "Microsoft.CognitiveServices/accounts"},
            {"AnyOf": [{"field": "kind", "equals": "OpenAI"}]}]}, storage), False)
        self.assertIs(policy_type_condition({"field": "type", "in": ["Microsoft.Compute/virtualMachines"]}, storage), False)

    def test_public_network_modify_blocks_despite_successful_target_preview(self):
        run = object.__new__(Run)
        run.receipt = {"targetValidation": "passed", "whatIf": "create-only-approved-resources"}
        run.rest = Mock(return_value={"properties": {"policyRule": {
            "if": {"allOf": [
                {"field": "type", "equals": "Microsoft.Storage/storageAccounts"},
                {"field": "Microsoft.Storage/storageAccounts/publicNetworkAccess", "notEquals": "Disabled"}
            ]},
            "then": {"effect": "modify"}
        }}})
        with self.assertRaisesRegex(ValueError, "Potential unapproved Azure Policy side effect"):
            run.check_policy_effects([{"policyDefinitionId": "synthetic-policy-test-only", "enforcementMode": "Default"}])
        run.rest.assert_called_once()


@unittest.skipUnless(os.environ.get("SPK_BOOTSTRAP_ARTIFACTS"), "Use bootstrap.py for actual compiled-template tests")
class CompiledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(os.environ["SPK_BOOTSTRAP_ARTIFACTS"])
        cls.template = load(cls.root / "main.arm.json")

    def test_actual_compiled_template_exact_allowlist(self):
        inspect_template(self.template)
        self.assertEqual((self.root / "main.arm.json").read_bytes(), (self.root / "main.repeat.arm.json").read_bytes())

    def test_compiled_extra_role_or_resource_rejected(self):
        for resource in [{"type": "Microsoft.Authorization/roleAssignments"},
                         {"type": "Microsoft.Compute/virtualMachines"},
                         {"type": "Microsoft.Storage/storageAccounts/blobServices/containers"}]:
            changed = copy.deepcopy(self.template)
            changed["resources"][1]["properties"]["template"]["resources"].append(resource)
            with self.assertRaises(ValueError):
                inspect_template(changed)

    def test_compiled_seed_and_bad_nested_scope_rejected(self):
        changed = copy.deepcopy(self.template)
        account = changed["resources"][1]["properties"]["template"]["resources"][0]
        account["properties"]["supportsHttpsTrafficOnly"] = False
        with self.assertRaises(ValueError):
            inspect_template(changed)
        changed = copy.deepcopy(self.template)
        changed["resources"][1]["resourceGroup"] = "different-group"
        with self.assertRaises(ValueError):
            inspect_template(changed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
