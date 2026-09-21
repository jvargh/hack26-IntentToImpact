import copy
import unittest

from validation import DesignValidationError, load, validate_journey


class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.journey = load(r"design\journey\hero-journey.v1.json")
        self.inventory = load(r"design\information-architecture\inventory.v1.json")

    def check(self):
        validate_journey(self.journey, self.inventory)

    def test_complete_five_moment_18_interaction_inventory(self):
        self.check()

    def test_missing_consequential_rpo_state_fails(self):
        self.journey["states"] = [s for s in self.journey["states"] if s["id"] != "FX-02"]
        with self.assertRaises(DesignValidationError):
            self.check()

    def test_all_correction_approval_and_applying_states_are_required(self):
        original = copy.deepcopy(self.journey)
        for state in original["states"]:
            if state["id"].startswith("FX-10:") or state["id"] == "FX-07:applying-locally":
                with self.subTest(state=state["id"]):
                    self.journey = copy.deepcopy(original)
                    self.journey["states"].remove(state)
                    with self.assertRaises(DesignValidationError):
                        self.check()

    def test_missing_interaction_mapping_fails_even_when_state_exists(self):
        self.journey["interactions"][1]["stateIds"] = []
        with self.assertRaisesRegex(DesignValidationError, "consequential state coverage"):
            self.check()

    def test_correction_cannot_skip_delivery_approval(self):
        state = next(s for s in self.journey["states"]
                     if s["id"] == "FX-10:material-approval-pending")
        state["illustrativeNextStateId"] = "FX-10:applying-locally"
        with self.assertRaisesRegex(DesignValidationError, "stage skipped"):
            self.check()

    def test_local_correction_cannot_skip_operator_consent_or_pending_verification(self):
        state = next(s for s in self.journey["states"] if s["id"] == "FX-11")
        state["illustrativeNextStateId"] = "FX-12"
        with self.assertRaisesRegex(DesignValidationError, "stage skipped"):
            self.check()

    def test_materialized_cannot_be_labelled_runtime_verified(self):
        next(s for s in self.journey["states"] if s["id"] == "FX-08")["label"] = "Runtime verified"
        with self.assertRaisesRegex(DesignValidationError, "not deployment"):
            self.check()

    def test_duplicate_route_component_and_path_fail(self):
        original = copy.deepcopy(self.inventory)
        for collection in ("routes", "components"):
            with self.subTest(collection=collection):
                self.inventory = copy.deepcopy(original)
                self.inventory[collection].append(copy.deepcopy(self.inventory[collection][0]))
                with self.assertRaisesRegex(DesignValidationError, "duplicate"):
                    self.check()
        self.inventory = copy.deepcopy(original)
        self.inventory["routes"][1]["path"] = self.inventory["routes"][0]["path"]
        with self.assertRaisesRegex(DesignValidationError, "duplicate route path"):
            self.check()

    def test_multiple_primary_actions_fail(self):
        self.journey["states"][0]["primaryAction"] = ["Start", "Approve"]
        with self.assertRaisesRegex(DesignValidationError, "one primary action"):
            self.check()

    def test_fixture_state_coverage_cannot_be_dropped(self):
        self.journey["states"] = [s for s in self.journey["states"] if s["fixtureId"] != "FX-19"]
        with self.assertRaisesRegex(DesignValidationError, "coverage incomplete"):
            self.check()

    def test_narrow_keyboard_and_zoom_variants_required(self):
        self.journey["interactions"][-1]["variantIds"] = []
        with self.assertRaisesRegex(DesignValidationError, "variant coverage"):
            self.check()

    def test_graph_and_ordered_list_cannot_diverge(self):
        component = next(c for c in self.inventory["components"] if c["id"] == "ContinuityList")
        component["expectedFieldRefs"] = ["P06.nodes"]
        with self.assertRaisesRegex(DesignValidationError, "graph/list"):
            self.check()

    def test_task_scenario_and_mode_are_stable(self):
        original = copy.deepcopy(self.journey)
        changes = [("taskId", "UX-02-01"), ("evidenceOrigin", "live-local")]
        for key, value in changes:
            with self.subTest(field=key):
                self.journey = copy.deepcopy(original)
                self.journey[key] = value
                with self.assertRaises(DesignValidationError):
                    self.check()
        self.journey = copy.deepcopy(original)
        self.journey["scenarioRef"]["id"] = "DIFFERENT-SCENARIO"
        with self.assertRaises(DesignValidationError):
            self.check()
        self.journey = copy.deepcopy(original)
        self.journey["runContextIntent"]["runMode"] = "live"
        with self.assertRaises(DesignValidationError):
            self.check()


if __name__ == "__main__":
    unittest.main()
