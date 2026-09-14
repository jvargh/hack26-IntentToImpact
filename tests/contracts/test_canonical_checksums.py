"""Cross-component canonical checksum compatibility; no store writes or provider calls."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))

from policy import Policy
from state.case_store import canonical_bytes, seal
from tools.contracts.integrity import semantic_checksum
from tools.contracts.validate import validate_contract


class CanonicalChecksumTests(unittest.TestCase):
    def test_non_ascii_payload_matches_real_store_and_foundation_vector(self):
        payload = {"customerImpact": "Claims — HTTPS protection"}
        expected = "sha256:e798e0dba8ca5b3cb2cd3054d864138e8db1469e27cd71ccd3eef971af232263"
        stored = seal(payload)
        self.assertEqual(stored["stateChecksum"], expected)
        self.assertEqual(semantic_checksum(payload), stored["stateChecksum"])
        self.assertEqual(semantic_checksum(stored), stored["stateChecksum"])
        self.assertTrue(canonical_bytes(payload).isascii())
        self.assertIn(b"\\u2014", canonical_bytes(payload))
        self.assertTrue(canonical_bytes(payload).endswith(b"\n"))
        self.assertNotIn("stateChecksum", payload)

    def test_nested_unicode_keys_values_and_surrogate_pairs_match_real_store(self):
        payload = {
            "résumé": {"claims": ["保険", "Café", "🔒", "e\u0301"], "note": "HTTPS — protection"},
            "stateChecksum": "sha256:" + "0" * 64,
        }
        original = deepcopy(payload)
        stored = seal(payload)
        self.assertEqual(semantic_checksum(payload), stored["stateChecksum"])
        self.assertEqual(semantic_checksum(stored), stored["stateChecksum"])
        self.assertEqual(payload, original)
        serialized = canonical_bytes({key: value for key, value in payload.items() if key != "stateChecksum"})
        self.assertTrue(serialized.isascii())
        self.assertIn(b"\\ud83d\\udd12", serialized)

    def test_actual_policy_unicode_output_matches_real_store_and_shared_helper(self):
        run = json.loads((ROOT / "contracts" / "examples" / "1.0.0" / "run-manifest.json").read_text(encoding="utf-8"))
        run["scope"]["resourceGroup"] = "rg-café-例"
        run = seal(run)
        policy = Policy(
            run, scope=run["scope"], root_id=run["rootId"], config_id=run["configId"],
            enabled_capabilities=("read-case",),
        )
        entry = policy.human_entry("browser", capabilities=("read-case",))
        result = policy.authorize(entry, {"capability": "read-case"}, current_run=run)
        self.assertTrue(result.allowed, result.reason)
        output = result.authorization_context
        validate_contract(output, "E08")
        self.assertEqual(output["scope"]["resourceGroup"], "rg-café-例")
        self.assertEqual(semantic_checksum(output), output["stateChecksum"])
        self.assertEqual(seal(output)["stateChecksum"], output["stateChecksum"])
        self.assertIn(b"\\u00e9", canonical_bytes(output))
        self.assertIn(b"\\u4f8b", canonical_bytes(output))


if __name__ == "__main__":
    unittest.main()
