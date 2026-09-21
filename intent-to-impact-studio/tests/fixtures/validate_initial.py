"""Validate authored U01 fixtures with the actual frozen contract/integrity helpers."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fixtures.experience.build_initial import (
    FIXTURE_REVISION, HISTORICAL, OUTPUT, SCENARIO_PATH, SCENARIO_HASH, SCENES, build, byte_hash, read, walk,
)
from tools.contracts.integrity import scenario_identity, validate_reference_integrity, validate_scenario
from tools.contracts.validate import identify_contract, validate_contract, fragment_validator

EXPECTED = {
    "FX-01": ("unknown", "not-requested", "unknown"),
    "FX-09": ("known-risk", "not-requested", "breached"),
    "FX-10": ("restoration-pending", "prepared", "breached"),
    "FX-11": ("restoration-pending", "verification-pending", "breached"),
    "FX-12": ("no-known-risk", "verified", "verified"),
    "FX-11:missing-evidence": ("unknown", "verification-pending", "unknown"),
    "FX-09:stale-evidence": ("unknown", "not-requested", "stale"),
}


class FixtureValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise FixtureValidationError(message)


def fixture_path(relative):
    path = (OUTPUT / relative).resolve()
    require(path.is_relative_to(OUTPUT.resolve()), "fixture path escapes owned bundle")
    return path


def scene_data(scene):
    return read(fixture_path(scene["response"])), read(fixture_path(scene["records"]))


def validate_scene(response, bundle, run, scene_id):
    require(run["runMode"] == "fixture" and run["purpose"] == "ux-mock", "trusted run must stay fixture/ux-mock")
    documents = [response] + bundle["records"]
    for document in documents:
        for item in walk(document):
            if "runMode" in item:
                require(item["runMode"] == "fixture" and item.get("purpose") == "ux-mock", "record mode/purpose must stay mock")
            if "origin" in item:
                require(item["origin"] == "fixture", "fixture cannot claim live origin")
            if "scenarioOrigin" in item:
                require(item["scenarioOrigin"] == "fixture", "projection origin must be fixture")
            if item.get("artifactType") == "evidence-reference":
                require(item["eligibility"] == "ineligible", "fixture evidence cannot be live-proof eligible")
            if item.get("artifactType") == "sandbox-operation-receipt":
                require((item["providerOperationId"] or "").startswith("fixture-"),
                        "fixture cannot claim an actual provider operation")
                require("FIXTURE" in (item["operatorConsentId"] or ""), "operation consent must be explicitly synthetic")
        require(document["scope"] == run["scope"] and run["scope"]["subscriptionId"] == "00000000-0000-0000-0000-000000000000",
                "fixture scope must remain synthetic, not a real Azure target")
    scenario = read(SCENARIO_PATH)
    require(scenario["stateChecksum"] == SCENARIO_HASH, "old or unexpected scenario")
    validate_reference_integrity(documents, {run["runId"]: run}, scenario, bundle["externalReferences"])
    validate_contract(response, "P01")
    validate_contract(response["operationsRisk"], "P05")
    validate_contract(response["continuityGraph"], "P06")
    by_id = {d["artifactId"]: d for d in documents}
    operations = response["operationsRisk"]
    evaluation = by_id[operations["evaluationRefs"][0]["artifact"]["artifactId"]]
    require((operations["riskState"], operations["restoration"]["status"], evaluation["status"]) == EXPECTED[scene_id],
            "authored scene status changed or premature restoration")
    require(operations["allowedActions"] == response["allowedActions"], "standalone P05 and P01 actions differ")
    require(response["continuityGraph"]["allowedActions"] == [], "graph is read-only; no workflow actions")
    coverage = response["coverage"]
    require(coverage["verifiedCount"] is None and coverage["applicableCount"] is None, "unassessed counts must remain null")
    require({r["promiseId"] for r in coverage["rows"]} == {f"CP-{n:02}" for n in range(1, 9)},
            "all eight coverage rows required")
    require(all(r["status"] == "unknown" and r["evaluation"] is None for r in coverage["rows"] if r["promiseId"] != "CP-01"),
            "unsupported promises cannot be verified")
    require(next(r for r in coverage["rows"] if r["promiseId"] == "CP-05")["confirmed"] is False,
            "RPO must not be automatically confirmed")
    promises = next(d for d in documents if d["artifactType"] == "customer-promise-contract")
    require({r["promiseId"] for r in coverage["rows"] if r["confirmed"]} == set(promises["confirmedPromiseIds"]),
            "coverage confirmations disagree with loaded fixture D03")
    if scene_id == "FX-01":
        require(promises["status"] == "draft" and promises["confirmedPromiseIds"] == []
                and promises["confirmationDecisionId"] is None, "initial overview must remain unconfirmed")
    else:
        require("FIXTURE" in (promises["confirmationDecisionId"] or ""), "scripted confirmation must never claim live authority")
    if scene_id == "FX-12":
        require(operations["restoration"]["verificationEvaluation"] in operations["evaluationRefs"],
                "verified restoration needs the displayed fixture evaluation")
        require(len(evaluation["predicateResults"]) == 4
                and all(p["result"] == "pass" and p["evidence"] for p in evaluation["predicateResults"])
                and bool(evaluation["evidence"]), "verified example requires four evidence-backed fixture predicates")
        snapshot = by_id[evaluation["runtimeSnapshot"]["artifact"]["artifactId"]]
        require(snapshot["observations"][0]["properties"] == scenario["desiredStorageConfiguration"],
                "restoration example must show the exact authored V2 configuration")
        for ref in evaluation["evidence"]:
            record = by_id[ref["reference"]["artifact"]["artifactId"]]
            require(record["evidenceState"] == "fresh", "verified example cannot use stale fixture evidence")
    for action in response["allowedActions"]:
        fragment_validator("core", "ActionId").validate(action["actionId"])
        require(action["capability"] == "read-case", "initial actions may only inspect authored fixtures")
    return Counter(identify_contract(d) for d in documents)


def validate_action_map(action_map, scene_entries, responses):
    require(action_map["transport"] == {
        "kind": "in-memory-fixture", "networkAccess": False, "liveEndpoints": [],
        "immutableRunMode": True, "executesWorkflow": False,
    }, "fixture transport must not call live endpoints or execute workflow")
    expected = {(scene_id, action["actionId"]) for scene_id, response in responses.items()
                for action in response["allowedActions"]}
    seen = set()
    for transition in action_map["transitions"]:
        require(set(transition) == {"fromSceneId", "actionId", "toSceneId", "effect", "executesWorkflow"},
                "transition may contain no executable command or endpoint")
        key = transition["fromSceneId"], transition["actionId"]
        require(key in expected and key not in seen, "transition must use the exact issued lowercase action")
        require(transition["toSceneId"] in responses, "dangling scene transition")
        require(transition["effect"] in {"load-authored-snapshot", "inspect-records"}
                and transition["executesWorkflow"] is False, "canned navigation cannot perform operations")
        seen.add(key)
    require(seen == expected, "all issued actions need one canned response")
    for entry in scene_entries:
        require(entry["primaryActionId"] in {a["actionId"] for a in responses[entry["sceneId"]]["allowedActions"]},
                "one primary action must reference an issued action")


def validate_catalog(manifest=None):
    manifest = manifest if manifest is not None else read(OUTPUT / "manifest.json")
    require(manifest["taskId"] == "MOCK-01-01" and manifest["schemaVersion"] == "1.0.0", "fixture task/version mismatch")
    require(manifest["fixtureRevision"] == FIXTURE_REVISION, "fixture revision mismatch")
    history = manifest["supersedes"]
    require((ROOT / history["root"]).resolve() == HISTORICAL.resolve(), "historical bundle mismatch")
    historical_paths = set()
    for source in history["files"]:
        path = (ROOT / source["path"]).resolve()
        require(path.is_relative_to(HISTORICAL.resolve()), "historical path escapes bundle")
        require(path not in historical_paths, "duplicate historical file")
        historical_paths.add(path)
        require(byte_hash(path.read_bytes()) == source["sha256"], "historical fixture bytes changed")
    require(historical_paths == {path.resolve() for path in HISTORICAL.rglob("*.json")},
            "historical fixture inventory changed")
    require(manifest["runMode"] == "fixture" and manifest["purpose"] == "ux-mock"
            and manifest["origin"] == "fixture" and manifest["evidenceOrigin"] == "ux-mock"
            and manifest["liveProofEligible"] is False, "manifest must be mock-only")
    require(manifest["fullFxCatalogComplete"] is False and manifest["humanGate"] == "GATE-UX01-pending",
            "no full catalog or human acceptance claimed")
    scenario = read(SCENARIO_PATH)
    validate_scenario(scenario)
    require(manifest["scenario"] == scenario_identity(scenario) and scenario["stateChecksum"] == SCENARIO_HASH,
            "manifest must use exact canonical V2 scenario")
    for source in manifest["inputFiles"]:
        path = (ROOT / source["path"]).resolve()
        require(path.is_relative_to(ROOT), "source path escapes workspace")
        require(byte_hash(path.read_bytes()) == source["sha256"], "consumed schema/design input drift")
    for field in ("runManifest", "actionMap"):
        require(byte_hash(fixture_path(manifest[field]).read_bytes()) == manifest[field + "Sha256"],
                f"{field} file hash mismatch")
    run, actions = read(fixture_path(manifest["runManifest"])), read(fixture_path(manifest["actionMap"]))
    require(actions["scenario"] == manifest["scenario"], "action map scenario mismatch")
    entries = manifest["scenes"]
    require(len(entries) == len(EXPECTED) and {e["sceneId"] for e in entries} == set(EXPECTED),
            "exact initial scene set required; not full FX catalog")
    responses, counts = {}, Counter()
    for entry in entries:
        for field in ("response", "records"):
            require(byte_hash(fixture_path(entry[field]).read_bytes()) == entry[field + "Sha256"],
                    f"fixture file hash mismatch: {entry['sceneId']} {field}")
        response, records = scene_data(entry)
        require(entry["origin"] == "fixture" and entry["recordCount"] == len(records["records"]), "scene origin/count mismatch")
        counts.update(validate_scene(response, records, run, entry["sceneId"]))
        responses[entry["sceneId"]] = response
    validate_action_map(actions, entries, responses)
    return {"scenes": len(responses), "projectionRoots": sum(counts[k] for k in ("P01", "P05", "P06")),
            "loadedDocumentRoots": sum(counts.values()), "contracts": dict(sorted(counts.items())),
            "fullFxCatalogComplete": False, "liveProofEligible": False}


def main():
    started = datetime.now(timezone.utc).isoformat()
    output = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests" / "fixtures"), pattern="test_initial_v2.py")
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    text = output.getvalue()
    sys.stdout.write(text)
    success = result.wasSuccessful() and result.testsRun > 0
    summary = validate_catalog() if success else None
    attempt = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    destination = ROOT / ".intent-to-impact" / "spikes" / "MOCK-01-01" / f"R{FIXTURE_REVISION}" / attempt
    destination.mkdir(parents=True, exist_ok=False)
    log = destination / "test-results.txt"
    log.write_text(text, encoding="utf-8")
    files = sorted(OUTPUT.rglob("*.json")) + [
        ROOT / "fixtures" / "experience" / "build_initial.py",
        ROOT / "fixtures" / "experience" / "README.md",
        Path(__file__), ROOT / "tests" / "fixtures" / "test_initial_v2.py",
        ROOT / "contracts" / "registry" / "1.0.0.json",
        *[ROOT / "tools" / "contracts" / name
          for name in ("integrity.py", "validate.py", "write_risk_examples.py")],
    ]
    receipt = {
        "schemaVersion": "1.0.0", "taskId": "MOCK-01-01", "parentPlanId": "MOCK-01",
        "fixtureRevision": FIXTURE_REVISION,
        "owner": "A-fixtures", "reviewer": "implementation-orchestrator", "deliveryClass": "P0-HERO",
        "status": "initial-fixtures-locally-validated" if success else "validation-failed",
        "command": r"contracts\.venv\Scripts\python.exe -B tests\fixtures\validate_initial.py",
        "generationCommand": r"contracts\.venv\Scripts\python.exe -B fixtures\experience\build_initial.py",
        "startedAt": started, "completedAt": datetime.now(timezone.utc).isoformat(),
        "exitCode": 0 if success else 1, "testsRun": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "validationCounts": summary,
        "scenario": scenario_identity(read(SCENARIO_PATH)),
        "fixtureEvidenceOrigin": "fixture", "designEvidenceOrigin": "ux-mock", "validationEvidenceOrigin": "live-local",
        "humanGate": "GATE-UX01-pending", "liveProofEligible": False,
        "testLog": str(log.relative_to(ROOT)), "testLogSha256": byte_hash(log.read_bytes()),
        "artifacts": [{"path": str(p.relative_to(ROOT)), "sha256": byte_hash(p.read_bytes())} for p in files],
        "limitations": read(OUTPUT / "manifest.json")["limitations"],
    }
    (destination / "evidence-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"MOCK-01-01: {result.testsRun} tests; {summary}; no human approval or live proof.")
    print(f"Evidence: {destination.relative_to(ROOT)}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
