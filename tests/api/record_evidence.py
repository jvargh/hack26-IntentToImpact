"""Persist actual local API evidence without credentials or external-provider claims."""

import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))
sys.path.insert(0, str(ROOT / "tests" / "api"))

from api.app import EFFECTS, Service
from test_api import ApiTests
from tools.contracts.integrity import validate_reference_integrity
from tools.contracts.validate import validate_contract


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (EFFECTS / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def archive_previous():
    previous = EFFECTS / "receipt.json"
    if not previous.exists():
        return None
    directory = EFFECTS / "history" / ("before-record-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    directory.mkdir(parents=True)
    for path in [previous, *EFFECTS.glob("sample-*.json")]:
        shutil.copy2(path, directory / path.name)
    archived = directory / previous.name
    return {"path": str(archived.relative_to(EFFECTS)), "sha256": sha(archived)}


def main():
    consumed = [
        ROOT / "contracts" / "schemas" / "1.0.0" / name
        for name in ("core.schema.json", "scenario.schema.json", "risk.schema.json", "projections.schema.json")
    ] + [
        ROOT / "tools" / "contracts" / "validate.py", ROOT / "tools" / "contracts" / "integrity.py",
        ROOT / "apps" / "control-plane" / "state" / "case_store.py",
        ROOT / "apps" / "control-plane" / "policy" / "guard.py",
        ROOT / "apps" / "control-plane" / "policy" / "capabilities.v1.json",
        ROOT / "reporting" / "continuity" / "graph.py",
        ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json",
    ]
    before = {str(p.relative_to(ROOT)): sha(p) for p in consumed}
    previous = archive_previous()
    started = datetime.now(timezone.utc).isoformat()
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s",
               str(ROOT / "tests" / "api"), "-p", "test_api.py", "-v"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if before != {str(p.relative_to(ROOT)): sha(p) for p in consumed}:
        raise RuntimeError("Accepted dependency or registry changed during tests; rerun against the new seam.")
    missing = [name for name in ("create-case", "acknowledge-run-context") if not Service.capability_available(name)]
    count = re.search(r"Ran (\d+) tests", result.stderr)
    skips = re.search(r"skipped=(\d+)", result.stderr)
    tests_run = int(count.group(1)) if count else 0
    tests_skipped = int(skips.group(1)) if skips else 0
    suite_passed = (result.returncode == 0 and tests_skipped == 0
                    and tests_run == len(unittest.defaultTestLoader.getTestCaseNames(ApiTests)))
    passed = suite_passed and not missing
    EFFECTS.mkdir(parents=True, exist_ok=True)
    sample_paths = []

    def sample(name, value):
        write(name, value)
        sample_paths.append(EFFECTS / name)

    if passed:
        example = ApiTests("test_create_persists_case_and_idempotent_event_receipt")
        try:
            example.setUp()
            created = example.client.post("/cases", json=example.create_body(key="completion-evidence"),
                                          headers=example.headers)
            if created.status_code != 201:
                raise RuntimeError("Actual sample case creation failed.")
            validate_contract(created.json(), "E04")
            create_replay = example.client.post("/cases", json=example.create_body(key="completion-evidence"),
                                                headers=example.headers)
            if create_replay.status_code != 200 or create_replay.json() != created.json():
                raise RuntimeError("Actual sample creation replay did not return the same event.")
            run = example.service.store.read_run(created.json()["runId"])
            created_case = example.service.store.read_case(run["runId"])
            experience_path = f"/cases/{run['caseId']}/experience"
            initial = example.client.get(experience_path)
            if initial.status_code != 200:
                raise RuntimeError("Actual sample initial projection failed.")
            action_id = initial.json()["allowedActions"][0]["actionId"]
            ack_input = example.ack_body(case=created_case, run=run, key="completion-evidence-ack")
            action_path = f"/cases/{run['caseId']}/actions/{action_id}"
            acknowledged = example.client.post(action_path, json=ack_input, headers=example.headers)
            if acknowledged.status_code != 200:
                raise RuntimeError("Actual sample context acknowledgement failed.")
            validate_contract(acknowledged.json(), "E04")
            ack_replay = example.client.post(action_path, json=ack_input, headers=example.headers)
            if ack_replay.status_code != 200 or ack_replay.json() != acknowledged.json():
                raise RuntimeError("Actual sample acknowledgement replay did not return the same event.")
            current_case = example.service.store.read_case(run["runId"])
            overview = example.client.get(experience_path)
            error = example.client.get("/cases/invalid/experience")
            if (overview.status_code != 200 or error.status_code != 404
                    or current_case["logicalRevision"] != created_case["logicalRevision"] + 1
                    or current_case["lifecycleState"] != "Draft"
                    or any(row["confirmed"] or row["status"] != "unknown" for row in overview.json()["coverage"]["rows"])):
                raise RuntimeError("Actual sample context-only state/projection invariants failed.")
            validate_reference_integrity(
                [current_case, *current_case["events"], overview.json()],
                {run["runId"]: run}, example.service.scenario,
            )
            sample("sample-create.json", created.json())
            sample("sample-created-case.json", created_case)
            sample("sample-initial-experience.json", initial.json())
            sample("sample-acknowledgement.json", acknowledged.json())
            sample("sample-experience.json", overview.json())
            sample("sample-error.json", error.json())
            sample("sample-case.json", current_case)
            sample("sample-run.json", run)
            sample("sample-origin.json", {
                "origin": "live-local", "scenarioInputOrigin": "fixture",
                "scenarioId": "DEMO-CASE-CLAIMS-V2", "scenarioVersion": "2.0.0",
                "historicalScenario": True, "nspOrV3Proof": False,
                "caseSetup": "Actual POST /cases through real policy and CaseStore.",
                "apiCreateProof": True, "apiContextAcknowledgementProof": True,
                "createStatus": created.status_code, "createReplayStatus": create_replay.status_code,
                "acknowledgementStatus": acknowledged.status_code, "acknowledgementReplayStatus": ack_replay.status_code,
                "httpReadStatus": overview.status_code, "errorStatus": error.status_code,
                "credentialsOmitted": True, "promisesConfirmed": False,
            })
        finally:
            example.doCleanups()
    sources = {}
    for folder in (ROOT / "apps" / "control-plane" / "api", ROOT / "tests" / "api"):
        for path in folder.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                sources[str(path.relative_to(ROOT))] = sha(path)
    receipt = {
        "version": "1.0.0", "task": "INT-01-01", "parentPlan": "INT-01",
        "status": "passed" if passed else ("partial" if suite_passed else "failed"),
        "taskComplete": passed,
        "origin": "live-local", "inputsOrigin": "fixture", "startedAt": started,
        "completedAt": datetime.now(timezone.utc).isoformat(), "command": command,
        "exitCode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
        "testsRun": tests_run, "testsSkipped": tests_skipped,
        "missingCapabilities": missing,
        "previousReceipt": previous,
        "nextSafeAction": (
            "Independent acceptance of this bounded historical V2 API seam only; no NSP/V3, provider or UI authority."
            if passed else
            "Review failing/skipped tests or restore the authoritative owner registry seam; no substitute permissions."
        ),
        "versions": {p: importlib.metadata.version(p) for p in ("fastapi", "starlette", "uvicorn", "httpx", "pydantic", "jsonschema")},
        "sourceFileHashes": sources, "consumedSourceHashes": before,
        "responseFileHashes": {p.name: sha(p) for p in sample_paths},
        "proofRows": [
            {"proof": "actual-loopback-listener-and-exact-child-stop", "status": "passed" if suite_passed else "failed"},
            {"proof": "real-store-unknown-P01-and-reference-integrity", "status": "passed" if passed else "failed"},
            {"proof": "shared-CP01-graph-explicit-binding-evaluation-gaps", "status": "passed" if suite_passed else "failed"},
            {"proof": "strict-session-csrf-origin-host-and-artifact-boundary", "status": "passed" if suite_passed else "failed"},
            {"proof": "guarded-create-case", "status": "blocked" if "create-case" in missing else ("passed" if passed else "failed")},
            {"proof": "guarded-context-only-acknowledgement", "status": "blocked" if "acknowledge-run-context" in missing else ("passed" if passed else "failed")},
            {"proof": "missing-malformed-unavailable-registry-no-writes", "status": "passed" if suite_passed else "failed"},
        ],
        "azureCalls": 0, "modelCalls": 0, "sharedRegistryOrSchemaEdits": 0,
        "serverLeftRunning": False, "noUxGateApproved": True,
        "limitations": [
            "Local demo session is not production auth or OS-owner resistance.",
            "Historical V2 scenario inputs are fixture; P01 is generated from actual local state, not a fixture response.",
            "No business requirements/approval or runtime verification is implemented.",
            "No LOCAL-09 NSP/V3 proof, cloud migration or human UX gate approval is claimed.",
        ],
    }
    write("receipt.json", receipt)
    for name, digest in {**before, **sources}.items():
        if sha(ROOT / name) != digest:
            raise RuntimeError("Source/evidence dependency changed.")
    print(json.dumps({"status": receipt["status"], "taskComplete": receipt["taskComplete"],
                      "testsRun": receipt["testsRun"], "testsSkipped": receipt["testsSkipped"],
                      "missingCapabilities": missing, "receipt": str((EFFECTS / "receipt.json").relative_to(ROOT))}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
