"""Record bounded live-local policy tests; fixture inputs are not cloud proof."""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".intent-to-impact" / "spikes" / "FND-03-01"
CORE = ROOT / "contracts" / "schemas" / "1.0.0" / "core.schema.json"
EXPECTED_CORE = "2188cefbe3f156776238c029899a35502d8435081639d6deab92e6fdffa39c01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    before = sha(CORE)
    if before != EXPECTED_CORE:
        raise RuntimeError("Frozen core hash changed; review the new contract before recording proof.")
    started = now()
    command = [
        sys.executable, "-B", "-m", "unittest", "discover", "-s",
        str(ROOT / "tests" / "policy"), "-p", "test_policy.py", "-v",
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if sha(CORE) != before:
        raise RuntimeError("Core changed during validation; evidence not promoted.")
    roots = [ROOT / "apps" / "control-plane" / "policy", ROOT / "tests" / "policy"]
    hashes = {str(p.relative_to(ROOT)): sha(p) for folder in roots
              for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    receipt = {
        "version": "1.0.0", "task": "FND-03-01", "parentPlan": "FND-03",
        "status": "passed" if result.returncode == 0 else "failed",
        "origin": "live-local", "inputsOrigin": "fixture", "startedAt": started,
        "completedAt": now(), "command": command, "exitCode": result.returncode,
        "stdout": result.stdout, "stderr": result.stderr,
        "pythonVersion": platform.python_version(),
        "jsonschemaVersion": importlib.metadata.version("jsonschema"),
        "consumedCore": {"version": "1.0.0", "path": str(CORE.relative_to(ROOT)), "sha256": before},
        "validator": {"path": "tools\\contracts\\validate.py",
                      "sha256": sha(ROOT / "tools" / "contracts" / "validate.py")},
        "sourceFileHashes": hashes,
        "externalRequests": 0, "azureMutations": 0, "schemaMutations": 0,
        "limitations": [
            "Trusted adapter/engine producers are assumed; no hostile OS/Python-owner protection.",
            "ApprovalBinding is a noncanonical projection, not D07/D08 schema or approval creation.",
            "Policy success never materializes/deploys/seeds/resets/claims runtime verification.",
            "State owner must recheck revision/approval/checksums under its commit lock.",
            "Fixture test inputs are not canonical live cases; no UX gate approval.",
        ],
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "receipt.json"
    if path.exists():
        history = OUTPUT / "history"
        history.mkdir(exist_ok=True)
        (history / f"receipt-{uuid4().hex}.json").write_bytes(path.read_bytes())
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    for name, expected in hashes.items():
        if sha(ROOT / name) != expected:
            raise RuntimeError("Source changed during evidence write.")
    print(json.dumps({"status": receipt["status"], "receipt": str(path.relative_to(ROOT)),
                      "sourceHashCount": len(hashes), "coreSha256": before}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
