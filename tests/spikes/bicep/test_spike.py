import copy
import json
import os
from pathlib import Path
import unittest

from run_spike import SOURCE, WORKSPACE, digest, expected_result, redact, validate_mapping


class OutcomeTests(unittest.TestCase):
    def test_failed_compiler_never_satisfies_success(self):
        self.assertFalse(expected_result(1, "", "Error BCP009: invalid expression"))

    def test_real_diagnostic_required_for_negative(self):
        self.assertTrue(expected_result(1, "", "Error BCP009: invalid expression", negative=True))
        self.assertFalse(expected_result(1, "", "Bicep CLI not found.", negative=True))
        self.assertFalse(expected_result(0, "", "Error BCP009", negative=True))
        self.assertFalse(expected_result(1, "", "", negative=True))

    def test_timeout_and_missing_capture_never_pass(self):
        self.assertFalse(expected_result(0, "", "", timed_out=True))
        self.assertFalse(expected_result(0, "", "", capture_error="capture failed"))
        self.assertFalse(expected_result(None, "", "Error BCP009", negative=True))
        self.assertFalse(expected_result(1, "", "Error BCP009", negative=True, timed_out=True))

    def test_stream_redaction(self):
        self.assertEqual(redact(f"{WORKSPACE}\\main.bicep"), "[workspace]\\main.bicep")
        self.assertEqual(redact("Bearer fake-token AccountKey=example;"), "Bearer [redacted] AccountKey=[redacted];")


@unittest.skipUnless(os.environ.get("SPK_BICEP_RUN_DIRECTORY"), "Run Run-Spike.ps1 for actual compiler evidence")
class LiveCompileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(os.environ["SPK_BICEP_RUN_DIRECTORY"])
        cls.receipt = json.loads((cls.root / "receipt.json").read_text(encoding="utf-8"))
        cls.template = json.loads((cls.root / "main.arm.json").read_text(encoding="utf-8-sig"))
        cls.sidecar = json.loads((SOURCE / "promise-mapping.json").read_text(encoding="utf-8"))

    def test_live_success_and_meaningful_negative(self):
        commands = {item["id"]: item for item in self.receipt["commands"]}
        for name in ["build-valid-1", "build-valid-2"]:
            self.assertEqual(commands[name]["exitCode"], 0)
            self.assertEqual(commands[name]["outcome"], "succeeded")
        negative = commands["build-invalid"]
        self.assertNotEqual(negative["exitCode"], 0)
        self.assertEqual(negative["outcome"], "expected-negative-failure")
        self.assertTrue(negative["expectationMet"])
        stderr = (self.root / negative["stderr"]["path"]).read_text(encoding="utf-8")
        self.assertRegex(stderr, r"\bError BCP\d{3}\b")
        self.assertFalse((self.root / "tmp" / "invalid.arm.json").exists())

    def test_resource_and_promise_mapping(self):
        self.assertEqual(validate_mapping(self.template, self.sidecar), self.receipt["sourceMapping"][0])
        self.assertEqual(self.receipt["runtimePromiseStatus"], "unknown")
        self.assertEqual(self.receipt["targetPreflight"]["status"], "not-run")
        self.assertFalse(self.receipt["cloudOperationsPerformed"])

    def test_every_control_required_not_only_disabled_public_access(self):
        mutations = [
            ("publicNetworkAccess", "Enabled"),
            ("allowBlobPublicAccess", True),
            ("supportsHttpsTrafficOnly", False),
            ("minimumTlsVersion", "TLS1_0"),
            ("networkAcls", {"defaultAction": "Allow", "bypass": "AzureServices"}),
        ]
        for key, value in mutations:
            with self.subTest(property=key):
                changed = copy.deepcopy(self.template)
                changed["resources"][0]["properties"][key] = value
                with self.assertRaises(AssertionError):
                    validate_mapping(changed, self.sidecar)

    def test_wrong_resource_tag_and_promise_rejected(self):
        for key, value in [("type", "Microsoft.Storage/storageAccounts/blobServices"), ("tags", {})]:
            with self.subTest(field=key):
                changed = copy.deepcopy(self.template)
                changed["resources"][0][key] = value
                with self.assertRaises((AssertionError, KeyError)):
                    validate_mapping(changed, self.sidecar)
        sidecar = copy.deepcopy(self.sidecar)
        sidecar["resources"][0]["promiseIds"] = ["CP-99"]
        with self.assertRaises(AssertionError):
            validate_mapping(self.template, sidecar)

    def test_exact_hashes_and_repeatability(self):
        self.assertTrue(self.receipt["sourceUnchanged"])
        for item in self.receipt["files"]:
            with self.subTest(path=item["path"]):
                self.assertEqual(digest(WORKSPACE / item["path"]), item["sha256"])
        for command in self.receipt["commands"]:
            for stream in ["stdout", "stderr"]:
                self.assertEqual(digest(self.root / command[stream]["path"]), command[stream]["sha256"])
        repeat = self.receipt["repeatability"]
        self.assertEqual(repeat["sourceSha256"], digest(SOURCE / "main.bicep"))
        self.assertEqual(repeat["firstOutputSha256"], digest(self.root / "main.arm.json"))
        self.assertEqual(repeat["firstOutputSha256"], repeat["secondOutputSha256"])
        self.assertEqual(repeat["secondOutputSha256"], digest(self.root / "main.repeat.arm.json"))


if __name__ == "__main__":
    unittest.main()
