from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[2]
STATE_SOURCE = ROOT / "apps" / "control-plane" / "state"
sys.path.insert(0, str(STATE_SOURCE))
sys.path.insert(0, str(STATE_SOURCE.parent))
from case_store import CaseStore, StoreError, canonical_bytes, seal
from policy import Policy


class CaseStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="iti-case-store-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.store = CaseStore(self.directory / "runs")
        manifest = json.loads(
            (ROOT / "contracts" / "examples" / "1.0.0" / "run-manifest.json").read_text()
        )
        manifest.update(
            runMode="fixture", purpose="test",
            scenarioId="DEMO-CASE-CLAIMS-V2", scenarioVersion="2.0.0",
        )
        manifest.pop("sourceRunId", None)
        self.manifest = self.store.create_run(manifest)
        self.run_id = self.manifest["runId"]
        self.case = self.store.create_case(self.run_id)
        self.case_path = (
            self.store.root / self.run_id / "cases" / self.manifest["caseId"] / "case.json"
        )

    def test_restart_loads_same_revision_and_verified_checksum(self) -> None:
        proposal = deepcopy(self.case)
        proposal["lifecycleState"] = "Discovering"
        committed = self.store.commit(self.run_id, 0, proposal)
        restarted = CaseStore(self.store.root)
        self.assertEqual(restarted.read_case(self.run_id), committed)
        self.assertEqual(committed["logicalRevision"], 1)
        self.assertEqual(committed["stateChecksum"], seal(committed)["stateChecksum"])
        self.assertEqual(
            (self.case_path.parent / "events.ndjson").read_bytes(), b""
        )

    def test_stale_revision_preserves_authoritative_bytes(self) -> None:
        before = self.case_path.read_bytes()
        with self.assertRaises(StoreError) as caught:
            self.store.commit(self.run_id, 9, self.case)
        self.assertEqual(caught.exception.code, "stale-revision")
        self.assertEqual(self.case_path.read_bytes(), before)

    def test_malformed_proposal_is_rejected_before_write(self) -> None:
        before = self.case_path.read_bytes()
        proposal = deepcopy(self.case)
        del proposal["runId"]
        with self.assertRaises(ValidationError):
            self.store.commit(self.run_id, 0, proposal)
        self.assertEqual(self.case_path.read_bytes(), before)

    def test_run_context_cannot_change_mode_scope_or_purpose(self) -> None:
        for name, value in (
            ("runMode", "live"), ("purpose", "hero"),
            ("scenarioId", "DEMO-CASE-CLAIMS-V1"),
            ("scenarioVersion", "1.0.0"),
        ):
            with self.subTest(field=name):
                proposal = deepcopy(self.manifest)
                proposal[name] = value
                with self.assertRaises(StoreError) as caught:
                    self.store.check_run_context(self.run_id, proposal)
                self.assertEqual(caught.exception.code, "not-authorized")
        proposal = deepcopy(self.manifest)
        proposal["scope"]["scopeId"] = "SCOPE-OTHER"
        with self.assertRaises(StoreError):
            self.store.check_run_context(self.run_id, proposal)
        self.assertEqual(self.store.read_run(self.run_id), self.manifest)

    def test_existing_run_cannot_be_recreated_to_switch_mode(self) -> None:
        proposed = deepcopy(self.manifest)
        proposed["runMode"] = "live"
        with self.assertRaisesRegex(StoreError, "already exists"):
            self.store.create_run(proposed)
        self.assertEqual(self.store.read_run(self.run_id)["runMode"], "fixture")

    def test_early_case_cannot_be_promoted_to_different_hero_run(self) -> None:
        hero = deepcopy(self.manifest)
        hero.update(runId="RUN-NEW-HERO", caseId="CASE-NEW-HERO", runMode="live", purpose="hero")
        self.store.create_run(hero)
        self.store.create_case(hero["runId"])
        with self.assertRaisesRegex(StoreError, "does not match"):
            self.store.commit(hero["runId"], 0, self.case)
        self.assertEqual(self.store.read_case(hero["runId"])["logicalRevision"], 0)

    def test_interrupted_replace_leaves_original_json_and_unrelated_file(self) -> None:
        before = self.case_path.read_bytes()
        unrelated = self.case_path.parent / "operator-notes.txt"
        unrelated.write_bytes(b"keep exactly\r\n")
        with patch("case_store.os.replace", side_effect=OSError("injected-before-replace")):
            with self.assertRaisesRegex(OSError, "injected"):
                self.store.commit(self.run_id, 0, self.case)
        self.assertEqual(self.case_path.read_bytes(), before)
        self.assertEqual(unrelated.read_bytes(), b"keep exactly\r\n")
        self.assertEqual(CaseStore(self.store.root).read_case(self.run_id), self.case)
        self.assertEqual(list(self.case_path.parent.glob("case-*.tmp")), [])

    def test_artifact_is_immutable_and_not_active_until_referenced(self) -> None:
        artifact = {
            "artifactId": "ART-EXAMPLE-REQUIREMENT",
            "runId": self.run_id,
            "caseId": self.manifest["caseId"],
            "scope": deepcopy(self.manifest["scope"]),
            "content": {"origin": "fixture"},
        }
        before = self.case_path.read_bytes()
        reference = self.store.put_artifact(self.run_id, artifact)
        self.assertEqual(reference, self.store.put_artifact(self.run_id, artifact))
        self.assertEqual(self.case_path.read_bytes(), before)
        self.assertEqual(self.store.read_case(self.run_id)["sections"], {})
        proposal = deepcopy(self.case)
        proposal["sections"]["requirements"] = reference
        self.store.commit(self.run_id, 0, proposal)
        self.assertEqual(
            self.store.read_artifact(self.run_id, reference)["content"],
            {"origin": "fixture"},
        )

    def test_missing_referenced_artifact_prevents_commit(self) -> None:
        proposal = deepcopy(self.case)
        proposal["sections"]["requirements"] = {
            "artifactId": "ART-MISSING",
            "checksum": "sha256:" + "a" * 64,
        }
        with self.assertRaises(FileNotFoundError):
            self.store.commit(self.run_id, 0, proposal)
        self.assertEqual(self.store.read_case(self.run_id)["logicalRevision"], 0)

    def test_manual_case_edit_or_duplicate_key_is_not_silently_repaired(self) -> None:
        original = self.case_path.read_bytes()
        changed = deepcopy(self.case)
        changed["lifecycleState"] = "Discovering"
        self.case_path.write_bytes(canonical_bytes(changed))
        with self.assertRaisesRegex(StoreError, "checksum"):
            self.store.read_case(self.run_id)
        duplicate = original.decode().replace(
            '"logicalRevision":0', '"logicalRevision":0,"logicalRevision":1'
        )
        self.case_path.write_text(duplicate, encoding="utf-8")
        with self.assertRaisesRegex(StoreError, "Duplicate"):
            self.store.read_case(self.run_id)
        self.assertEqual(self.case_path.read_text(encoding="utf-8"), duplicate)

    def test_path_traversal_and_invalid_ids_are_rejected(self) -> None:
        for run_id in ("..\\outside", "RUN-A\\..\\outside", "\\\\host\\share", "RUN-A:stream"):
            with self.subTest(run=run_id), self.assertRaises(ValidationError):
                self.store.read_case(run_id)
        self.assertFalse((self.directory / "outside").exists())

    def test_second_process_writer_is_rejected_and_lock_released(self) -> None:
        code = (
            "import sys; from pathlib import Path;"
            f"sys.path.insert(0,{str(STATE_SOURCE)!r});"
            "from case_store import CaseStore,StoreError;"
            f"s=CaseStore(Path({str(self.store.root)!r}));"
            f"s.commit({self.run_id!r},0,s.read_case({self.run_id!r}))"
        )
        with self.store._lock(self.case_path.parent):
            result = subprocess.run(
                [sys.executable, "-B", "-c", code], cwd=ROOT,
                capture_output=True, text=True, timeout=20, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Another writer is active", result.stderr)
        self.store.commit(self.run_id, 0, self.case)
        self.assertEqual(self.store.read_case(self.run_id)["logicalRevision"], 1)

    def test_event_projection_failure_is_visible_and_does_not_undo_case(self) -> None:
        actual_replace = self.store._replace

        def fail_projection(destination: Path, payload: bytes) -> None:
            if destination.name == "events.ndjson":
                raise OSError("injected export failure")
            actual_replace(destination, payload)

        with patch.object(self.store, "_replace", side_effect=fail_projection):
            with self.assertLogs("case_store", level="WARNING") as messages:
                result = self.store.commit(self.run_id, 0, self.case)
            self.assertIn("event-projection-unavailable", messages.output[0])
        self.assertEqual(self.store.read_case(self.run_id)["logicalRevision"], 1)
        self.assertEqual(result["logicalRevision"], 1)
        self.store.rebuild_event_projection(self.run_id)
        self.assertEqual((self.case_path.parent / "events.ndjson").read_bytes(), b"")

    def test_nonfinite_state_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            seal({"bad": float("inf")})

    def test_corrupt_immutable_artifact_cannot_be_silently_overwritten(self) -> None:
        artifact = {
            "artifactId": "ART-IMMUTABLE-EXAMPLE",
            "runId": self.run_id, "caseId": self.manifest["caseId"],
            "scope": deepcopy(self.manifest["scope"]), "value": "fixture",
        }
        reference = self.store.put_artifact(self.run_id, artifact)
        name = reference["checksum"].split(":", 1)[1] + ".json"
        path = self.store.root / self.run_id / "artifacts" / name
        path.write_bytes(b"externally changed bytes")
        with self.assertRaisesRegex(StoreError, "immutable artifact"):
            self.store.put_artifact(self.run_id, artifact)
        self.assertEqual(path.read_bytes(), b"externally changed bytes")

    def test_policy_read_context_preserves_checksum_when_stored(self) -> None:
        policy = Policy(
            self.manifest, scope=self.manifest["scope"],
            root_id=self.manifest["rootId"], config_id=self.manifest["configId"],
            enabled_capabilities=["read-case"],
        )
        browser = policy.human_entry("browser", capabilities=["read-case"])
        result = policy.authorize(
            browser, {"capability": "read-case"}, current_run=self.store.read_run(self.run_id)
        )
        self.assertTrue(result.allowed)
        reference = self.store.put_artifact(self.run_id, result.authorization_context)
        self.assertEqual(reference["checksum"], result.authorization_context["stateChecksum"])
        proposal = deepcopy(self.case)
        proposal["sections"]["authorization-context"] = reference
        self.store.commit(self.run_id, 0, proposal)
        self.assertEqual(
            self.store.read_artifact(self.run_id, reference), result.authorization_context
        )


if __name__ == "__main__":
    unittest.main()
