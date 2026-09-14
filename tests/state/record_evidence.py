"""Capture bounded local case-store test results without touching a product run."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid


def main() -> int:
    workspace = Path(__file__).resolve().parents[2]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    evidence = workspace / ".intent-to-impact" / "spikes" / "FND-02-01" / run_id
    evidence.mkdir(parents=True, exist_ok=False)
    command = [
        sys.executable, "-B", "-m", "unittest", "discover", "-s",
        str(workspace / "tests" / "state"), "-p", "test_case_store.py", "-v",
    ]
    sources = [
        workspace / "apps" / "control-plane" / "state" / "case_store.py",
        workspace / "tests" / "state" / "test_case_store.py",
        Path(__file__).resolve(),
        workspace / "contracts" / "schemas" / "1.0.0" / "core.schema.json",
        workspace / "tools" / "contracts" / "validate.py",
        workspace / "apps" / "control-plane" / "policy" / "guard.py",
        workspace / "apps" / "control-plane" / "policy" / "capabilities.v1.json",
    ]
    before = {
        str(source.relative_to(workspace)): hashlib.sha256(source.read_bytes()).hexdigest()
        for source in sources
    }
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(command, cwd=workspace, capture_output=True, timeout=90, check=False)
    (evidence / "stdout.txt").write_bytes(result.stdout)
    (evidence / "stderr.txt").write_bytes(result.stderr)
    output = result.stderr.decode("utf-8", errors="replace")
    match = re.search(r"Ran (\d+) tests", output)
    count = int(match.group(1)) if match else 0
    after = {
        str(source.relative_to(workspace)): hashlib.sha256(source.read_bytes()).hexdigest()
        for source in sources
    }
    passed = result.returncode == 0 and count > 0 and before == after
    receipt = {
        "schemaVersion": "1.0.0", "taskId": "FND-02-01",
        "status": "passed" if passed else "failed",
        "evidenceOrigin": "live-local", "testInputOrigin": "fixture",
        "command": command, "startedAt": started,
        "completedAt": datetime.now(timezone.utc).isoformat(),
        "exitCode": result.returncode, "testsRun": count,
        "reviewStatus": "test-verified", "azureEffects": "none",
        "sources": after,
        "sourceHashesBefore": before,
        "sourcesUnchangedDuringTests": before == after,
        "logs": {
            "stdout.txt": hashlib.sha256(result.stdout).hexdigest(),
            "stderr.txt": hashlib.sha256(result.stderr).hexdigest(),
        },
        "limits": [
            "Storage primitive only, not an implemented HTTP or authorization boundary",
            "No live Azure, product approval or completed M1/M0.5 claim",
            "No power-loss or hostile-OS-user assurance",
        ],
    }
    path = evidence / "receipt.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "testsRun": count, "receipt": str(path)}))
    if not passed:
        print(output, file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
