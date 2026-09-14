"""Run SPK-02-01 and preserve genuine local test evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid


def main() -> int:
    source_root = Path(__file__).resolve().parent
    workspace = source_root.parents[2]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    evidence = workspace / ".intent-to-impact" / "spikes" / "SPK-02-01" / run_id
    evidence.mkdir(parents=True, exist_ok=False)
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(source_root),
        "-p",
        "test_*.py",
        "-v",
    ]
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    result = subprocess.run(command, capture_output=True, timeout=60, check=False)
    completed = datetime.now(timezone.utc).isoformat()
    (evidence / "stdout.txt").write_bytes(result.stdout)
    (evidence / "stderr.txt").write_bytes(result.stderr)
    report = result.stderr.decode("utf-8", errors="replace")
    count = re.search(r"Ran (\d+) tests", report)
    test_count = int(count.group(1)) if count else 0
    passed = result.returncode == 0 and test_count > 0
    receipt = {
        "schemaVersion": "1.0.0",
        "artifactType": "spike-test-receipt",
        "taskId": "SPK-02-01",
        "origin": "live-local",
        "runPurpose": "bounded-file-safety-spike",
        "productionStoreProof": False,
        "azureEffects": "none",
        "command": command,
        "startedAt": started,
        "completedAt": completed,
        "elapsedSeconds": round(time.monotonic() - clock, 4),
        "exitCode": result.returncode,
        "testsRun": test_count,
        "status": "passed" if passed else "failed",
        "pythonVersion": sys.version,
        "sources": {
            source.name: hashlib.sha256(source.read_bytes()).hexdigest()
            for source in sorted(source_root.glob("*.py"))
        },
        "evidence": {
            "stdout.txt": hashlib.sha256(result.stdout).hexdigest(),
            "stderr.txt": hashlib.sha256(result.stderr).hexdigest(),
        },
        "limitations": [
            "Windows local-filesystem spike, not a production persistence engine",
            "No power-loss, distributed writer, arbitrary-root or Azure verification claim",
            "Failure-path temporary directories were owned by unittest and cleaned up",
        ],
    }
    (evidence / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": receipt["status"], "testsRun": test_count, "receipt": str(evidence / "receipt.json")}))
    if not passed:
        print(report, file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
