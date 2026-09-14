import copy
import unittest

from validate_local08 import (
    ROOT, PRESERVATION, DesignValidationError, check_preservation, load_artifacts,
    read_json, record_schema_v2, validate_v2,
)


class CurrentV2DesignTests(unittest.TestCase):
    def setUp(self):
        self.data = load_artifacts()

    def check(self):
        return validate_v2(self.data)

    def test_current_v2_five_moments_eighteen_interactions_and_shared_tokens(self):
        summary = self.check()
        self.assertEqual({k: summary[k] for k in ("moments", "interactions", "states", "components", "fixtures")},
                         {"moments": 5, "interactions": 18, "states": 28, "components": 18, "fixtures": 20})
        self.assertEqual(len(summary["contrastMeasurements"]), 28)
        self.assertFalse(summary["uxdAcceptanceEstablished"])

    def test_all_historical_sources_receipts_logs_and_snapshots_are_unchanged(self):
        self.assertEqual(len(check_preservation()), 34)

    def test_historical_hash_drift_is_a_failure_not_rewritten_evidence(self):
        manifest = read_json(ROOT / PRESERVATION)
        manifest["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(DesignValidationError, "historical V1 source/evidence changed"):
            check_preservation(manifest)

    def test_current_sources_cannot_still_identify_v1(self):
        self.data["informationArchitecture"]["scenarioId"] = "DEMO-CASE-CLAIMS-V1"
        with self.assertRaisesRegex(DesignValidationError, "CURRENT artifacts must identify V2"):
            self.check()

    def test_exact_public_configuration_values_and_types_required(self):
        original = copy.deepcopy(self.data)
        for key, value in (("publicNetworkAccess", "Disabled"), ("supportsHttpsTrafficOnly", False),
                           ("supportsHttpsTrafficOnly", 1), ("allowBlobPublicAccess", True),
                           ("minimumTlsVersion", "TLS1_0")):
            with self.subTest(property=key, value=value):
                self.data = copy.deepcopy(original)
                self.data["journey"]["cp01DesignReference"]["desiredProperties"][key] = value
                with self.assertRaisesRegex(DesignValidationError, "four predicates"):
                    self.check()

    def test_private_network_or_verifier_infrastructure_cannot_be_required(self):
        original = copy.deepcopy(self.data)
        for resource in ("private-endpoint", "private-dns", "vnet", "verifier-vm"):
            with self.subTest(resource=resource):
                self.data = copy.deepcopy(original)
                self.data["journey"]["cp01DesignReference"]["requiredInfrastructure"].append(resource)
                with self.assertRaisesRegex(DesignValidationError, "cannot require private infrastructure"):
                    self.check()

    def test_old_public_network_access_seed_is_not_a_v2_breach(self):
        seed = self.data["journey"]["cp01DesignReference"]["seedProposal"]
        seed.update({"property": "publicNetworkAccess", "from": "Disabled", "to": "Enabled"})
        with self.assertRaisesRegex(DesignValidationError, "publicNetworkAccess Enabled is not a breach"):
            self.check()

    def test_https_seed_does_not_enable_anonymous_access(self):
        self.data["journey"]["cp01DesignReference"]["seedProposal"]["unchangedProperties"]["allowBlobPublicAccess"] = True
        with self.assertRaisesRegex(DesignValidationError, "anonymous-access and TLS"):
            self.check()

    def test_restoration_requires_all_four_fresh_properties(self):
        self.data["journey"]["cp01DesignReference"]["restorationProposal"]["freshlyVerify"].remove("minimumTlsVersion")
        with self.assertRaisesRegex(DesignValidationError, "freshly verify all four"):
            self.check()

    def test_graph_property_must_identify_https_requirement(self):
        self.data["journey"]["cp01DesignReference"]["graphFocus"]["property"] = "publicNetworkAccess"
        with self.assertRaisesRegex(DesignValidationError, "graph risk property"):
            self.check()

    def test_runtime_materialization_and_human_actions_cannot_be_collapsed(self):
        state = next(s for s in self.data["journey"]["states"] if s["id"] == "FX-10:material-approval-pending")
        state["illustrativeNextStateId"] = "FX-11"
        with self.assertRaisesRegex(DesignValidationError, "approval/materialization ordering"):
            self.check()

    def test_materialized_label_cannot_become_runtime_verified(self):
        next(s for s in self.data["journey"]["states"] if s["id"] == "FX-08")["label"] = "Runtime verified"
        with self.assertRaisesRegex(DesignValidationError, "not runtime verified"):
            self.check()

    def test_fixture_evidence_cannot_count_as_live_proof(self):
        self.data["journey"]["cp01DesignReference"]["evidenceBoundary"]["fixtureEligibleAsLiveProof"] = True
        with self.assertRaisesRegex(DesignValidationError, "cannot become live V2 proof"):
            self.check()

    def test_v1_runtime_evidence_cannot_be_rebound_to_v2(self):
        self.data["journey"]["cp01DesignReference"]["evidenceBoundary"]["reuseV1ApprovalOrRuntimeProof"] = True
        with self.assertRaisesRegex(DesignValidationError, "cannot become live V2 proof"):
            self.check()

    def test_design_origin_cannot_claim_provider_execution(self):
        self.data["componentStates"]["evidenceOrigin"] = "live-local"
        with self.assertRaisesRegex(DesignValidationError, "design/fixture evidence cannot be live proof"):
            self.check()

    def test_promise_confirmation_cannot_be_automatic(self):
        self.data["journey"]["cp01DesignReference"]["confirmation"]["automaticallyConfirmed"] = True
        with self.assertRaisesRegex(DesignValidationError, "human confirmation cannot be automatic"):
            self.check()

    def test_user_direction_does_not_approve_deployment_seed_or_restoration(self):
        original = copy.deepcopy(self.data)
        for operation in ("deployment", "seed", "restoration"):
            with self.subTest(operation=operation):
                self.data = copy.deepcopy(original)
                self.data["journey"]["cp01DesignReference"]["operationApproval"][operation] = "approved"
                with self.assertRaisesRegex(DesignValidationError, "no operation approval"):
                    self.check()

    def test_no_changes_to_rpo_cost_oracle_or_p1_scope(self):
        self.data["journey"]["wordingConstraints"][0] = "RPO automatically confirmed."
        with self.assertRaisesRegex(DesignValidationError, "RPO and recovery/cost oracle"):
            self.check()

    def test_missing_interaction_or_correction_state_fails(self):
        original = copy.deepcopy(self.data)
        self.data["journey"]["interactions"].pop()
        with self.assertRaisesRegex(DesignValidationError, "18 interactions required"):
            self.check()
        self.data = original
        self.data["journey"]["states"] = [
            s for s in self.data["journey"]["states"] if s["id"] != "FX-10:delivery-approved-not-applied"
        ]
        with self.assertRaisesRegex(DesignValidationError, "28 consequential states"):
            self.check()

    def test_duplicate_component_reference_fails(self):
        self.data["componentStates"]["components"].append(copy.deepcopy(self.data["componentStates"]["components"][0]))
        with self.assertRaisesRegex(DesignValidationError, "duplicate"):
            self.check()

    def test_old_private_customer_impact_is_rejected(self):
        self.data["journey"]["moments"][3]["customerImpact"] = "Connectivity no longer matches the approved private boundary."
        with self.assertRaisesRegex(DesignValidationError, "old private promise"):
            self.check()

    def test_current_handoff_cannot_point_at_historical_journey(self):
        self.data["current"]["artifacts"]["journey"] = r"design\journey\hero-journey.v1.json"
        with self.assertRaisesRegex(DesignValidationError, "unambiguously identify"):
            self.check()

    def test_neutral_token_values_css_and_no_old_alignment_blocker(self):
        original = copy.deepcopy(self.data)
        self.data["tokens"]["css"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(DesignValidationError, "token/CSS hash drift"):
            self.check()
        self.data = original
        self.data["tokens"]["valueSource"]["consumeSections"].append("scenarioAlignment")
        with self.assertRaisesRegex(DesignValidationError, "not historical scenario blockers"):
            self.check()

    def test_wording_blocker_is_removed_but_schema_binding_not_invented(self):
        original = copy.deepcopy(self.data)
        self.data["current"]["readiness"]["wordingOnlyBlocker"] = True
        with self.assertRaisesRegex(DesignValidationError, "wording ready"):
            self.check()
        self.data = original
        self.data["componentStates"]["contractBinding"]["status"] = "bound"
        with self.assertRaisesRegex(DesignValidationError, "P field binding must remain pending"):
            self.check()

    def test_human_gate_cannot_be_passed_by_the_design_revision(self):
        self.data["current"]["readiness"]["humanGate"] = "GATE-UX01-passed"
        with self.assertRaisesRegex(DesignValidationError, "gate acceptance"):
            self.check()

    def test_uxd003_cannot_fabricate_review_or_live_alignment(self):
        self.data["revisionDecision"]["liveAlignmentEvidenceRefs"] = ["FAKE-LIVE-EVIDENCE"]
        with self.assertRaisesRegex(DesignValidationError, "not a fabricated review/approval"):
            self.check()

    def test_readonly_u04_specialization_changes_only_scenario_and_task_selectors(self):
        original = read_json(ROOT / "design" / "reviews" / "ux-record.schema.json")
        specialized = record_schema_v2()
        expected = copy.deepcopy(original)
        props = expected["$defs"]["decision"]["properties"]
        props["scenarioId"]["const"] = "DEMO-CASE-CLAIMS-V2"
        props["taskId"]["const"] = "UX-01-01"
        self.assertEqual(specialized, expected)
        self.assertEqual(original["$defs"]["decision"]["properties"]["scenarioId"]["const"], "DEMO-CASE-CLAIMS-V1")


if __name__ == "__main__":
    unittest.main()
