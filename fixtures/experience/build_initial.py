"""Deterministic authored fixtures, never an evaluator, transport, or operation runner."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.contracts.integrity import semantic_checksum, validate_reference_integrity
from tools.contracts.validate import identify_contract
from tools.contracts.write_risk_examples import seal

HISTORICAL = ROOT / "fixtures" / "experience" / "initial-v2"
OUTPUT = ROOT / "fixtures" / "experience" / "initial-v2-r2"
FIXTURE_REVISION = 2
SCENARIO_PATH = ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json"
EXAMPLES_PATH = ROOT / "contracts" / "examples" / "1.0.0" / "risk-examples.json"
SCENARIO_HASH = "sha256:a140b136272f077c82dcd1d38e8e2c13b0aa7aea192be2a80112ccc744213e9a"
RUN_ID = "RUN-UX-MOCK-CLAIMS-V2-R2"
CASE_ID = "CASE-UX-MOCK-CLAIMS-V2-R2"
SCENES = [
    ("FX-01", "fx-01", "unknown", "view-risk-example", "Show authored risk example", "FX-09"),
    ("FX-09", "fx-09", "risk", "review-correction-example", "Review correction example", "FX-10"),
    ("FX-10", "fx-10", "pending", "view-verification-pending", "Inspect verification pending example", "FX-11"),
    ("FX-11", "fx-11", "pending", "view-restoration-example", "View authored restoration evidence", "FX-12"),
    ("FX-12", "fx-12", "risk", "inspect-fixture-evidence", "Inspect fixture evidence", "FX-12"),
    ("FX-11:missing-evidence", "fx-11-missing", "unknown", "view-verification-pending", "Return to pending example", "FX-11"),
    ("FX-09:stale-evidence", "fx-09-stale", "risk", "view-current-risk-example", "Return to current risk example", "FX-09"),
]
SECONDARY = {
    "FX-09": ("view-stale-evidence-example", "Inspect stale evidence example", "FX-09:stale-evidence"),
    "FX-11": ("view-missing-evidence-example", "Inspect missing evidence example", "FX-11:missing-evidence"),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def byte_hash(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def is_link(value):
    return isinstance(value, dict) and set(value) == {"contractId", "artifact", "scenario"}


def link(contract_id, value, identity):
    return {"contractId": contract_id, "artifact": {"artifactId": value["artifactId"], "checksum": value["stateChecksum"]},
            "scenario": deepcopy(identity)}


def make_run(source):
    run = deepcopy(source["runManifest"])
    run.update({"artifactId": "ART-RUN-UX-MOCK-CLAIMS-V2-R2", "runId": RUN_ID, "caseId": CASE_ID,
                "purpose": "ux-mock", "rootId": "ROOT-UX-MOCK-CLAIMS-V2-R2", "configId": "CONFIG-UX-MOCK-CLAIMS-V2-R2"})
    return seal(run)


def finalize(documents, root_id):
    """Refresh checksum-bound references in a finite fixture DAG, without verdict logic."""
    by_id = {d["artifactId"]: d for d in documents}
    complete, active = {}, set()

    def fix(value):
        if isinstance(value, list):
            return [fix(item) for item in value]
        if not isinstance(value, dict):
            return value
        if is_link(value):
            result = deepcopy(value)
            target = result["artifact"]["artifactId"]
            if target in by_id:
                result["artifact"]["checksum"] = finish(target)["stateChecksum"]
            return result
        if value.get("artifactType") in {"operations-risk", "intent-continuity-graph"}:
            return deepcopy(finish(value["artifactId"]))
        return {key: fix(child) for key, child in value.items()}

    def finish(artifact_id):
        if artifact_id in complete:
            return complete[artifact_id]
        if artifact_id in active:
            raise ValueError("Fixture reference cycle")
        active.add(artifact_id)
        complete[artifact_id] = seal({key: fix(value) for key, value in by_id[artifact_id].items()})
        active.remove(artifact_id)
        return complete[artifact_id]

    response = finish(root_id)
    return response, [complete[key] for key in sorted(complete) if key != root_id]


def author_scene(source, scene, revision, run, scenario):
    scene_id, slug, base, primary, label, target = scene
    records = {item["name"]: deepcopy(item["value"]) for item in source["records"]}
    overview = records[f"{base}-overview"]
    operations = records[f"{base}-operations"]
    graph = records[f"{base}-graph"]
    promises = records["promise-contract"]
    evidence = records["evidence-breach"]
    evaluation = records["unknown-evaluation"] if base == "unknown" else records["risk-evaluation"]
    finding = records["pending-finding"] if base == "pending" else records["risk-finding"]
    actions = [{"actionId": primary, "capability": "read-case", "label": label}]
    transitions = [{"fromSceneId": scene_id, "actionId": primary, "toSceneId": target,
                    "effect": "inspect-records" if scene_id == "FX-12" else "load-authored-snapshot",
                    "executesWorkflow": False}]
    if scene_id in SECONDARY:
        action, text, next_scene = SECONDARY[scene_id]
        actions.append({"actionId": action, "capability": "read-case", "label": text})
        transitions.append({"fromSceneId": scene_id, "actionId": action, "toSceneId": next_scene,
                            "effect": "load-authored-snapshot", "executesWorkflow": False})
    overview["allowedActions"] = deepcopy(actions)
    operations["allowedActions"] = deepcopy(actions)
    operations["blockers"] = [{
        "code": "fixture-only-no-operation-authority",
        "message": "Authored fixture only: no deployment, seed, restoration, approval or live proof is performed.",
    }]
    overview["blockers"] = deepcopy(operations["blockers"])
    overview["artifactRefs"].append(link("D03", promises, source["scenario"]))

    if scene_id == "FX-01":
        promises.update({"status": "draft", "confirmedPromiseIds": [], "confirmationDecisionId": None})
        for row in overview["coverage"]["rows"]:
            row["confirmed"] = False
            row["reasonCode"] = "promise-unconfirmed" if row["promiseId"] != "CP-01" else evaluation["reasonCode"]
        operations["headline"] = "Define Protected Claims: promises and RPO are unconfirmed (mock)"
        operations["customerImpact"] = "Confirm the claims protection requirements and the consequential RPO before decisions. No runtime assurance is established."
    elif scene_id == "FX-09":
        operations["headline"] = "Customer Promise At Risk: HTTPS is no longer required (mock)"
        operations["customerImpact"] = "The public claims endpoint no longer requires HTTPS. Anonymous blob access stays disabled; this does not mean documents were accessed."
    elif scene_id == "FX-10":
        operations["restoration"]["status"] = "prepared"
        operations["headline"] = "Correction prepared (mock); material and delivery approvals are not demonstrated"
        finding["status"] = "correction-prepared"
    elif scene_id == "FX-11":
        operations["restoration"]["status"] = "verification-pending"
        operations["headline"] = "Runtime verification pending (mock), not verified by prepared or local files"
    elif scene_id == "FX-11:missing-evidence":
        operations["restoration"]["status"] = "verification-pending"
        operations["headline"] = "Restoration remains unknown: fresh configuration evidence and binding are missing"
        operations["blockers"].append({"code": "restoration-evidence-missing", "message": "No fresh scoped restoration proof is available; do not display verified."})
    elif scene_id == "FX-09:stale-evidence":
        evidence["evidenceState"] = "stale"
        evidence["validUntil"] = "2026-09-12T17:06:00Z"
        records["evidence-baseline"]["evidenceState"] = "stale"
        evaluation.update({"status": "stale", "reasonCode": "fixture-observation-stale", "evaluatedAt": "2026-09-12T17:20:00Z"})
        for predicate in evaluation["predicateResults"]:
            predicate.update({"result": "unknown", "reasonCode": "fixture-observation-stale"})
        finding.update({"status": "stale", "reasonCode": "fixture-observation-stale"})
        operations.update({"riskState": "unknown", "headline": "Last HTTPS observation is stale (mock); current assurance is unknown"})
        operations["blockers"].append({"code": "fixture-observation-stale", "message": "The last observed property is historical; this is not a fresh risk or restoration verdict."})
        next(e for e in graph["edges"] if e["relation"] == "evaluates")["status"] = "gap"
        for projection in (overview, operations, graph):
            projection["asOf"] = "2026-09-12T17:20:00Z"
    elif scene_id == "FX-12":
        # These are fixed authored outcomes, not computed from observed properties.
        desired = deepcopy(scenario["desiredStorageConfiguration"])
        evidence.update({"observedAt": "2026-09-12T17:08:00Z", "retrievedAt": "2026-09-12T17:08:00Z",
                         "validUntil": "2026-09-12T17:13:00Z",
                         "sourceChecksum": semantic_checksum({"resourceId": run["scope"]["resourceIds"][0], "properties": desired})})
        snapshot = records["risk-snapshot"]
        snapshot["observations"][0]["properties"] = desired
        snapshot.update({"collectedAt": "2026-09-12T17:08:00Z", "evidenceWindow": {"from": "2026-09-12T17:08:00Z", "to": "2026-09-12T17:08:00Z"}})
        evaluation.update({"status": "verified", "reasonCode": "fixture-four-predicates-restored",
                           "evaluatedAt": "2026-09-12T17:08:00Z", "evidenceWindow": deepcopy(snapshot["evidenceWindow"])})
        for predicate in evaluation["predicateResults"]:
            predicate.update({"result": "pass", "reasonCode": "fixture-four-predicates-restored"})
        operation = records["baseline-operation"]
        operation.update({"operation": "restore", "operationId": "OPERATION-RESTORE-FIXTURE-V2",
                          "providerOperationId": "fixture-restoration-not-provider-proof",
                          "operatorConsentId": "CONSENT-FIXTURE-RESTORE-NOT-LIVE",
                          "startedAt": "2026-09-12T17:07:00Z", "completedAt": "2026-09-12T17:08:00Z"})
        operation["evidence"] = deepcopy(snapshot["evidence"])
        records["runtime-binding"]["boundAt"] = "2026-09-12T17:08:00Z"
        finding.update({"status": "resolved", "reasonCode": "fixture-four-predicates-restored",
                        "restorationOperation": link("D13", operation, source["scenario"]),
                        "lastObservedAt": "2026-09-12T17:08:00Z"})
        operations.update({"riskState": "no-known-risk", "headline": "CP-01 configuration restored in this fixture; other promises remain unknown",
                           "customerImpact": "This authored example shows HTTPS required, anonymous blob access disabled and TLS1.2 on the public endpoint. It is not live or complete access-control proof.",
                           "restoration": {"status": "verified", "operationReceipt": link("D13", operation, source["scenario"]),
                                           "verificationEvaluation": link("D17", evaluation, source["scenario"])}})
        next(e for e in graph["edges"] if e["relation"] == "evaluates")["status"] = "supported"
        next(n for n in graph["nodes"] if n["nodeId"] == "NODE-EVALUATION")["label"] = "Fixture CP-01 four-predicate restoration evaluation"
        next(n for n in graph["nodes"] if n["nodeId"] == "NODE-BASELINE")["label"] = "Acknowledged fixture restoration binding"
        for projection in (overview, operations, graph):
            projection["asOf"] = "2026-09-12T17:08:00Z"

    for row in overview["coverage"]["rows"]:
        if row["promiseId"] == "CP-01":
            row.update({"status": evaluation["status"], "reasonCode": evaluation["reasonCode"]})
    overview["blockers"] = deepcopy(operations["blockers"])
    next(n for n in graph["nodes"] if n["nodeId"] == "NODE-CP01")["label"] = "Protected Claims: public endpoint / HTTPS / anonymous access disabled / TLS1.2"
    next(n for n in graph["nodes"] if n["nodeId"] == "NODE-EVALUATION")["label"] = (
        "Fixture CP-01 evaluation: " + evaluation["status"] + " — " + evaluation["reasonCode"])
    overview["operationsRisk"], overview["continuityGraph"] = deepcopy(operations), deepcopy(graph)

    selected = list(records.values())
    ids = {d["artifactId"]: d["artifactId"] + "-MOCK-R2-" + slug.upper() for d in selected}
    for document in selected:
        for item in walk(document):
            if "artifactType" in item:
                item.update({"runId": RUN_ID, "caseId": CASE_ID, "caseRevisionAtWrite": revision})
                item["artifactId"] = ids[item["artifactId"]]
                if "purpose" in item:
                    item["purpose"] = "ux-mock"
                if "logicalRevision" in item:
                    item["logicalRevision"] = revision
                if scene_id in {"FX-12", "FX-09:stale-evidence"}:
                    item["updatedAt"] = "2026-09-12T17:08:00Z" if scene_id == "FX-12" else "2026-09-12T17:20:00Z"
            if is_link(item) and item["artifact"]["artifactId"] in ids:
                item["artifact"]["artifactId"] = ids[item["artifact"]["artifactId"]]
    response, needed = finalize(selected, overview["artifactId"])
    external_ids = {item["artifact"]["artifactId"] for d in [response] + needed for item in walk(d) if is_link(item)}
    externals = [deepcopy(ref) for ref in source["externalReferences"] if ref["artifact"]["artifactId"] in external_ids]
    validate_reference_integrity([response] + needed, {RUN_ID: run}, scenario, externals)
    return response, {"records": needed, "externalReferences": externals}, transitions


def build():
    source, scenario = read(EXAMPLES_PATH), read(SCENARIO_PATH)
    if scenario["stateChecksum"] != SCENARIO_HASH:
        raise ValueError("Unexpected canonical V2 scenario hash; do not silently regenerate another scenario")
    run = make_run(source)
    files = {"run-manifest.json": encoded(run)}
    entries, transitions = [], []
    for revision, scene in enumerate(SCENES):
        scene_id, slug, _, primary, _, _ = scene
        response, records, actions = author_scene(source, scene, revision, run, scenario)
        response_path, records_path = f"scenes\\{slug}\\response.json", f"scenes\\{slug}\\records.json"
        files[response_path], files[records_path] = encoded(response), encoded(records)
        entries.append({"sceneId": scene_id, "fixtureId": scene_id.split(":")[0],
                        "response": response_path, "responseSha256": byte_hash(files[response_path]),
                        "records": records_path, "recordsSha256": byte_hash(files[records_path]),
                        "primaryActionId": primary, "projectionIds": ["P01", "P05", "P06"],
                        "recordCount": len(records["records"]), "origin": "fixture"})
        transitions.extend(actions)
    action_map = {
        "schemaVersion": "1.0.0", "scenario": source["scenario"],
        "transport": {"kind": "in-memory-fixture", "networkAccess": False, "liveEndpoints": [],
                      "immutableRunMode": True, "executesWorkflow": False},
        "navigationMeaning": "Browse independent authored snapshots. A scene change never confirms, approves, materializes, deploys, seeds or restores.",
        "transitions": transitions,
    }
    files["action-map.json"] = encoded(action_map)
    manifest = {
        "schemaVersion": "1.0.0", "contractId": "U01", "taskId": "MOCK-01-01",
        "fixtureRevision": FIXTURE_REVISION,
        "supersedes": {
            "reason": "New immutable fixture identities after correcting shared Unicode checksum canonicalization.",
            "root": str(HISTORICAL.relative_to(ROOT)),
            "files": [
                {"path": str(path.relative_to(ROOT)), "sha256": byte_hash(path.read_bytes())}
                for path in sorted(HISTORICAL.rglob("*.json"))
            ],
        },
        "scenario": source["scenario"], "runMode": "fixture", "purpose": "ux-mock",
        "origin": "fixture", "evidenceOrigin": "ux-mock", "liveProofEligible": False,
        "currentDesign": "design\\components\\CURRENT.v2.json",
        "registry": "contracts\\registry\\1.0.0.json", "fullFxCatalogComplete": False,
        "inputFiles": [
            {"path": str(path.relative_to(ROOT)), "sha256": byte_hash(path.read_bytes())}
            for path in [
                SCENARIO_PATH, EXAMPLES_PATH,
                *[ROOT / "contracts" / "schemas" / "1.0.0" / f"{name}.schema.json"
                  for name in ("core", "scenario", "risk", "projections")],
                ROOT / "design" / "components" / "CURRENT.v2.json",
            ]
        ],
        "initialSceneId": "FX-01", "humanGate": "GATE-UX01-pending",
        "runManifest": "run-manifest.json", "runManifestSha256": byte_hash(files["run-manifest.json"]),
        "actionMap": "action-map.json", "actionMapSha256": byte_hash(files["action-map.json"]),
        "scenes": entries,
        "limitations": [
            "Historical V2 scenario under LOCAL-09, not current NSP/V3 proof. Original initial-v2 bytes are retained but are not valid under the corrected Unicode checksum convention.",
            "Initial P01/P05/P06 only; no complete P02/P03/P04/P07/P08/P09 or full FX-00..19 catalog.",
            "FX-10/11 show only prepared/pending risk-summary aspects. Distinct material/delivery/applying examples and local byte receipts await FND-01-04 and MOCK-01-02.",
            "D10/D11/D12 are explicitly opaque fixture references accepted only by the integrity helper's external-reference seam; never loaded graph proof.",
            "All acknowledgement/confirmation/evaluation IDs are synthetic, including FX-12 verified. No operation or human approval is authorized or proved.",
            "Unknown counts stay null. CP-05 remains unconfirmed; unsupported promises remain unknown. No client calculations or fallback to live transport.",
        ],
    }
    files["manifest.json"] = encoded(manifest)
    return files


def write_bundle(files, destination):
    for relative, content in files.items():
        path = destination / relative
        if path.exists() and path.read_bytes() != content:
            raise ValueError(f"Fixture revision is immutable; publish a new revision: {relative}")
    for relative, content in files.items():
        path = destination / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = build()
    if args.check:
        for relative, content in files.items():
            path = OUTPUT / relative
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError(f"Fixture output drift: {relative}")
        print(f"Initial V2 revision {FIXTURE_REVISION}: {len(SCENES)} scenes, {len(files)} deterministic files match.")
    else:
        write_bundle(files, OUTPUT)
        print(f"Wrote {len(files)} fixture-only files for {len(SCENES)} initial scenes.")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
