from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from jsonschema import ValidationError

from validate_initial import (
    OUTPUT, ROOT, FixtureValidationError, build, read, scene_data, validate_action_map,
    validate_catalog, validate_scene,
)
from fixtures.experience.build_initial import finalize, seal, write_bundle
from tools.contracts.integrity import ReferenceIntegrityError

sys.path.insert(0, str(ROOT / "apps" / "control-plane"))
from state.case_store import seal as store_seal


class InitialV2FixtureTests(unittest.TestCase):
    def setUp(self):
        self.manifest = read(OUTPUT / "manifest.json")
        self.run = read(OUTPUT / self.manifest["runManifest"])
        self.entries = {s["sceneId"]: s for s in self.manifest["scenes"]}
        self.select("FX-09")

    def select(self, scene_id):
        self.scene_id = scene_id
        self.response, self.bundle = scene_data(self.entries[scene_id])

    def record(self, artifact_type):
        return next(r for r in self.bundle["records"] if r["artifactType"] == artifact_type)

    def reseal(self):
        self.response, self.bundle["records"] = finalize(
            [self.response] + self.bundle["records"], self.response["artifactId"])

    def check(self):
        return validate_scene(self.response, self.bundle, self.run, self.scene_id)

    def test_all_full_projections_and_referenced_records_pass_actual_helpers(self):
        summary = validate_catalog()
        self.assertEqual(summary["scenes"], 7)
        self.assertEqual(summary["projectionRoots"], 21)
        self.assertEqual(summary["loadedDocumentRoots"], 66)
        self.assertFalse(summary["fullFxCatalogComplete"])
        self.assertFalse(summary["liveProofEligible"])

    def test_authoring_is_deterministic_and_does_not_rewrite_inputs(self):
        before = {item["path"]: item["sha256"] for item in self.manifest["inputFiles"]}
        for relative, content in build().items():
            self.assertEqual((OUTPUT / relative).read_bytes(), content, relative)
        self.assertEqual(before, {item["path"]: item["sha256"] for item in read(OUTPUT / "manifest.json")["inputFiles"]})
        validate_catalog()

    def test_revision_uses_new_identity_and_preserves_original_bundle(self):
        self.assertEqual(self.manifest["fixtureRevision"], 2)
        previous = read(ROOT / self.manifest["supersedes"]["root"] / "run-manifest.json")
        self.assertNotEqual(self.run["runId"], previous["runId"])
        self.assertNotEqual(self.run["caseId"], previous["caseId"])
        self.assertNotEqual(self.run["artifactId"], previous["artifactId"])
        self.assertEqual(self.run["scenarioHash"], previous["scenarioHash"])
        validate_catalog()

    def test_unicode_projection_hash_uses_the_real_store_convention(self):
        for scene in ("FX-01", "FX-12", "FX-11:missing-evidence"):
            with self.subTest(scene=scene):
                self.select(scene)
                self.assertTrue(any(ord(char) > 127 for char in json.dumps(self.response, ensure_ascii=False)))
                self.assertEqual(self.response["stateChecksum"], store_seal(self.response)["stateChecksum"])
                self.check()

    def test_published_revision_cannot_be_overwritten(self):
        with TemporaryDirectory(prefix="iti-fixture-revision-") as temporary:
            destination = Path(temporary)
            files = {"manifest.json": b"original", "scenes\\example.json": b"snapshot"}
            write_bundle(files, destination)
            write_bundle(files, destination)
            with self.assertRaisesRegex(ValueError, "immutable"):
                write_bundle({**files, "manifest.json": b"changed"}, destination)
            self.assertEqual((destination / "manifest.json").read_bytes(), b"original")
            self.assertEqual((destination / "scenes" / "example.json").read_bytes(), b"snapshot")

    def test_initial_promises_and_rpo_are_unconfirmed(self):
        self.select("FX-01")
        self.check()
        self.assertTrue(all(not row["confirmed"] and row["status"] == "unknown" for row in self.response["coverage"]["rows"]))
        self.assertEqual(self.record("customer-promise-contract")["confirmedPromiseIds"], [])

    def test_verified_restoration_has_fixture_evaluation_and_unknown_other_promises(self):
        self.select("FX-12")
        self.check()
        evaluation = self.record("promise-evaluation")
        self.assertEqual(evaluation["status"], "verified")
        self.assertEqual([p["result"] for p in evaluation["predicateResults"]], ["pass"] * 4)
        self.assertIsNone(self.response["coverage"]["verifiedCount"])
        self.assertEqual(self.record("evidence-reference")["eligibility"], "ineligible")

    def test_missing_and_stale_evidence_scenes_remain_explicit(self):
        for scene_id, status in (("FX-11:missing-evidence", "unknown"), ("FX-09:stale-evidence", "stale")):
            with self.subTest(scene=scene_id):
                self.select(scene_id)
                self.check()
                self.assertEqual(self.record("promise-evaluation")["status"], status)
                self.assertNotEqual(self.response["operationsRisk"]["restoration"]["status"], "verified")
                if status == "stale":
                    self.assertTrue(all(r["evidenceState"] == "stale" for r in self.bundle["records"]
                                        if r["artifactType"] == "evidence-reference"))

    def test_fixture_cannot_claim_live_origin(self):
        self.record("evidence-reference")["origin"] = "live-external"
        self.reseal()
        with self.assertRaisesRegex(FixtureValidationError, "cannot claim live origin"):
            self.check()

    def test_fixture_cannot_claim_real_provider_operation(self):
        self.record("sandbox-operation-receipt")["providerOperationId"] = "real-azure-operation"
        self.reseal()
        with self.assertRaisesRegex(FixtureValidationError, "actual provider operation"):
            self.check()

    def test_fixture_evidence_cannot_be_eligible_for_live_proof(self):
        self.record("evidence-reference")["eligibility"] = "eligible"
        self.reseal()
        with self.assertRaisesRegex(FixtureValidationError, "live-proof eligible"):
            self.check()

    def test_run_mode_and_purpose_cannot_be_changed(self):
        original = deepcopy(self.run)
        for field, value in (("runMode", "live"), ("purpose", "test")):
            with self.subTest(field=field):
                self.run = deepcopy(original)
                self.run[field] = value
                seal(self.run)
                with self.assertRaisesRegex(FixtureValidationError, "trusted run must stay"):
                    self.check()

    def test_record_mode_cannot_override_run_context(self):
        self.response["runMode"] = "live"
        self.reseal()
        with self.assertRaisesRegex(FixtureValidationError, "record mode/purpose"):
            self.check()

    def test_prepared_cannot_become_verified_without_a_verification_record(self):
        self.select("FX-10")
        self.record("operations-risk")["restoration"]["status"] = "verified"
        self.reseal()
        with self.assertRaisesRegex(ReferenceIntegrityError, "Restoration label requires an evaluation reference"):
            self.check()

    def test_verified_fixture_needs_evidence_backing_not_only_a_status_string(self):
        self.select("FX-12")
        evaluation = self.record("promise-evaluation")
        evaluation["evidence"] = []
        for predicate in evaluation["predicateResults"]:
            predicate["evidence"] = []
        self.reseal()
        with self.assertRaisesRegex(FixtureValidationError, "four evidence-backed"):
            self.check()

    def test_dangling_loaded_reference_fails(self):
        self.bundle["records"].remove(self.record("promise-evaluation"))
        with self.assertRaisesRegex(ReferenceIntegrityError, "Unresolved artifact reference"):
            self.check()

    def test_tampered_record_checksum_fails(self):
        self.record("promise-evaluation")["stateChecksum"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ReferenceIntegrityError, "checksum mismatch"):
            self.check()

    def test_old_scenario_cannot_be_reinterpreted_as_v2(self):
        self.run.update({"scenarioId": "DEMO-CASE-CLAIMS-V1", "scenarioVersion": "1.0.0"})
        seal(self.run)
        with self.assertRaises((ReferenceIntegrityError, ValidationError)):
            self.check()

    def test_graph_and_ordered_list_have_identical_supported_gap_and_broken_edges(self):
        graph = self.record("intent-continuity-graph")
        graph["listEntries"][0]["relatedEdgeIds"] = []
        self.reseal()
        with self.assertRaisesRegex(ReferenceIntegrityError, "Graph/list edge mismatch"):
            self.check()

    def test_opaque_delivery_reference_cannot_become_supported_graph_proof(self):
        self.select("FX-10")
        graph = self.record("intent-continuity-graph")
        graph["nodes"].append({"nodeId": "NODE-FAKE-CORRECTION", "nodeType": "correction", "label": "Not a loaded record",
                               "source": {"kind": "artifact", "reference": next(r for r in self.bundle["externalReferences"] if r["contractId"] == "D11")}})
        graph["listEntries"].append({"nodeId": "NODE-FAKE-CORRECTION", "relatedEdgeIds": []})
        self.reseal()
        with self.assertRaisesRegex(ReferenceIntegrityError, "Unresolved artifact reference"):
            self.check()

    def test_closed_p01_rejects_made_up_design_props(self):
        self.response["customerImpact"] = "Not a frozen P01 key"
        self.reseal()
        with self.assertRaises(ValidationError):
            self.check()

    def test_action_id_is_exact_lowercase_core_action_id(self):
        self.response["allowedActions"][0]["actionId"] = "REVIEW-CORRECTION"
        self.reseal()
        with self.assertRaises(ValidationError):
            self.check()

    def test_transition_map_cannot_call_live_endpoints_or_execute_workflow(self):
        responses = {key: scene_data(entry)[0] for key, entry in self.entries.items()}
        original = read(OUTPUT / "action-map.json")
        for field, value in (("networkAccess", True), ("liveEndpoints", ["https://management.azure.com"]),
                             ("executesWorkflow", True)):
            with self.subTest(field=field):
                actions = deepcopy(original)
                actions["transport"][field] = value
                with self.assertRaisesRegex(FixtureValidationError, "must not call live"):
                    validate_action_map(actions, list(self.entries.values()), responses)

    def test_transition_has_no_command_and_no_dangling_scene(self):
        responses = {key: scene_data(entry)[0] for key, entry in self.entries.items()}
        actions = read(OUTPUT / "action-map.json")
        actions["transitions"][0]["command"] = "not-executable"
        with self.assertRaisesRegex(FixtureValidationError, "no executable command"):
            validate_action_map(actions, list(self.entries.values()), responses)
        del actions["transitions"][0]["command"]
        actions["transitions"][0]["toSceneId"] = "FX-99"
        with self.assertRaisesRegex(FixtureValidationError, "dangling scene"):
            validate_action_map(actions, list(self.entries.values()), responses)

    def test_file_hash_mismatch_and_path_escape_fail(self):
        self.manifest["scenes"][0]["responseSha256"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(FixtureValidationError, "file hash mismatch"):
            validate_catalog(self.manifest)
        self.manifest["scenes"][0]["response"] = r"..\..\..\README.md"
        with self.assertRaisesRegex(FixtureValidationError, "escapes owned bundle"):
            validate_catalog(self.manifest)

    def test_no_full_catalog_or_human_gate_acceptance_can_be_claimed(self):
        self.manifest["humanGate"] = "GATE-UX01-passed"
        with self.assertRaisesRegex(FixtureValidationError, "no full catalog or human acceptance"):
            validate_catalog(self.manifest)


if __name__ == "__main__":
    unittest.main()
