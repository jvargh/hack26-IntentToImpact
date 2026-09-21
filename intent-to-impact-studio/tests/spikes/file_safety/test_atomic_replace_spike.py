from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from atomic_replace_spike import (
    RevisionConflictError,
    initialize,
    read_case,
    replace_case,
    writer_lock,
)


SCRIPT = Path(__file__).with_name("atomic_replace_spike.py")


class FileSafetySpikeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="intent-to-impact-spk02-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        initialize(self.root)
        replace_case(self.root, None, {"logicalRevision": 1, "status": "original"})

    def child(self, operation: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), operation, str(self.root)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def test_replacement_survives_new_process_and_preserves_unrelated_file(self) -> None:
        unrelated = self.root / "operator-notes.txt"
        original_bytes = b"operator-owned content must remain unchanged\r\n"
        unrelated.write_bytes(original_bytes)
        replace_case(self.root, 1, {"logicalRevision": 2, "status": "committed"})
        result = self.child("read")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "committed")
        self.assertEqual(unrelated.read_bytes(), original_bytes)
        self.assertEqual(list(self.root.glob("case-*.tmp")), [])

    def test_stale_revision_preserves_prior_bytes(self) -> None:
        previous = (self.root / "case.json").read_bytes()
        with self.assertRaisesRegex(RevisionConflictError, "found 1"):
            replace_case(self.root, 2, {"logicalRevision": 3, "status": "overwrite"})
        self.assertEqual((self.root / "case.json").read_bytes(), previous)

    def test_invalid_next_revision_preserves_prior_bytes(self) -> None:
        previous = (self.root / "case.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "Next logical revision"):
            replace_case(self.root, 1, {"logicalRevision": True})
        self.assertEqual((self.root / "case.json").read_bytes(), previous)

    def test_nonfinite_json_is_rejected_before_any_replacement(self) -> None:
        previous = (self.root / "case.json").read_bytes()
        with self.assertRaises(ValueError):
            replace_case(self.root, 1, {"logicalRevision": 2, "value": float("nan")})
        self.assertEqual((self.root / "case.json").read_bytes(), previous)

    def test_second_process_is_rejected_while_lock_is_owned(self) -> None:
        with writer_lock(self.root):
            result = self.child("lock")
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertIn("writer-busy:", result.stderr)
        released = self.child("lock")
        self.assertEqual(released.returncode, 0, released.stderr)
        self.assertEqual(released.stdout.strip(), "LOCKED")

    def test_interrupted_write_preserves_case_and_releases_process_lock(self) -> None:
        previous = (self.root / "case.json").read_bytes()
        result = self.child("interrupt-before-replace")
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual((self.root / "case.json").read_bytes(), previous)
        orphans = list(self.root.glob("case-*.tmp"))
        self.assertEqual(len(orphans), 1)
        self.assertEqual(
            json.loads(orphans[0].read_text(encoding="utf-8"))["status"], "interrupted"
        )
        self.assertEqual(self.child("read").returncode, 0)
        replace_case(self.root, 1, {"logicalRevision": 2, "status": "restarted"})
        self.assertEqual(read_case(self.root)["status"], "restarted")
        self.assertTrue(orphans[0].exists(), "Spike must not silently promote/delete orphans")

    def test_unreferenced_artifact_does_not_change_authoritative_case(self) -> None:
        previous = (self.root / "case.json").read_bytes()
        candidate = self.root / "unreferenced-candidate"
        candidate.mkdir()
        (candidate / "main.bicep").write_text("targetScope = 'resourceGroup'\n")
        result = self.child("read")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"logicalRevision": 1, "status": "original"})
        self.assertEqual((self.root / "case.json").read_bytes(), previous)

    def test_unmarked_directory_is_rejected(self) -> None:
        unmarked = self.root / "unmarked"
        unmarked.mkdir()
        with self.assertRaises(FileNotFoundError):
            replace_case(unmarked, None, {"logicalRevision": 1})
        self.assertEqual(list(unmarked.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
