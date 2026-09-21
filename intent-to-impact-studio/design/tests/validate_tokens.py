"""U02/U03 design validation and deterministic CSS projection; no UI/domain engine."""

import argparse
import hashlib
import io
import json
import math
import re
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKEN_FILE = ROOT / "design" / "tokens" / "tokens.v1.json"
CSS_FILE = ROOT / "design" / "tokens" / "tokens.v1.css"
COMPONENT_FILE = ROOT / "design" / "components" / "component-state-contract.v1.json"
EVIDENCE_DIR = ROOT / ".intent-to-impact" / "spikes" / "UX-02-01" / "LOCAL-08"
DIRECTIVE_FILE = ROOT / ".intent-to-impact" / "execution" / "decisions" / "LOCAL-08.json"
SCENARIO_ALIGNMENT = {
    "sourceScenarioId": "DEMO-CASE-CLAIMS-V1",
    "targetScenarioId": "DEMO-CASE-CLAIMS-V2",
    "targetScenarioVersion": "2.0.0",
    "decisionRef": r".intent-to-impact\execution\decisions\LOCAL-08.json",
    "status": "pending-separate-v2-journey-ia-wording",
    "liveFixtureBinding": "blocked",
    "sourceScenarioReinterpreted": False,
}
INPUT_FILES = [
    ROOT / "design" / "journey" / "hero-journey.v1.json",
    ROOT / "design" / "information-architecture" / "inventory.v1.json",
]
OUTPUT_FILES = [
    TOKEN_FILE, CSS_FILE, COMPONENT_FILE,
    ROOT / "design" / "tokens" / "README.md",
    ROOT / "design" / "tests" / "validate_tokens.py",
    ROOT / "design" / "tests" / "test_ux_02_01.py",
]
PALETTE_GROUPS = ("neutral", "design", "local", "verified", "risk", "warning", "fixture")
REQUIRED_STATUSES = {
    "empty", "unknown", "pending", "design-supported", "design-approved", "prepared",
    "delivery-approved", "applying", "materialized", "azure-deployed", "runtime-verified",
    "at-risk", "stale", "blocked", "failed", "recovered", "fixture", "replayed",
    "evidence-fresh", "evidence-partial",
}
REQUIRED_TOKEN_TYPES = {
    **{f"color-{name}": "color" for name in (
        "canvas", "surface", "ink", "muted", "border", "action", "action-hover",
        "on-action", "focus", "graph-edge")},
    **{f"status-{group}-{part}": "color" for group in PALETTE_GROUPS for part in ("text", "surface")},
    **{f"font-{name}": "font-family" for name in ("display", "body", "code")},
    **{f"font-weight-{name}": "font-weight" for name in ("body", "label", "heading")},
    **{f"font-size-{name}": "dimension" for name in ("meta", "body", "section", "title", "hero")},
    **{f"space-{name}": "dimension" for name in (1, 2, 3, 4, 6, 8, 12)},
    **{name: "dimension" for name in (
        "layout-page-gutter", "layout-card-gap", "layout-max-width", "layout-reading-width",
        "density-hero-padding", "density-functional-padding", "radius-card", "radius-badge",
        "border-width", "graph-edge-width", "graph-broken-width", "focus-ring-width",
        "focus-ring-offset", "control-min-height", "breakpoint-narrow")},
    "line-height-body": "number", "line-height-heading": "number",
    "motion-fast": "duration", "motion-standard": "duration", "motion-reduced": "duration",
}
EVENTS = {
    "navigate-local-route", "activate-issued-action", "inspect-safe-evidence",
    "toggle-detail", "focus-lineage-item", "open-current-decision",
    "mark-seen-issued-action", "export-issued-artifact", "close-and-restore-focus",
}


class TokenValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise TokenValidationError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def index(items, key="id"):
    require(isinstance(items, list), f"{key} inventory must be an array")
    result = {}
    for item in items:
        require(isinstance(item, dict) and key in item, f"missing {key}")
        require(isinstance(item[key], str) and item[key] not in result, f"duplicate or invalid {key}: {item[key]}")
        result[item[key]] = item
    return result


def unique_refs(values, allowed, message, allow_empty=False):
    require(isinstance(values, list) and all(isinstance(v, str) for v in values), message)
    require((allow_empty or bool(values)) and len(values) == len(set(values)), message)
    require(set(values) <= set(allowed), message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def check_metadata(artifact, contract_id):
    require(artifact["contractId"] == contract_id and artifact["schemaVersion"] == "1.0.0",
            "contract/version mismatch")
    require(artifact["taskId"] == "UX-02-01" and artifact["scenarioId"] == "DEMO-CASE-CLAIMS-V1",
            "historical source task/scenario mismatch; do not relabel V1 as V2")
    require(artifact["scenarioAlignment"] == SCENARIO_ALIGNMENT,
            "V2 wording alignment and live fixture binding must remain pending/blocked")
    require(artifact["intendedConsumers"] == ["mock", "production"], "both consumers must share tokens")
    require(artifact["evidenceOrigin"] == "ux-mock", "design artifact is not live proof")
    require(artifact["status"] == "provisional-human-checkpoint-pending"
            and artifact["humanVisualApproval"] == "pending"
            and artifact["checkpointId"] == "UX-Checkpoint-01", "human visual approval remains pending")


def luminance(color):
    channels = [int(color[n:n + 2], 16) / 255 for n in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast_ratio(a, b):
    dark, light = sorted((luminance(a), luminance(b)))
    return (light + 0.05) / (dark + 0.05)


def required_pairs():
    pairs = {
        "body-canvas": ("color-ink", "color-canvas", "normal-text"),
        "body-surface": ("color-ink", "color-surface", "normal-text"),
        "secondary-canvas": ("color-muted", "color-canvas", "normal-text"),
        "secondary-surface": ("color-muted", "color-surface", "normal-text"),
        "action-label": ("color-on-action", "color-action", "normal-text"),
        "action-hover-label": ("color-on-action", "color-action-hover", "normal-text"),
        "link-surface": ("color-action", "color-surface", "normal-text"),
        "link-canvas": ("color-action", "color-canvas", "normal-text"),
        "control-boundary-surface": ("color-border", "color-surface", "non-text"),
        "control-boundary-canvas": ("color-border", "color-canvas", "non-text"),
        "graph-edge": ("color-graph-edge", "color-surface", "non-text"),
        "graph-broken-edge": ("status-risk-text", "color-surface", "non-text"),
        "focus-surface": ("color-focus", "color-surface", "focus"),
        "focus-canvas": ("color-focus", "color-canvas", "focus"),
    }
    for group in PALETTE_GROUPS:
        pairs[f"{group}-label"] = (f"status-{group}-text", f"status-{group}-surface", "normal-text")
        pairs[f"focus-{group}"] = ("color-focus", f"status-{group}-surface", "focus")
    return pairs


def validate_tokens(bundle):
    check_metadata(bundle, "U02")
    require(set(bundle) == {
        "contractId", "schemaVersion", "artifactId", "taskId", "parentPlanId", "scenarioId",
        "owner", "reviewer", "intendedConsumers", "evidenceOrigin", "status", "checkpointId",
        "humanVisualApproval", "direction", "cssPrefix", "tokens", "contrastPairs",
        "focus", "responsive", "reducedMotion", "statusPresentations", "scenarioAlignment", "scopeNote",
    }, "token bundle contains unsupported fields")
    require(nonempty(bundle["scopeNote"]), "LOCAL-08 scope boundary must be explicit")
    require(bundle["cssPrefix"] == "iti", "CSS namespace must remain stable")
    tokens = index(bundle["tokens"])
    require(REQUIRED_TOKEN_TYPES.keys() <= tokens.keys(), "missing required status/focus/design token")
    for token_id, token in tokens.items():
        require(set(token) == {"id", "type", "value"}, "malformed token fields")
        require(re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", token_id), "invalid token ID")
        kind, value = token["type"], token["value"]
        if kind == "color":
            valid = isinstance(value, str) and re.fullmatch(r"#[0-9A-F]{6}", value)
        elif kind == "dimension":
            valid = isinstance(value, str) and re.fullmatch(r"(?:[0-9]+(?:\.[0-9]+)?)(?:px|rem|ch)", value)
            valid = valid and float(re.match(r"[0-9.]+", value)[0]) > 0
        elif kind == "duration":
            valid = isinstance(value, str) and re.fullmatch(r"[0-9]+ms", value)
        elif kind == "font-family":
            valid = isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9", \-]+', value)
            valid = valid and value.endswith(("serif", "sans-serif", "monospace"))
        elif kind == "font-weight":
            valid = type(value) is int and value in range(100, 1000, 100)
        elif kind == "number":
            valid = type(value) in (int, float) and math.isfinite(value) and value > 0
        else:
            valid = False
        require(valid, f"malformed token type/value: {token_id}")
        require(token_id not in REQUIRED_TOKEN_TYPES or kind == REQUIRED_TOKEN_TYPES[token_id],
                f"wrong required token type: {token_id}")
    pairs = index(bundle["contrastPairs"])
    require(required_pairs().keys() <= pairs.keys(), "missing mandated contrast pair")
    measurements = []
    for pair_id, pair in pairs.items():
        require(set(pair) == {"id", "foreground", "background", "minimum", "purpose"},
                "malformed contrast pair")
        foreground, background = pair["foreground"], pair["background"]
        require(foreground in tokens and background in tokens
                and tokens[foreground]["type"] == tokens[background]["type"] == "color",
                "contrast references must resolve to colors")
        purpose = pair["purpose"]
        require(purpose in ("normal-text", "non-text", "focus"), "unknown contrast purpose")
        minimum = 4.5 if purpose == "normal-text" else 3
        require(type(pair["minimum"]) in (int, float) and math.isfinite(pair["minimum"])
                and pair["minimum"] >= minimum, "AA threshold cannot be weakened")
        if pair_id in required_pairs():
            require((foreground, background, purpose) == required_pairs()[pair_id],
                    "mandated contrast pair changed")
        ratio = contrast_ratio(tokens[foreground]["value"], tokens[background]["value"])
        require(ratio >= pair["minimum"], f"low contrast: {pair_id} {ratio:.3f} < {pair['minimum']}")
        measurements.append({"id": pair_id, "ratio": round(ratio, 4),
                             "minimum": pair["minimum"], "purpose": purpose, "passed": True})
    focus = bundle["focus"]
    require(set(focus) == {"colorToken", "widthToken", "offsetToken", "gapColorToken", "treatment"},
            "focus treatment is incomplete")
    require([focus[k] for k in ("colorToken", "widthToken", "offsetToken", "gapColorToken")]
            == ["color-focus", "focus-ring-width", "focus-ring-offset", "color-surface"],
            "focus must use measured ring and separation tokens")
    require(nonempty(focus["treatment"]), "visible focus treatment required")
    for token_id in ("focus-ring-width", "focus-ring-offset"):
        value = tokens[token_id]["value"]
        require(value.endswith("px") and float(value[:-2]) >= 2, "focus outline needs >=2px width/offset")
    require(tokens["control-min-height"]["value"].endswith("rem")
            and float(tokens["control-min-height"]["value"][:-3]) >= 2.75, "44px target basis required")
    motion = bundle["reducedMotion"]
    require(set(motion) == {"mediaQuery", "durationTokenIds", "replacementTokenId", "behavior"},
            "reduced-motion coverage required")
    require(motion["mediaQuery"] == "prefers-reduced-motion: reduce"
            and motion["durationTokenIds"] == ["motion-fast", "motion-standard"]
            and motion["replacementTokenId"] == "motion-reduced"
            and tokens["motion-reduced"]["value"] == "0ms", "reduced-motion must suppress both durations")
    responsive = bundle["responsive"]
    require(set(responsive) == {"narrowMaxToken", "overrides", "behavior"}
            and responsive["narrowMaxToken"] == "breakpoint-narrow", "narrow breakpoint required")
    require(tokens["breakpoint-narrow"]["value"].endswith("rem"), "breakpoint must scale with text")
    overrides = index(responsive["overrides"], "tokenId")
    require(set(overrides) == {"layout-page-gutter", "layout-card-gap", "font-size-hero", "density-hero-padding"},
            "narrow layout token coverage incomplete")
    for token_id, override in overrides.items():
        require(set(override) == {"tokenId", "valueTokenId"}, "invalid responsive override")
        ref = override["valueTokenId"]
        require(ref in tokens and tokens[ref]["type"] == tokens[token_id]["type"],
                "responsive override type mismatch")
    statuses = index(bundle["statusPresentations"])
    require(set(statuses) == REQUIRED_STATUSES, "missing required status presentation")
    for status in statuses.values():
        require(set(status) == {"id", "label", "icon", "foreground", "background", "meaning"},
                "status must pair label/icon/colors/meaning")
        require(all(nonempty(status[k]) for k in ("label", "icon", "meaning")), "missing status label/icon/meaning")
        require(not re.search(r"\bprivate\s+(?:connectivity|claims)\b", status["label"], re.IGNORECASE),
                "status labels must not hard-code the historical private promise")
        require(any(p["purpose"] == "normal-text" and p["foreground"] == status["foreground"]
                    and p["background"] == status["background"] for p in pairs.values()),
                "status colors must use a measured text pair")
    require(statuses["materialized"]["label"] == "Implementation Materialized"
            and statuses["runtime-verified"]["label"] == "Runtime verified for scope/window",
            "materialized and runtime verification meanings must remain distinct")
    for field in ("label", "icon", "foreground", "background"):
        require(len({statuses[s][field] for s in ("materialized", "azure-deployed", "runtime-verified")}) == 3,
                "local/deployed/verified need distinct presentation")
    return measurements


def validate_components(contract, bundle, journey, inventory):
    check_metadata(contract, "U03")
    require(set(contract) == {
        "contractId", "schemaVersion", "artifactId", "taskId", "scenarioId", "tokenContract",
        "sourceRefs", "intendedConsumers", "status", "evidenceOrigin", "checkpointId",
        "humanVisualApproval", "contractBinding", "presentationOnly", "primaryActionPolicy",
        "eventBoundary", "sharedStateRefs", "sharedVariantRefs", "sharedTokenRefs",
        "identityTreatment", "components", "statePresentations", "statePresentationBoundary", "fidelity",
        "scenarioAlignment", "claimLabelPolicy",
    }, "unsupported component contract fields; no client domain rules")
    require(journey["scenarioRef"]["id"] == inventory["scenarioId"] == "DEMO-CASE-CLAIMS-V1",
            "historical V1 sources require a separate V2 wording revision, not relabeling")
    labels = contract["claimLabelPolicy"]
    require(set(labels) == {"topicLabel", "controlTopicLabel", "valueSource", "labelIsVerification", "note"}
            and labels["topicLabel"] == "Protected Claims" and labels["controlTopicLabel"] == "HTTPS"
            and labels["valueSource"] == "supplied-projection" and labels["labelIsVerification"] is False
            and nonempty(labels["note"]), "claim labels must stay neutral/projection-supplied, not private or verified")
    require(contract["presentationOnly"] is True, "no client domain workflow")
    require(contract["contractBinding"] == {"status": "pending", "owner": "A/C",
            "decisionRef": "UXD-002", "expectedProjectionVersion": "1.0.0"}, "projection binding remains pending")
    require(contract["tokenContract"] == {"id": "U02", "version": "1.0.0",
            "path": r"design\tokens\tokens.v1.json"}, "shared token version/path mismatch")
    require(contract["sourceRefs"] == [r"design\journey\hero-journey.v1.json",
            r"design\information-architecture\inventory.v1.json"], "accepted source references changed")
    require(contract["primaryActionPolicy"] == {
        "maximumDominantActions": 1, "authority": "server-issued allowedActions", "waitingMayHaveNoAction": True,
    }, "one server-issued dominant action required")
    tokens = index(bundle["tokens"])
    statuses = index(bundle["statusPresentations"])
    unique_refs(contract["sharedTokenRefs"], tokens, "unknown/duplicate shared token")
    require(set(contract["sharedStateRefs"]) == set(inventory["crossCuttingStateCoverage"]["required"]),
            "shared system states must match accepted IA")
    unique_refs(contract["sharedStateRefs"], inventory["crossCuttingStateCoverage"]["required"],
                "duplicate shared system state")
    require(set(contract["sharedVariantRefs"]) == {v["id"] for v in journey["sharedVariants"]},
            "shared interaction variants must match accepted journey")
    unique_refs(contract["sharedVariantRefs"], {v["id"] for v in journey["sharedVariants"]},
                "duplicate shared variant")
    accepted = index(inventory["components"])
    components = index(contract["components"])
    require(components.keys() == accepted.keys(), "all accepted component IDs required; no new components")
    interactions = index(journey["interactions"])
    source_states = index(journey["states"])
    fixture_ids = {s["fixtureId"] for s in source_states.values()}
    for component_id, component in components.items():
        require(set(component) == {"id", "tier", "bindingStatus", "fixtureRefs", "interactionRefs",
                "propDrafts", "displayOrder", "tokenRefs", "events", "accessibility"},
                "unsupported component fields; no predicates or workflow")
        require(type(component["tier"]) is int and component["tier"] in (1, 2, 3), "invalid component fidelity")
        require(component["bindingStatus"] == "pending", "props are not canonical/frozen")
        unique_refs(component["fixtureRefs"], fixture_ids, "unknown/duplicate component fixture reference")
        unique_refs(component["tokenRefs"], tokens, "unknown/duplicate component token reference")
        unique_refs(component["events"], EVENTS, "unknown/duplicate event; no client domain rules")
        expected_interactions = {i["id"] for i in interactions.values() if component_id in i["componentIds"]}
        unique_refs(component["interactionRefs"], interactions, "unknown/duplicate interaction reference")
        require(set(component["interactionRefs"]) == expected_interactions, "accepted interaction coverage changed")
        for interaction_id in component["interactionRefs"]:
            relevant_fixtures = {source_states[s]["fixtureId"] for s in interactions[interaction_id]["stateIds"]}
            require(bool(relevant_fixtures.intersection(component["fixtureRefs"])),
                    "component fixture linkage does not cover its accepted interaction")
        props = component["propDrafts"]
        require(isinstance(props, dict) and props, "prop drafts required")
        flattened = []
        for prop, refs in props.items():
            require(re.fullmatch(r"[a-z][A-Za-z0-9]*", prop), "invalid prop draft name")
            unique_refs(refs, accepted[component_id]["expectedFieldRefs"], "unknown/duplicate expected P field")
            flattened.extend(refs)
        require(len(flattened) == len(set(flattened))
                and set(flattened) == set(accepted[component_id]["expectedFieldRefs"]),
                "expected prop references must preserve accepted inventory")
        require(component["displayOrder"] and all(nonempty(v) for v in component["displayOrder"])
                and nonempty(component["accessibility"]), "hierarchy and accessible intent required")
        require(not any(re.search(r"\bprivate\s+(?:connectivity|claims)\b", v, re.IGNORECASE)
                        for v in component["displayOrder"]), "component headings must remain networking-neutral")
    require(components["ContinuityGraph"]["propDrafts"] == components["ContinuityList"]["propDrafts"]
            and components["ContinuityGraph"]["displayOrder"] == components["ContinuityList"]["displayOrder"],
            "graph/list must share exact lineage and reading order")
    scenes = index(contract["statePresentations"], "stateId")
    require(scenes.keys() == source_states.keys(), "all accepted journey states and correction variants required")
    for state_id, scene in scenes.items():
        require(set(scene) == {"stateId", "fixtureId", "tier", "dominantActionCount", "statusIds"},
                "state presentation is not a transition or rule")
        source = source_states[state_id]
        require(scene["fixtureId"] == source["fixtureId"] and scene["tier"] == source["tier"],
                "state fixture/fidelity mismatch")
        require(type(scene["dominantActionCount"]) is int
                and scene["dominantActionCount"] == int(source["primaryAction"] is not None),
                "dominant action must match accepted scene, never multiply or auto-advance")
        unique_refs(scene["statusIds"], statuses, "unknown/duplicate status presentation")
        require("runtime-verified" not in scene["statusIds"] or state_id == "FX-12",
                "local delivery or pending restoration cannot imply runtime verification")
    for state_id, required in {
        "FX-06": {"prepared"}, "FX-07": {"delivery-approved"},
        "FX-08": {"materialized", "unknown"}, "FX-11": {"materialized", "pending"},
        "FX-12": {"runtime-verified", "unknown"}, "FX-09": {"at-risk"},
    }.items():
        require(required <= set(scenes[state_id]["statusIds"]), "consequential state meaning lost")
    require(set(contract["fidelity"]) == {"1", "2", "3"}, "three fidelity tiers required")
    identity = contract["identityTreatment"]
    require(identity["label"] == "Demo Identity" and identity["fontToken"] == "font-size-meta"
            and identity["foregroundToken"] == "color-muted"
            and identity["backgroundToken"] == "color-surface" and nonempty(identity["detail"]),
            "compact readable Demo Identity treatment required")
    return {"components": len(components), "states": len(scenes), "fixtures": len(fixture_ids)}


def render_css(bundle):
    validate_tokens(bundle)
    tokens = index(bundle["tokens"])
    prefix = bundle["cssPrefix"]
    lines = ["/* Generated from U02 tokens.v1.json v1.0.0; do not hand-edit. */", ":root {"]
    for token_id in sorted(tokens):
        value = tokens[token_id]["value"]
        text = value if isinstance(value, str) else json.dumps(value, allow_nan=False)
        lines.append(f"  --{prefix}-{token_id}: {text};")
    lines.extend(["}", "", f"@media (max-width: {tokens[bundle['responsive']['narrowMaxToken']]['value']}) {{", "  :root {"])
    for override in sorted(bundle["responsive"]["overrides"], key=lambda item: item["tokenId"]):
        lines.append(f"    --{prefix}-{override['tokenId']}: var(--{prefix}-{override['valueTokenId']});")
    lines.extend(["  }", "}", "", "@media (prefers-reduced-motion: reduce) {", "  :root {"])
    replacement = bundle["reducedMotion"]["replacementTokenId"]
    for token_id in sorted(bundle["reducedMotion"]["durationTokenIds"]):
        lines.append(f"    --{prefix}-{token_id}: var(--{prefix}-{replacement});")
    lines.extend(["  }", "}", ""])
    return "\n".join(lines).encode("utf-8")


def check_css(bundle, path=CSS_FILE):
    require(path.is_file(), "derived CSS missing; run --emit-css")
    require(path.read_bytes() == render_css(bundle), "derived CSS drift detected")


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-css", action="store_true", help="Regenerate only the owned CSS token projection.")
    args = parser.parse_args()
    bundle, contract = read_json(TOKEN_FILE), read_json(COMPONENT_FILE)
    journey, inventory = (read_json(p) for p in INPUT_FILES)
    before = {str(p.relative_to(ROOT)): file_hash(p) for p in INPUT_FILES}
    directive = read_json(DIRECTIVE_FILE)
    require(directive["decisionId"] == "LOCAL-08"
            and directive["implementationInterpretation"]["scenarioId"] == SCENARIO_ALIGNMENT["targetScenarioId"],
            "LOCAL-08 target scenario reference mismatch")
    measurements = validate_tokens(bundle)
    coverage = validate_components(contract, bundle, journey, inventory)
    if args.emit_css:
        CSS_FILE.write_bytes(render_css(bundle))
        print(f"Generated {CSS_FILE.relative_to(ROOT)} deterministically.")
        return 0
    started = datetime.now(timezone.utc).isoformat()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "design" / "tests"), pattern="test_ux_02_01.py")
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    text = output.getvalue()
    sys.stdout.write(text)
    success = result.wasSuccessful() and result.testsRun > 0
    unchanged = before == {str(p.relative_to(ROOT)): file_hash(p) for p in INPUT_FILES}
    success = success and unchanged
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    log = EVIDENCE_DIR / "test-results.txt"
    log.write_text(text, encoding="utf-8")
    receipt = {
        "schemaVersion": "1.0.0", "taskId": "UX-02-01", "parentPlanId": "UX-02",
        "deliveryClass": "P0-SUPPORT", "scenarioId": "DEMO-CASE-CLAIMS-V1",
        "scenarioAlignment": SCENARIO_ALIGNMENT,
        "coverageScenarioId": "DEMO-CASE-CLAIMS-V1",
        "v2JourneyCoverageValidated": False, "v2LiveFixtureBindingValidated": False,
        "scopeDirective": {"path": str(DIRECTIVE_FILE.relative_to(ROOT)), "sha256": file_hash(DIRECTIVE_FILE)},
        "historicalEvidenceRoot": r".intent-to-impact\spikes\UX-02-01\history\DEMO-CASE-CLAIMS-V1",
        "owner": "D-ux", "reviewer": "implementation-orchestrator",
        "status": "draft-implemented-locally-validated" if success else "validation-failed",
        "command": r"python -B design\tests\validate_tokens.py",
        "generationCommand": r"python -B design\tests\validate_tokens.py --emit-css",
        "startedAt": started, "completedAt": datetime.now(timezone.utc).isoformat(),
        "exitCode": 0 if success else 1, "testsRun": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "designEvidenceOrigin": "ux-mock", "validationEvidenceOrigin": "live-local",
        "humanVisualApproval": "pending", "checkpointId": "UX-Checkpoint-01",
        "technicalFieldBinding": {"status": "pending", "decisionRef": "UXD-002"},
        "coverage": coverage, "tokenCount": len(bundle["tokens"]),
        "contrastMethod": "WCAG sRGB relative luminance; unrounded comparison; normal text >=4.5:1, focus/non-text >=3:1",
        "contrastMeasurements": measurements,
        "testLog": str(log.relative_to(ROOT)), "testLogSha256": file_hash(log),
        "artifacts": [{"path": str(p.relative_to(ROOT)), "sha256": file_hash(p)} for p in OUTPUT_FILES],
        "acceptedInputs": [{"path": path, "sha256": digest} for path, digest in before.items()],
        "acceptedInputsUnchanged": unchanged,
        "limits": [
            "Token-level contrast/focus specifications only; no rendered browser/a11y or human visual acceptance.",
            "No UI components, mock payloads, canonical schemas, generated domain types or client workflow rules.",
            "No external assets/services, cloud operations, deployed application or runtime proof.",
            "C must bind both future transports to the same token artifact; A/C reconcile expected field refs after freeze.",
            "LOCAL-08 targets V2 public-endpoint configuration. A separate V2 journey/IA wording revision is required before live fixture binding; V1 is not reinterpreted or accepted as V2.",
            "Normal in-product promise confirmation is still required. No deployment, drift-seed or other Azure operation is authorized by this design update.",
        ],
    }
    (EVIDENCE_DIR / "evidence-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"UX-02-01: {result.testsRun} tests; {len(measurements)} contrast pairs; {receipt['status']}")
    return receipt["exitCode"]


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
