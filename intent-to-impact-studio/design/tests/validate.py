"""Run one independent design suite and persist its own local evidence receipt."""

import argparse
import hashlib
import io
import json
import platform
import sys
import unittest
from datetime import datetime, timezone
from importlib.metadata import version

from validation import ROOT

TASK_FILES = {
    "UX-01-01": [
        r"design\journey\hero-journey.v1.json",
        r"design\information-architecture\inventory.v1.json",
        r"design\journey\README.md",
        r"design\tests\test_ux_01_01.py",
    ],
    "UX-03-01": [
        r"design\reviews\ux-record.schema.json",
        r"design\reviews\checkpoint-agendas.v1.json",
        r"design\reviews\README.md",
        r"design\decisions\UXD-001.json",
        r"design\decisions\UXD-002.json",
        r"design\tests\test_ux_03_01.py",
    ],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=TASK_FILES, required=True)
    parser.add_argument("--receipt-only", action="store_true",
                        help="Embed current test output in the receipt; leave existing log files unchanged.")
    args = parser.parse_args()
    task = args.task
    command = fr"python -B design\tests\validate.py --task {task}"
    if args.receipt_only:
        command += " --receipt-only"
    started = datetime.now(timezone.utc).isoformat()
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "design" / "tests"),
        pattern=f"test_{task.lower().replace('-', '_')}.py",
    )
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    text = output.getvalue()
    sys.stdout.write(text)
    success = result.wasSuccessful() and result.testsRun > 0
    destination = ROOT / ".intent-to-impact" / "spikes" / task
    destination.mkdir(parents=True, exist_ok=True)
    log = destination / "test-results.txt"
    if not args.receipt_only:
        log.write_text(text, encoding="utf-8")
    files = TASK_FILES[task] + [r"design\tests\validation.py", r"design\tests\validate.py"]
    receipt = {
        "schemaVersion": "1.0.0",
        "taskId": task,
        "parentPlanId": "UX-01" if task == "UX-01-01" else "UX-03",
        "deliveryClass": "P0-HERO" if task == "UX-01-01" else "P0-SUPPORT",
        "scenarioId": "DEMO-CASE-CLAIMS-V1",
        "scenarioVersion": "1.0.0",
        "owner": "D-ux",
        "reviewer": "implementation-orchestrator",
        "status": "draft-implemented-locally-validated" if success else "validation-failed",
        "humanAcceptance": "pending",
        "command": command,
        "workingDirectory": str(ROOT),
        "startedAt": started,
        "completedAt": datetime.now(timezone.utc).isoformat(),
        "exitCode": 0 if success else 1,
        "testsRun": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "validationEvidenceOrigin": "live-local",
        "designEvidenceOrigin": "ux-mock",
        "environment": {"python": platform.python_version(),
                        "jsonschema": version("jsonschema") if task == "UX-03-01" else "not-used"},
        "testLog": None if args.receipt_only else str(log.relative_to(ROOT)),
        "testLogSha256": None if args.receipt_only else hashlib.sha256(log.read_bytes()).hexdigest(),
        "inlineTestOutput": text if args.receipt_only else None,
        "artifacts": [{"path": file, "sha256": hashlib.sha256((ROOT / file).read_bytes()).hexdigest()}
                      for file in files],
        "unresolvedHumanDecisions": [
            {"id": "UXD-001", "status": "illustrative-pending-review",
             "question": "Human confirmation of CP-01 wording, editorial hierarchy and one dominant risk action has not occurred."},
        ],
        "unresolvedTechnicalReviews": [
            {"id": "UXD-002", "status": "pending-review",
             "question": "A/C/D must bind expected projection fields, scenario hash and correction variants to accepted contracts."},
        ],
        "acceptanceBoundary": {
            "structuralValidationOnly": True,
            "humanAuthenticityEstablished": False,
            "reviewEvidenceAuthenticityEstablished": False,
            "requiredExternalReview": "Implementation-orchestrator checks actual technical reviewer attribution/evidence and genuine demo-human product acceptance; field strings do not authenticate either.",
        },
        "pendingGates": [f"GATE-UX{n:02}" for n in range(1, 7)],
        "limits": [
            "No human approval, accepted downstream dependency, browser test or production semantic alignment.",
            "No canonical D/P schema, U01 response fixture, token or UI component implemented.",
            "No Azure/model execution, deployment, live runtime verification or live hero proof.",
            "Negative tests mutate in-memory copies only; they do not persist fabricated approvals.",
        ],
    }
    receipt_path = destination / "evidence-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"{task}: {receipt['status']}; {result.testsRun} tests; {receipt_path.relative_to(ROOT)}")
    return receipt["exitCode"]


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
