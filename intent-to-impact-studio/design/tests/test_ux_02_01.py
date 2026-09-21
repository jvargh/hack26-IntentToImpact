import copy
import json
import unittest
from uuid import uuid4

from validate_tokens import (
    COMPONENT_FILE, CSS_FILE, EVIDENCE_DIR, INPUT_FILES, TOKEN_FILE,
    TokenValidationError, check_css, contrast_ratio, read_json, render_css,
    unique_object, validate_components, validate_tokens,
)


class TokenFoundationTests(unittest.TestCase):
    def setUp(self):
        self.bundle = read_json(TOKEN_FILE)
        self.contract = read_json(COMPONENT_FILE)
        self.journey, self.inventory = (read_json(path) for path in INPUT_FILES)

    def token(self, token_id):
        return next(t for t in self.bundle["tokens"] if t["id"] == token_id)

    def check_components(self):
        return validate_components(self.contract, self.bundle, self.journey, self.inventory)

    def test_versioned_token_bundle_and_mandated_contrast_pairs_pass(self):
        results = validate_tokens(self.bundle)
        self.assertEqual(len(results), 28)
        self.assertTrue(all(r["passed"] and r["ratio"] >= r["minimum"] for r in results))

    def test_wcag_contrast_reference_values(self):
        self.assertAlmostEqual(contrast_ratio("#000000", "#FFFFFF"), 21.0)
        self.assertAlmostEqual(contrast_ratio("#123456", "#123456"), 1.0)

    def test_missing_required_focus_and_status_tokens_fail(self):
        original = copy.deepcopy(self.bundle)
        for token_id in ("color-focus", "focus-ring-width", "status-risk-text", "status-local-surface"):
            with self.subTest(token=token_id):
                self.bundle = copy.deepcopy(original)
                self.bundle["tokens"] = [t for t in self.bundle["tokens"] if t["id"] != token_id]
                with self.assertRaisesRegex(TokenValidationError, "missing required"):
                    validate_tokens(self.bundle)

    def test_missing_required_status_presentation_fails(self):
        self.bundle["statusPresentations"] = [
            s for s in self.bundle["statusPresentations"] if s["id"] != "materialized"
        ]
        with self.assertRaisesRegex(TokenValidationError, "missing required status presentation"):
            validate_tokens(self.bundle)

    def test_status_always_requires_readable_label_icon_and_color(self):
        for field in ("label", "icon", "foreground"):
            with self.subTest(field=field):
                bundle = copy.deepcopy(self.bundle)
                del bundle["statusPresentations"][0][field]
                with self.assertRaisesRegex(TokenValidationError, "label/icon/colors/meaning"):
                    validate_tokens(bundle)

    def test_low_contrast_mandated_text_pair_fails(self):
        self.token("color-muted")["value"] = "#F7F5F0"
        with self.assertRaisesRegex(TokenValidationError, "low contrast: secondary-canvas"):
            validate_tokens(self.bundle)

    def test_contrast_threshold_cannot_be_weakened_or_pair_removed(self):
        original = copy.deepcopy(self.bundle)
        self.bundle["contrastPairs"][0]["minimum"] = 1
        with self.assertRaisesRegex(TokenValidationError, "threshold cannot be weakened"):
            validate_tokens(self.bundle)
        self.bundle = original
        self.bundle["contrastPairs"].pop()
        with self.assertRaisesRegex(TokenValidationError, "missing mandated contrast pair"):
            validate_tokens(self.bundle)

    def test_duplicate_token_and_json_keys_fail(self):
        self.bundle["tokens"].append(copy.deepcopy(self.bundle["tokens"][0]))
        with self.assertRaisesRegex(TokenValidationError, "duplicate"):
            validate_tokens(self.bundle)
        with self.assertRaisesRegex(TokenValidationError, "duplicate JSON key"):
            json.loads('{"color": "white", "color": "black"}', object_pairs_hook=unique_object)

    def test_malformed_types_and_css_injection_fail(self):
        original = copy.deepcopy(self.bundle)
        mutations = [
            ("font-weight-label", True), ("space-4", 16), ("color-ink", "#FFFFFF80"),
            ("motion-fast", "slow"), ("font-body", "serif; background:url(https://invalid)"),
            ("line-height-body", float("nan")),
        ]
        for token_id, value in mutations:
            with self.subTest(token=token_id):
                self.bundle = copy.deepcopy(original)
                self.token(token_id)["value"] = value
                with self.assertRaisesRegex(TokenValidationError, "malformed token type/value"):
                    validate_tokens(self.bundle)

    def test_required_token_type_cannot_be_reassigned(self):
        self.token("focus-ring-width").update({"type": "number", "value": 3})
        with self.assertRaisesRegex(TokenValidationError, "wrong required token type"):
            validate_tokens(self.bundle)

    def test_visible_focus_width_and_contrast_are_enforced(self):
        original = copy.deepcopy(self.bundle)
        self.token("focus-ring-width")["value"] = "1px"
        with self.assertRaisesRegex(TokenValidationError, "focus outline"):
            validate_tokens(self.bundle)
        self.bundle = original
        self.token("color-focus")["value"] = "#FFFFFF"
        with self.assertRaisesRegex(TokenValidationError, "low contrast: focus-surface"):
            validate_tokens(self.bundle)

    def test_reduced_motion_and_breakpoint_coverage_required(self):
        original = copy.deepcopy(self.bundle)
        self.token("motion-reduced")["value"] = "100ms"
        with self.assertRaisesRegex(TokenValidationError, "reduced-motion must suppress"):
            validate_tokens(self.bundle)
        self.bundle = original
        self.bundle["responsive"]["overrides"].pop()
        with self.assertRaisesRegex(TokenValidationError, "narrow layout token coverage"):
            validate_tokens(self.bundle)

    def test_css_emission_is_deterministic_under_input_reordering(self):
        expected = render_css(self.bundle)
        self.bundle["tokens"].reverse()
        self.bundle["contrastPairs"].reverse()
        self.bundle["responsive"]["overrides"].reverse()
        self.assertEqual(render_css(self.bundle), expected)
        self.assertNotIn(b"\r", expected)
        self.assertTrue(expected.endswith(b"\n"))

    def test_committed_css_matches_and_contains_accessibility_overrides(self):
        check_css(self.bundle, CSS_FILE)
        css = CSS_FILE.read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 48rem)", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("--iti-motion-standard: var(--iti-motion-reduced)", css)
        self.assertIn("--iti-focus-ring-width: 3px", css)
        self.assertNotIn("@import", css)
        self.assertNotIn("url(", css)

    def test_generated_css_drift_is_detected_in_owned_isolated_output(self):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        path = EVIDENCE_DIR / f"isolated-css-{uuid4().hex}.css"
        try:
            path.write_bytes(render_css(self.bundle))
            check_css(self.bundle, path)
            path.write_bytes(path.read_bytes() + b"/* unwanted drift */\n")
            with self.assertRaisesRegex(TokenValidationError, "CSS drift"):
                check_css(self.bundle, path)
        finally:
            path.unlink(missing_ok=True)

    def test_all_existing_components_and_journey_states_are_represented(self):
        coverage = self.check_components()
        self.assertEqual(coverage, {"components": 18, "states": 28, "fixtures": 20})

    def test_duplicate_component_or_token_reference_fails(self):
        original = copy.deepcopy(self.contract)
        self.contract["components"].append(copy.deepcopy(self.contract["components"][0]))
        with self.assertRaisesRegex(TokenValidationError, "duplicate"):
            self.check_components()
        self.contract = original
        self.contract["components"][0]["tokenRefs"].append(self.contract["components"][0]["tokenRefs"][0])
        with self.assertRaisesRegex(TokenValidationError, "duplicate component token"):
            self.check_components()

    def test_unknown_fixture_and_projection_reference_fail(self):
        original = copy.deepcopy(self.contract)
        self.contract["components"][0]["fixtureRefs"].append("FX-99")
        with self.assertRaisesRegex(TokenValidationError, "component fixture reference"):
            self.check_components()
        self.contract = original
        self.contract["components"][0]["propDrafts"]["invented"] = ["P99.clientEligibility"]
        with self.assertRaisesRegex(TokenValidationError, "expected P field"):
            self.check_components()

    def test_unfrozen_projection_binding_cannot_be_claimed_accepted(self):
        self.contract["contractBinding"]["status"] = "bound"
        with self.assertRaisesRegex(TokenValidationError, "binding remains pending"):
            self.check_components()

    def test_real_but_unrelated_fixture_cannot_replace_component_coverage(self):
        next(c for c in self.contract["components"] if c["id"] == "QuestionPanel")["fixtureRefs"] = ["FX-00"]
        with self.assertRaisesRegex(TokenValidationError, "fixture linkage"):
            self.check_components()

    def test_missing_correction_variant_and_extra_dominant_action_fail(self):
        original = copy.deepcopy(self.contract)
        self.contract["statePresentations"] = [
            s for s in self.contract["statePresentations"]
            if s["stateId"] != "FX-10:material-approved-delivery-pending"
        ]
        with self.assertRaisesRegex(TokenValidationError, "correction variants required"):
            self.check_components()
        self.contract = original
        self.contract["statePresentations"][0]["dominantActionCount"] = 2
        with self.assertRaisesRegex(TokenValidationError, "dominant action"):
            self.check_components()

    def test_materialized_and_pending_cannot_mean_runtime_verified(self):
        for state_id in ("FX-08", "FX-11"):
            with self.subTest(state=state_id):
                contract = copy.deepcopy(self.contract)
                next(s for s in contract["statePresentations"] if s["stateId"] == state_id)["statusIds"] = ["runtime-verified"]
                with self.assertRaisesRegex(TokenValidationError, "cannot imply runtime verification"):
                    validate_components(contract, self.bundle, self.journey, self.inventory)

    def test_local_and_runtime_status_styles_cannot_collapse(self):
        statuses = {s["id"]: s for s in self.bundle["statusPresentations"]}
        statuses["materialized"]["foreground"] = statuses["runtime-verified"]["foreground"]
        statuses["materialized"]["background"] = statuses["runtime-verified"]["background"]
        with self.assertRaisesRegex(TokenValidationError, "distinct presentation"):
            validate_tokens(self.bundle)

    def test_no_client_domain_rule_or_calculation_events(self):
        original = copy.deepcopy(self.contract)
        self.contract["eligibilityRules"] = {"cheapestWins": True}
        with self.assertRaisesRegex(TokenValidationError, "no client domain rules"):
            self.check_components()
        self.contract = original
        self.contract["components"][0]["events"].append("calculate-promise-coverage")
        with self.assertRaisesRegex(TokenValidationError, "no client domain rules"):
            self.check_components()

    def test_shared_mock_production_contract_and_pending_visual_approval(self):
        self.bundle["intendedConsumers"] = ["mock"]
        with self.assertRaisesRegex(TokenValidationError, "both consumers"):
            validate_tokens(self.bundle)
        self.contract["humanVisualApproval"] = "approved"
        with self.assertRaisesRegex(TokenValidationError, "visual approval remains pending"):
            self.check_components()

    def test_v2_target_is_explicit_without_reinterpreting_historical_v1(self):
        for artifact in (self.bundle, self.contract):
            self.assertEqual(artifact["scenarioId"], "DEMO-CASE-CLAIMS-V1")
            self.assertEqual(artifact["scenarioAlignment"]["targetScenarioId"], "DEMO-CASE-CLAIMS-V2")
            self.assertEqual(artifact["scenarioAlignment"]["targetScenarioVersion"], "2.0.0")
            self.assertFalse(artifact["scenarioAlignment"]["sourceScenarioReinterpreted"])
        self.assertEqual(EVIDENCE_DIR.name, "LOCAL-08")
        self.assertEqual(EVIDENCE_DIR.parent.name, "UX-02-01")

    def test_v2_fixture_binding_remains_blocked_pending_separate_wording_revision(self):
        for field, value in (("liveFixtureBinding", "ready"), ("status", "compatible")):
            with self.subTest(field=field):
                bundle = copy.deepcopy(self.bundle)
                bundle["scenarioAlignment"][field] = value
                with self.assertRaisesRegex(TokenValidationError, "pending/blocked"):
                    validate_tokens(bundle)
                contract = copy.deepcopy(self.contract)
                contract["scenarioAlignment"][field] = value
                with self.assertRaisesRegex(TokenValidationError, "pending/blocked"):
                    validate_components(contract, self.bundle, self.journey, self.inventory)

    def test_historical_source_cannot_be_silently_relabeled_v2(self):
        self.journey["scenarioRef"]["id"] = "DEMO-CASE-CLAIMS-V2"
        with self.assertRaisesRegex(TokenValidationError, "separate V2 wording revision"):
            self.check_components()

    def test_claim_topic_is_neutral_and_supplied_projection_is_not_verification(self):
        for field, value in (("topicLabel", "Private Claims"),
                             ("controlTopicLabel", "Private Connectivity"),
                             ("labelIsVerification", True)):
            with self.subTest(field=field):
                contract = copy.deepcopy(self.contract)
                contract["claimLabelPolicy"][field] = value
                with self.assertRaisesRegex(TokenValidationError, "neutral/projection-supplied"):
                    validate_components(contract, self.bundle, self.journey, self.inventory)

    def test_status_and_component_headings_cannot_require_the_old_private_promise(self):
        self.bundle["statusPresentations"][0]["label"] = "Private Connectivity"
        with self.assertRaisesRegex(TokenValidationError, "historical private promise"):
            validate_tokens(self.bundle)
        self.contract["components"][0]["displayOrder"][0] = "Private Claims"
        with self.assertRaisesRegex(TokenValidationError, "networking-neutral"):
            self.check_components()


if __name__ == "__main__":
    unittest.main()
