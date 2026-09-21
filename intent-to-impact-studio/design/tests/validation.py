"""Bounded design checks; not a product workflow or authorization engine."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = "DEMO-CASE-CLAIMS-V1"
FIXTURES = {f"FX-{n:02}" for n in range(20)}
ROUTES = {
    "home", "overview", "intent", "options", "decisions",
    "implementation", "operations", "value", "evidence",
}
COMPONENTS = {
    "CaseShell", "PromiseCard", "ContractPanel", "QuestionPanel",
    "OptionComparison", "DecisionPanel", "ChangeSetSummary", "FileDiff",
    "ValidationList", "ApplyPanel", "RiskPanel", "ContinuityGraph",
    "ContinuityList", "AwaySummary", "AttentionStrip", "OutcomeReceipt",
    "EvidenceDrawer", "EvidenceBadge",
}
CORRECTION = [
    "FX-10", "FX-10:material-approval-pending",
    "FX-10:material-approved-delivery-pending",
    "FX-10:delivery-approved-not-applied", "FX-10:applying-locally", "FX-11",
]
INTERACTIONS = {
    1: ["FX-01"], 2: ["FX-02"], 3: ["FX-03"], 4: ["FX-04", "FX-05"],
    5: ["FX-06"], 6: ["FX-07"],
    7: ["FX-07:applying-locally", "FX-08", "FX-08:baseline-acknowledged"],
    8: ["FX-09"], 9: ["FX-18"], 10: ["FX-13", "FX-18"],
    11: CORRECTION[:-1],
    12: ["FX-11", "FX-11:runtime-restoration-awaiting-consent",
         "FX-11:runtime-verification-pending"],
    13: ["FX-12"], 14: ["FX-13"], 15: ["FX-19"], 16: ["FX-00"],
    17: ["FX-14", "FX-15", "FX-16"], 18: ["FX-17"],
}
VARIANTS = {
    "loading", "disabled-action", "retry", "narrow-layout",
    "keyboard-focus", "zoom-200", "reduced-motion",
}
PARTICIPANTS = {
    1: {"Stakeholder", "D", "C", "A", "E"},
    2: {"Stakeholder", "D", "C", "A", "B", "E"},
    3: {"D", "C", "A", "B", "E", "operator"},
    4: {"Stakeholder", "D", "C", "A", "B", "E", "operator"},
    5: {"Stakeholder", "D", "C", "A", "E"},
    6: {"Stakeholder", "A", "B", "C", "D", "E"},
}
PREREQUISITES = {
    1: {"MOCK-02-01", "UX-03-01"},
    2: {"E2E-02-02", "UX-03-01"},
    3: {"E2E-02-03", "UX-03-01"},
    4: {"E2E-02-05", "UX-03-01"},
    5: {"E2E-02-06", "UX-03-01"},
    6: {"UX-04-02", "GATE-UX02", "GATE-UX03", "GATE-UX04",
        "GATE-UX05", "E2E-01-02"},
}


class DesignValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise DesignValidationError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"),
                      object_pairs_hook=unique_object)


def index(items, key="id"):
    result = {}
    for item in items:
        require(item[key] not in result, f"duplicate {key}: {item[key]}")
        result[item[key]] = item
    return result


def validate_journey(journey, inventory):
    for artifact in (journey, inventory):
        require(artifact["schemaVersion"] == "1.0.0", "design version changed")
        require(artifact["taskId"] == "UX-01-01", "task ID changed")
        require(artifact["status"] == "provisional-human-checkpoint-pending",
                "human approval cannot be inferred")
        require(artifact["evidenceOrigin"] == "ux-mock", "design is not live proof")
        require(artifact["contractBinding"]["status"] == "pending",
                "unaccepted projection binding")
    require(journey["scenarioRef"]["id"] == inventory["scenarioId"] == SCENARIO,
            "canonical scenario ID changed")
    require(journey["scenarioRef"]["version"] == "1.0.0", "scenario version changed")
    require(journey["scenarioRef"]["contentHash"] is None, "unaccepted scenario hash")
    require(journey["presentationOnly"] is True, "not a frontend workflow")
    require(journey["runContextIntent"] == {
        "runMode": "fixture", "purpose": "ux-mock", "immutable": True,
    }, "run context is mock-only and immutable")
    require(journey["scope"] == ["UC-01", "UC-02", "UC-08"], "P1 scope added")
    require(journey["promiseRefs"] == [f"CP-{n:02}" for n in range(1, 9)],
            "eight canonical promise references required")
    moments = index(journey["moments"])
    require(list(moments) == [f"MOMENT-{n:02}" for n in range(1, 6)],
            "five ordered hero moments required")
    require([m["label"] for m in moments.values()] == [
        "Promise", "Decision", "Implementation Prepared / Approved / Materialized",
        "Promise At Risk", "Proof",
    ], "hero moment semantics changed")
    routes = index(inventory["routes"])
    components = index(inventory["components"])
    require(set(routes) == ROUTES, "missing or extra P0 route")
    require(set(components) == COMPONENTS, "missing or extra component")
    paths = [r["path"] for r in routes.values() if r["path"] is not None]
    require(len(paths) == len(set(paths)), "duplicate route path")
    require(routes["evidence"]["path"] is None, "drawer must remain contextual")
    states = index(journey["states"])
    variants = index(journey["sharedVariants"])
    require(set(variants) == VARIANTS, "shared state variant coverage incomplete")
    require({s["fixtureId"] for s in states.values()} == FIXTURES,
            "FX-00..19 coverage incomplete")
    for state in states.values():
        require(state["routeId"] in routes, "unknown state route")
        require(state["fixtureId"] in routes[state["routeId"]]["fixtureIds"],
                "state fixture absent from route")
        require(state["tier"] in (1, 2, 3), "invalid fidelity tier")
        action = state["primaryAction"]
        require(action is None or isinstance(action, str) and action.strip(),
                "at most one primary action, as text or null")
        require(state["illustrativeNextStateId"] is None
                or state["illustrativeNextStateId"] in states, "dangling scene reference")
    for moment in moments.values():
        require(moment["routeId"] in routes and moment["customerImpact"].strip(),
                "moment needs customer impact and route")
        require(set(moment["fixtureIds"]) <= FIXTURES, "unknown moment fixture")
    interactions = index(journey["interactions"])
    require(set(interactions) == {f"UX-I-{n:02}" for n in range(1, 19)},
            "18 stable interactions required")
    covered = set()
    for number, expected in INTERACTIONS.items():
        interaction = interactions[f"UX-I-{number:02}"]
        actual = interaction["stateIds"]
        require(set(actual) == set(expected) and len(actual) == len(set(actual)),
                f"consequential state coverage missing for UX-I-{number:02}")
        require(set(actual) <= states.keys(), "required state definition missing")
        require(interaction["momentId"] in moments, "unknown interaction moment")
        require(set(interaction["componentIds"]) <= components.keys(),
                "unknown interaction component")
        require(set(interaction.get("variantIds", [])) <= variants.keys(),
                "unknown interaction variant")
        require(bool(interaction["acceptance"].strip()), "missing interaction acceptance")
        covered.update(actual)
    require(covered == states.keys(), "unmapped design state")
    expected_variants = {
        16: {"loading"}, 17: {"disabled-action", "retry"},
        18: {"narrow-layout", "keyboard-focus", "zoom-200", "reduced-motion"},
    }
    for number, expected in expected_variants.items():
        require(set(interactions[f"UX-I-{number:02}"].get("variantIds", [])) == expected,
                "missing interaction variant coverage")
    chains = [
        ["FX-06", "FX-07", "FX-07:applying-locally", "FX-08"],
        CORRECTION,
        ["FX-11", "FX-11:runtime-restoration-awaiting-consent",
         "FX-11:runtime-verification-pending", "FX-12"],
    ]
    for chain in chains:
        for source, target in zip(chain, chain[1:]):
            require(states[source]["illustrativeNextStateId"] == target,
                    f"consequential approval/application stage skipped: {source}")
    require(states["FX-06"]["label"] == "Implementation Prepared"
            and states["FX-07"]["label"] == "Implementation Approved"
            and states["FX-08"]["label"].startswith("Implementation Materialized /")
            and "Runtime unknown" in states["FX-08"]["label"]
            and "verification pending" in states["FX-11"]["label"],
            "local materialization is not deployment or verified restoration")
    for route in routes.values():
        require(set(route["componentIds"]) <= components.keys(), "unknown route component")
        require(set(route["fixtureIds"]) <= FIXTURES, "unknown route fixture")
        require(bool(route["accessibility"].strip()), "route accessibility required")
    require(components["ContinuityGraph"]["expectedFieldRefs"]
            == components["ContinuityList"]["expectedFieldRefs"],
            "graph/list lineage must match")
    for component in components.values():
        require(component["expectedFieldRefs"], "component needs expected field refs")
        require(all(p in {f"P0{n}" for n in range(1, 10)}
                    for p in component["projectionIds"]), "unknown projection ID")
    require(set(inventory["crossCuttingStateCoverage"]["required"]) == {
        "empty", "loading", "blocked", "stale", "failed", "recovered", "disabled-action",
    }, "screen state coverage incomplete")


def validate_record(record, schema):
    """Validate structure/completeness only; never authenticate evidence or accept a gate."""
    from jsonschema import Draft202012Validator, FormatChecker

    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker())
                  .iter_errors(record))
    require(not errors, "schema validation failed: " + "; ".join(
        error.message[:180] for error in errors))
    technical = record["technicalReviews"]
    required_roles = set(technical["requiredRoles"])
    if record["recordType"] == "ux-decision":
        expected = {"D", "C"}
        if record["classification"] != "presentation-only":
            expected.add("A")
        require(expected == required_roles, "required contract/presentation reviewer missing or extra")
        require(set(record["screenIds"]) <= ROUTES, "unknown UXD screen")
        require(set(record["componentIds"]) <= COMPONENTS, "unknown UXD component")
    else:
        n = int(record["recordId"][-2:])
        require(record["gateId"] == f"GATE-UX{n:02}", "checkpoint/gate ID mismatch")
        require(set(record["participantRoles"]) == PARTICIPANTS[n],
                "source checkpoint participants changed")
        require(required_roles == PARTICIPANTS[n] - {"Stakeholder"},
                "required technical review lanes missing or extra")
        require(set(record["prerequisiteIds"]) == PREREQUISITES[n],
                "source gate prerequisites changed")
        require(record["coordinator"] == ("D" if n == 1 else "E"),
                "wrong source gate coordinator")
        require(record["participantSourceRef"].endswith(record["recordId"]),
                "participant source reference mismatch")
        approval = record["humanApproval"]
        if approval["status"] == "approved":
            require(all(d["decision"] == "approved" for d in approval["decisions"]),
                    "rejected human decision cannot approve a checkpoint")
    reviews = index(technical["records"], "role")
    require(reviews.keys() <= required_roles, "review for unassigned technical lane")
    if technical["status"] == "complete":
        require(reviews.keys() == required_roles, "missing required technical review evidence")
        require(all(r["disposition"] == "approved" for r in reviews.values()),
                "unresolved technical review cannot be complete")
    return {
        "structuralValidation": "passed",
        "acceptanceEstablished": False,
        "evidenceAuthenticity": "unverified",
        "acceptanceBlocker": (
            "Implementation-orchestrator must inspect actual assigned-reviewer evidence, "
            "actor attribution, current subject/version, prerequisite acceptance and "
            "genuine demo-human product/UX confirmation at the linked checkpoint. "
            "Neither actorType/actorRef nor evidenceRef strings establish authenticity."
        ),
    }


def validate_review_package(checkpoints, decisions, schema):
    require(len(checkpoints) == 6, "exactly six checkpoint records required")
    checkpoint_index = index(checkpoints, "recordId")
    require(set(checkpoint_index) == {f"UX-Checkpoint-{n:02}" for n in range(1, 7)},
            "exact pending checkpoint IDs required")
    decision_index = index(decisions, "recordId")
    require("UXD-001" in decision_index and decision_index["UXD-001"]["illustrative"],
            "clearly illustrative UXD example required")
    require("UXD-002" in decision_index and not decision_index["UXD-002"]["illustrative"],
            "real pending contract question required")
    for record in checkpoints + decisions:
        validate_record(record, schema)
        require(record["technicalReviews"]["status"] == "pending"
                and not record["technicalReviews"]["records"],
                "foundation has no completed technical review")
    for checkpoint in checkpoints:
        require(checkpoint["gateState"] == "pending"
                and checkpoint["agendaState"] == "draft", "gate remains pending draft")
        require(not checkpoint["evidenceRefs"], "no checkpoint meeting evidence exists")
        require(checkpoint["humanApproval"]["status"] == "pending"
                and not checkpoint["humanApproval"]["decisions"],
                "foundation has no human product approval")
        require(set(checkpoint["openDecisionRefs"]) <= decision_index.keys(),
                "unknown checkpoint decision reference")
    for decision in decisions:
        require(decision["checkpointId"] in checkpoint_index, "unknown UXD checkpoint")
        require(decision["state"] == "pending-review", "UXD remains pending human review")
        require(not decision["liveAlignmentEvidenceRefs"], "no live alignment performed")
