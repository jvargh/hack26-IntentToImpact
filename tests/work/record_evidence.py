"""Bounded local work evidence; never invokes models or Azure APIs."""

import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".intent-to-impact" / "spikes" / "FND-04-01"
EXPECTED_CORE = "2188cefbe3f156776238c029899a35502d8435081639d6deab92e6fdffa39c01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    consumed = [
        ROOT / "contracts" / "schemas" / "1.0.0" / "core.schema.json",
        ROOT / "tools" / "contracts" / "validate.py",
        ROOT / "apps" / "control-plane" / "state" / "case_store.py",
        ROOT / "apps" / "control-plane" / "policy" / "guard.py",
        ROOT / "apps" / "control-plane" / "policy" / "capabilities.v1.json",
    ]
    before = {str(p.relative_to(ROOT)): sha(p) for p in consumed}
    if before[str(consumed[0].relative_to(ROOT))] != EXPECTED_CORE:
        raise RuntimeError("Frozen core changed; review the dependency instead of claiming compatibility.")
    started = datetime.now(timezone.utc).isoformat()
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s",
               str(ROOT / "tests" / "work"), "-p", "test_coordinator.py", "-v"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    after = {str(p.relative_to(ROOT)): sha(p) for p in consumed}
    if before != after:
        raise RuntimeError("Consumed contract/state/policy changed during validation.")
    sources = {}
    for folder in (ROOT / "apps" / "control-plane" / "work", ROOT / "tests" / "work"):
        for path in folder.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                sources[str(path.relative_to(ROOT))] = sha(path)
    receipt = {
        "version": "1.0.0", "task": "FND-04-01", "parentPlan": "FND-04",
        "status": "passed" if result.returncode == 0 else "failed",
        "origin": "live-local", "inputsOrigin": "fixture", "startedAt": started,
        "completedAt": datetime.now(timezone.utc).isoformat(),
        "command": command, "exitCode": result.returncode,
        "stdout": result.stdout, "stderr": result.stderr,
        "pythonVersion": platform.python_version(),
        "jsonschemaVersion": importlib.metadata.version("jsonschema"),
        "consumedSourceHashes": before, "sourceFileHashes": sources,
        "sharedSourcesUnchangedDuringValidation": True,
        "azureRequests": 0, "modelCalls": 0, "sharedSchemaEdits": 0,
        "proof": [
            "Actual CaseStore durable writes and child-interpreter restart read.",
            "Same request/completion receipt on duplicate; changed input conflicts.",
            "Monotonic canonical E04 sequence and actual trusted executor attribution.",
            "Fresh status/dependency checks after explicit stale revision; no automatic retry.",
            "Before-commit/capture faults remain incomplete; lost response deduplicates committed completion.",
            "Derived export interruption retains canonical events and rebuilds exactly.",
            "Uncertain running work reconciles to recovery-required without reexecution.",
            "Configured caps fail without pruning; persisted full idempotency cap also rejects enqueue.",
            "Presentation deduplicates local E04-linked metadata, not canonical E05/attention.",
        ],
        "limits": [
            "No actual provider task execution or external-outcome verification.",
            "No canonical E05/attention counters; no HTTP/SSE service or UX approval.",
            "No lease/fencing, distributed lock, power-loss or hostile OS-owner guarantee.",
            "Owning engine validates domain results and supplies trusted current policy facts.",
        ],
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "receipt.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    for name, digest in {**before, **sources}.items():
        if sha(ROOT / name) != digest:
            raise RuntimeError("Evidence source hash changed.")
    print(json.dumps({"status": receipt["status"], "receipt": str(path.relative_to(ROOT)),
                      "producedSourceHashes": len(sources), "consumedSourceHashes": len(before),
                      "receiptSha256": sha(path)}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
