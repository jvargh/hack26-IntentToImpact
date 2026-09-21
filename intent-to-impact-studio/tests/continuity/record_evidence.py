"""Capture actual local graph tests; synthetic input is never live runtime proof."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    output = ROOT / ".intent-to-impact" / "spikes" / "ENG-04-01" / run_id
    output.mkdir(parents=True, exist_ok=False)
    sources = [
        ROOT / "reporting" / "continuity" / "graph.py",
        ROOT / "tests" / "continuity" / "test_graph.py",
        Path(__file__).resolve(),
        ROOT / "tools" / "contracts" / "validate.py",
        ROOT / "tools" / "contracts" / "integrity.py",
        ROOT / "contracts" / "examples" / "1.0.0" / "risk-examples.json",
        ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json",
        *sorted((ROOT / "contracts" / "schemas" / "1.0.0").glob("*.json")),
    ]

    def hashes():
        return {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sources
        }

    before = hashes()
    command = [
        sys.executable, "-B", "-m", "unittest", "discover", "-s",
        str(ROOT / "tests" / "continuity"), "-p", "test_graph.py", "-v",
    ]
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=120, check=False)
    after = hashes()
    (output / "stdout.txt").write_bytes(result.stdout)
    (output / "stderr.txt").write_bytes(result.stderr)
    match = re.search(r"Ran (\d+) tests", result.stderr.decode("utf-8", errors="replace"))
    count = int(match.group(1)) if match else 0
    passed = result.returncode == 0 and count > 0 and before == after
    receipt = {
        "schemaVersion": "1.0.0", "taskId": "ENG-04-01",
        "status": "passed" if passed else "failed",
        "origin": "live-local", "inputOrigin": "fixture",
        "startedAt": started, "completedAt": datetime.now(timezone.utc).isoformat(),
        "command": command, "exitCode": result.returncode, "testsRun": count,
        "sources": after, "sourceHashesBefore": before,
        "sourcesUnchangedDuringTests": before == after,
        "logs": {
            "stdout.txt": hashlib.sha256(result.stdout).hexdigest(),
            "stderr.txt": hashlib.sha256(result.stderr).hexdigest(),
        },
        "limits": [
            "Pure graph projection, not a new evaluator, provider or authorization source",
            "Fixture verification status never satisfies live runtime proof",
            "No UI rendering or human UX gate approval",
        ],
    }
    path = output / "receipt.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "testsRun": count, "receipt": str(path)}))
    if not passed:
        print(result.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
