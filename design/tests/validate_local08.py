"""Current V2 design checks. Reuses read-only helpers; never re-labels a V1 input."""

import copy
import io
import json
import re
import sys
import unittest
from datetime import datetime, timezone

from validate_tokens import ROOT, file_hash, read_json, render_css, validate_tokens
from validation import DesignValidationError, index, require, validate_record

SCENARIO = "DEMO-CASE-CLAIMS-V2"
DIRECTIVE = ROOT / ".intent-to-impact" / "execution" / "decisions" / "LOCAL-08.json"
PATHS = {
    "journey": r"design\journey\hero-journey.v2.json",
    "informationArchitecture": r"design\information-architecture\inventory.v2.json",
    "componentStates": r"design\components\component-state-contract.v2.json",
    "tokens": r"design\tokens\tokens.v2-manifest.json",
    "builderGuide": r"design\journey\README.v2.md",
    "revisionDecision": r"design\decisions\UXD-003.json",
}
CURRENT = r"design\components\CURRENT.v2.json"
PRESERVATION = r"design\tests\local08-v1-preservation.json"
PROPERTY_NAMES = ["publicNetworkAccess", "supportsHttpsTrafficOnly", "allowBlobPublicAccess", "minimumTlsVersion"]
DESIRED = {"publicNetworkAccess": "Enabled", "supportsHttpsTrafficOnly": True,
           "allowBlobPublicAccess": False, "minimumTlsVersion": "TLS1_2"}
EXCLUDED = {"private-endpoint", "private-dns", "vnet", "vpn", "verifier-vm", "standalone-public-ip"}
PENDING_OPERATIONS = {"deployment": "not-approved", "seed": "not-approved", "restoration": "not-approved"}


def same(actual, expected, message):
    require(json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True), message)


def load_artifacts():
    data = {key: read_json(ROOT / path) for key, path in PATHS.items() if key != "builderGuide"}
    data["current"] = read_json(ROOT / CURRENT)
    return data


def check_preservation(manifest=None):
    manifest = manifest if manifest is not None else read_json(ROOT / PRESERVATION)
    files = index(manifest["files"], "path")
    require(len(files) == 34, "fixed 34-file historical preservation oracle required")
    for path, item in files.items():
        require(file_hash(ROOT / path) == item["sha256"], f"historical V1 source/evidence changed: {path}")
    return [{"path": p, "sha256": item["sha256"], "unchanged": True} for p, item in files.items()]


def record_schema_v2():
    schema = copy.deepcopy(read_json(ROOT / "design" / "reviews" / "ux-record.schema.json"))
    props = schema["$defs"]["decision"]["properties"]
    require(props["scenarioId"]["const"] == "DEMO-CASE-CLAIMS-V1"
            and props["taskId"]["const"] == "UX-03-01", "unexpected historical U04 selectors")
    props["scenarioId"]["const"] = SCENARIO
    props["taskId"]["const"] = "UX-01-01"
    return schema


def validate_cp01(journey, directive):
    reference = journey["cp01DesignReference"]
    same({key: directive["implementationInterpretation"][key] for key in PROPERTY_NAMES},
         DESIRED, "LOCAL-08 properties differ from current task oracle")
    require(directive["implementationInterpretation"]["scenarioId"] == SCENARIO,
            "directive must identify V2")
    require(reference["promiseId"] == "CP-01"
            and reference["statement"] == directive["implementationInterpretation"]["cp01Statement"],
            "CP-01 wording must match user-directed public configuration assurance")
    same(reference["desiredProperties"], DESIRED, "V2 desired properties must match all four predicates")
    same(reference["requiredInfrastructure"], ["storage-public-endpoint"], "V2 cannot require private infrastructure")
    same(sorted(reference["excludedRequiredInfrastructure"]), sorted(EXCLUDED), "private infrastructure exclusions changed")
    seed = reference["seedProposal"]
    same({key: seed[key] for key in ("authorization", "property", "from", "to")},
         {"authorization": "not-approved", "property": "supportsHttpsTrafficOnly", "from": True, "to": False},
         "V2 seed is unapproved HTTPS-required false; publicNetworkAccess Enabled is not a breach")
    same(seed["unchangedProperties"], {k: v for k, v in DESIRED.items() if k != "supportsHttpsTrafficOnly"},
         "seed must keep public endpoint, anonymous-access and TLS predicates unchanged")
    require("no real data" in seed["safeData"].lower(), "safe seed must exclude real HTTP data")
    restoration = reference["restorationProposal"]
    same({key: restoration[key] for key in ("authorization", "property", "to", "desiredStateHash")},
         {"authorization": "not-approved", "property": "supportsHttpsTrafficOnly", "to": True, "desiredStateHash": None},
         "restoration must be unapproved and bound to future approved V2 desired state")
    same(restoration["freshlyVerify"], PROPERTY_NAMES, "restoration must freshly verify all four properties")
    graph = reference["graphFocus"]
    same({key: graph[key] for key in ("property", "desiredValue", "observedExampleValue")},
         {"property": "supportsHttpsTrafficOnly", "desiredValue": True, "observedExampleValue": False},
         "graph risk property must be supportsHttpsTrafficOnly")
    same(graph["projectionRefs"], ["P05.findings", "P06.edges", "P06.gaps"], "graph refs must remain expected projections")
    same(reference["confirmation"], {"normalInProductRequired": True, "automaticallyConfirmed": False,
                                     "recordedHumanConfirmation": None}, "normal human confirmation cannot be automatic")
    same(reference["operationApproval"], PENDING_OPERATIONS, "no operation approval may be invented")
    same(reference["evidenceBoundary"], {"designOrigin": "ux-mock", "runtimeProofClaimed": False,
         "fixtureEligibleAsLiveProof": False, "newV2ProductRunRequired": True,
         "reuseV1ApprovalOrRuntimeProof": False}, "fixture/V1 evidence cannot become live V2 proof")


def validate_v2(data):
    journey, ia, components, tokens = (data[k] for k in ("journey", "informationArchitecture", "componentStates", "tokens"))
    old_journey = read_json(ROOT / "design" / "journey" / "hero-journey.v1.json")
    old_ia = read_json(ROOT / "design" / "information-architecture" / "inventory.v1.json")
    old_components = read_json(ROOT / "design" / "components" / "component-state-contract.v1.json")
    for artifact in (journey, ia, components, tokens, data["current"]):
        require(artifact["schemaVersion"] == "1.0.0" and artifact["designRevision"] == "2.0.0",
                "V2 design revision/schema version mismatch")
        scenario = artifact["scenarioRef"]["id"] if artifact is journey else artifact["scenarioId"]
        require(scenario == SCENARIO, "CURRENT artifacts must identify V2, not V1")
        require(artifact["evidenceOrigin"] == "ux-mock", "design/fixture evidence cannot be live proof")
    require(journey["scenarioRef"]["version"] == "2.0.0"
            and journey["scenarioRef"]["contentHash"] is None
            and journey["scenarioRef"]["bindingStatus"] == "pending", "canonical scenario hash binding remains pending")
    for artifact in (journey, ia, components):
        require(artifact["contractBinding"]["status"] == "pending", "P field binding must remain pending")
        require(artifact["status"] == "provisional-human-checkpoint-pending", "no human gate approval")
    for artifact in (journey, ia, tokens):
        require(artifact["wordingAlignment"] == "current-v2-complete", "wording-only blocker must be removed")
    same(journey["runContextIntent"], old_journey["runContextIntent"], "immutable fixture run context must remain")
    for key in ("customerIntent", "scope", "promiseRefs"):
        same(journey[key], old_journey[key], "business/RPO/cost/P0 scope must remain unchanged")
    same(journey["wordingConstraints"][:3], old_journey["wordingConstraints"][:3],
         "RPO and recovery/cost oracle must not change")
    validate_cp01(journey, read_json(DIRECTIVE))
    moments, old_moments = index(journey["moments"]), index(old_journey["moments"])
    require(list(moments) == list(old_moments) and len(moments) == 5, "same five hero moments required")
    for moment_id, moment in moments.items():
        for key in ("label", "routeId", "fixtureIds", "primaryIntent", "tier"):
            same(moment[key], old_moments[moment_id][key], "five-moment structure/action hierarchy changed")
    states, old_states = index(journey["states"]), index(old_journey["states"])
    require(states.keys() == old_states.keys(), "all 28 consequential states/variants required")
    for state_id, state in states.items():
        same({k: v for k, v in state.items() if k != "label"},
             {k: v for k, v in old_states[state_id].items() if k != "label"},
             "state/actions/approval/materialization ordering changed")
        if state_id not in ("FX-01", "FX-09", "FX-12"):
            require(state["label"] == old_states[state_id]["label"], "materialized/pending is not runtime verified")
    require("HTTPS" in states["FX-09"]["label"] and "configuration" in states["FX-12"]["label"],
            "risk/restoration labels need V2 configuration meaning")
    interactions, old_interactions = index(journey["interactions"]), index(old_journey["interactions"])
    require(interactions.keys() == old_interactions.keys() and len(interactions) == 18, "18 interactions required")
    for interaction_id, interaction in interactions.items():
        same({k: v for k, v in interaction.items() if k != "acceptance"},
             {k: v for k, v in old_interactions[interaction_id].items() if k != "acceptance"},
             "interaction/state/component coverage must be preserved")
    same(journey["sharedVariants"], old_journey["sharedVariants"], "shared a11y/recovery variants changed")
    for key in ("routes", "components", "navigation", "commonExpectedFieldRefs", "crossCuttingStateCoverage"):
        same(ia[key], old_ia[key], "accepted IA route/component/expected field structure must remain")
    for key in ("components", "statePresentations", "sharedStateRefs", "sharedVariantRefs",
                "sharedTokenRefs", "primaryActionPolicy", "identityTreatment", "fidelity"):
        if key == "components":
            index(components[key])
        elif key == "statePresentations":
            index(components[key], "stateId")
        same(components[key], old_components[key], "shared component/state/token/action contract changed")
    require(ia["graphRiskProperty"] == components["graphRiskProperty"] == "supportsHttpsTrafficOnly",
            "current graph property must identify HTTPS-required")
    require(components["scenarioAlignment"]["sourceScenarioId"] == SCENARIO
            and components["scenarioAlignment"]["targetScenarioId"] == SCENARIO
            and components["scenarioAlignment"]["status"] == "current-v2-wording-complete"
            and components["scenarioAlignment"]["liveFixtureBinding"] == "pending-canonical-projection-schema"
            and components["scenarioAlignment"]["sourceScenarioReinterpreted"] is False,
            "current V2 sources must remove only the wording blocker")
    same(components["sourceRefs"], [PATHS["journey"], PATHS["informationArchitecture"]], "component sources must be CURRENT V2")
    same(components["tokenContract"], {"id": "U02", "version": "1.0.0", "path": PATHS["tokens"]},
         "components must use current token manifest")
    visible = [m["customerImpact"] for m in moments.values()] + [s["label"] for s in states.values()]
    require(not any(re.search(r"approved private|private claims-storage|private-path evidence|public network disabled",
                              text, re.IGNORECASE) for text in visible), "V2 must not retain the old private promise")
    source = tokens["valueSource"]
    require(source["path"] == r"design\tokens\tokens.v1.json" and tokens["css"]["path"] == r"design\tokens\tokens.v1.css",
            "reuse the existing palette and CSS; no redesign")
    require(file_hash(ROOT / source["path"]) == source["sha256"]
            and file_hash(ROOT / tokens["css"]["path"]) == tokens["css"]["sha256"], "shared token/CSS hash drift")
    same(source["consumeSections"], ["tokens", "contrastPairs", "focus", "responsive", "reducedMotion", "statusPresentations"],
         "consume neutral token sections, not historical scenario blockers")
    values = read_json(ROOT / source["path"])
    contrast = validate_tokens(values)
    require((ROOT / tokens["css"]["path"]).read_bytes() == render_css(values), "shared CSS drift")
    require(tokens["humanVisualApproval"] == components["humanVisualApproval"] == "pending"
            and tokens["runtimeProofClaimed"] is False, "no aesthetic approval or runtime proof")
    current = data["current"]
    same(current["artifacts"], PATHS, "CURRENT must unambiguously identify all V2 handoff paths")
    same(current["readiness"], {
        "businessWording": "current-v2-complete", "wordingOnlyBlocker": False, "mockDesignConsumption": "ready",
        "canonicalProjectionBinding": "pending-A-frozen-schema",
        "fullResponseFixtureValidation": "pending-canonical-projection-schema",
        "technicalReview": "pending-implementation-orchestrator", "humanGate": "GATE-UX01-pending",
    }, "wording ready is not frozen schemas or gate acceptance")
    same(current["operationAuthorization"], PENDING_OPERATIONS, "no operation authorization")
    record = data["revisionDecision"]
    uxd_result = validate_record(record, record_schema_v2())
    require(record["recordId"] == "UXD-003" and not record["illustrative"]
            and record["state"] == "pending-review" and record["technicalReviews"]["records"] == []
            and not record["mockAlignmentEvidenceRefs"] and not record["liveAlignmentEvidenceRefs"],
            "UXD-003 is an actual technical revision, not a fabricated review/approval")
    require("LOCAL-08" in record["sourceRefs"][0], "UXD-003 must cite the user direction")
    return {"moments": len(moments), "interactions": len(interactions), "states": len(states),
            "components": len(ia["components"]), "fixtures": len({s["fixtureId"] for s in states.values()}),
            "contrastMeasurements": contrast, "uxdAcceptanceEstablished": uxd_result["acceptanceEstablished"]}


def main():
    started = datetime.now(timezone.utc).isoformat()
    output = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "design" / "tests"), pattern="test_local08_v2.py")
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    text = output.getvalue()
    sys.stdout.write(text)
    successful = result.wasSuccessful() and result.testsRun > 0
    summary = validate_v2(load_artifacts()) if successful else None
    preservation = check_preservation()
    common = [CURRENT, PATHS["revisionDecision"], r"design\tests\validate_local08.py",
              r"design\tests\test_local08_v2.py", PRESERVATION]
    targets = {
        "UX-01-01": ("LOCAL-08", [PATHS["journey"], PATHS["informationArchitecture"], PATHS["builderGuide"]]),
        "UX-02-01": ("V2", [PATHS["componentStates"], PATHS["tokens"]]),
    }
    for task, (suffix, files) in targets.items():
        destination = ROOT / ".intent-to-impact" / "spikes" / task / suffix
        destination.mkdir(parents=True, exist_ok=True)
        log = destination / "test-results.txt"
        log.write_text(text, encoding="utf-8")
        receipt = {
            "schemaVersion": "1.0.0", "taskId": task, "correction": "LOCAL-08-current-scenario-alignment",
            "parentPlanId": task[:5], "deliveryClass": "P0-SUPPORT", "scenarioId": SCENARIO, "scenarioVersion": "2.0.0",
            "owner": "D-ux", "reviewer": "implementation-orchestrator",
            "status": "v2-wording-complete-locally-validated" if successful else "validation-failed",
            "command": r"python -B design\tests\validate_local08.py",
            "startedAt": started, "completedAt": datetime.now(timezone.utc).isoformat(),
            "exitCode": 0 if successful else 1, "testsRun": result.testsRun,
            "failures": len(result.failures), "errors": len(result.errors),
            "designEvidenceOrigin": "ux-mock", "validationEvidenceOrigin": "live-local",
            "currentHandoff": CURRENT, "coverage": summary,
            "canonicalProjectionBinding": "UXD-002-pending-A-frozen-schema", "humanGate": "GATE-UX01-pending",
            "operationAuthorization": PENDING_OPERATIONS,
            "testLog": str(log.relative_to(ROOT)), "testLogSha256": file_hash(log),
            "artifacts": [{"path": p, "sha256": file_hash(ROOT / p)} for p in files + common],
            "directive": {"path": str(DIRECTIVE.relative_to(ROOT)), "sha256": file_hash(DIRECTIVE)},
            "historicalPreservation": preservation,
            "recordSchemaSpecialization": "Read-only U04 copy: only decision scenarioId=V2 and taskId=UX-01-01 selectors changed; no source schema edits.",
            "limits": [
                "Current business wording removes the wording-only prerequisite blocker, not the pending A-owned P schema binding.",
                "No production UI, complete mock payload, live runtime proof, operation authorization or human approval.",
                "UXD-003 awaits technical review; actor/evidence strings and local tests cannot authenticate or pass human gates.",
                "Token values/CSS are reused unchanged; old scenario metadata/receipts remain historical, not relabeled.",
            ],
        }
        (destination / "evidence-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"V2 correction: {result.testsRun} tests; {len(preservation)} historical files unchanged; wording ready, P binding/human gate pending.")
    return 0 if successful else 1


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
