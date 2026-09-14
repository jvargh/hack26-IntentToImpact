"""FND-01-03 fixture contract and cross-reference tests; no provider or evaluator calls."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from jsonschema import ValidationError
from tools.contracts.integrity import (
    ReferenceIntegrityError, assert_scenario_identity_unchanged, scenario_identity,
    semantic_checksum, validate_reference_integrity, validate_scenario,
)
from tools.contracts.validate import (
    BUNDLES, CONTRACT_NAMES, REGISTERED_CONTRACTS, REGISTRY_MANIFEST,
    identify_contract, validate_contract,
)
from tools.contracts.write_risk_examples import build_examples

EXAMPLES = ROOT / "contracts" / "examples" / "1.0.0"
SCENARIO = ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json"
GENERATED = ROOT / "contracts" / "generated" / "1.0.0"
WORK = ROOT / ".intent-to-impact" / "spikes" / "FND-01-03"
CORE_REQUIRED = BUNDLES["core"]["definitions"]["CommonEnvelope"]["required"]


def packet():
    return json.loads((EXAMPLES / "risk-examples.json").read_text(encoding="utf-8"))


def scenario():
    return json.loads(SCENARIO.read_text(encoding="utf-8"))


def records(value):
    return {item["name"]: item["value"] for item in value["records"]}


def seal(value):
    value["stateChecksum"] = semantic_checksum(value)
    return value


def check_packet(value, *, selected=None, extra_runs=None):
    runs = {value["runManifest"]["runId"]: value["runManifest"], **(extra_runs or {})}
    documents = list(records(value).values()) if selected is None else selected
    validate_reference_integrity(documents, runs, scenario(), value["externalReferences"])


def command(*arguments):
    return subprocess.run(
        list(arguments), cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"},
    )


class V2ScenarioTests(unittest.TestCase):
    def test_canonical_scenario_hash_and_unbound_public_configuration(self):
        value = scenario()
        validate_scenario(value)
        self.assertEqual(value["desiredStorageConfiguration"], {
            "publicNetworkAccess": "Enabled", "supportsHttpsTrafficOnly": True,
            "allowBlobPublicAccess": False, "minimumTlsVersion": "TLS1_2",
        })
        self.assertTrue(all(item is None for item in value["operatorBinding"].values()))
        self.assertEqual(value["seedProposal"]["authorizationStatus"], "not-authorized")
        self.assertFalse(value["seedProposal"]["after"])
        self.assertFalse(value["seedProposal"]["allowBlobPublicAccess"])
        self.assertEqual(value["desiredStateChecksum"], semantic_checksum(value["desiredStorageConfiguration"]))

    def test_each_of_eight_promise_ids_occurs_exactly_once(self):
        value = scenario()
        self.assertEqual({p["promiseId"] for p in value["promises"]}, {f"CP-{i:02d}" for i in range(1, 9)})
        duplicate = deepcopy(value)
        duplicate["promises"][-1]["promiseId"] = "CP-01"
        duplicate["promises"][-1]["statement"] = "Different text must not bypass ID uniqueness."
        with self.assertRaises(ValidationError):
            validate_contract(duplicate, "SCENARIO-V2")
        for count in (7, 9):
            changed = deepcopy(value)
            changed["promises"] = (value["promises"] + [value["promises"][0]])[:count]
            with self.assertRaises(ValidationError):
                validate_contract(changed, "SCENARIO-V2")

    def test_cost_and_recovery_are_facts_not_eligibility_or_rpo_confirmation(self):
        value = scenario()
        self.assertIsNone(value["rpoMinutes"])
        self.assertEqual(value["scriptedRpoAnswerMinutes"], 15)
        self.assertEqual(value["monthlyBudgetUsd"], 8000)
        self.assertEqual([(c["candidateId"], c["monthlyEstimateUsd"]) for c in value["candidates"]], [("A", 6000), ("B", 7200)])
        self.assertIsNone(value["candidates"][0]["regionalRecoveryProfile"])
        self.assertEqual(value["candidates"][1]["regionalRecoveryProfile"], "PROFILE-ACTIVE-PASSIVE-V2")
        for candidate in value["candidates"]:
            self.assertNotIn("eligibility", candidate)
        value["candidates"][0]["monthlyEstimateUsd"] = 7200
        with self.assertRaises(ValidationError):
            validate_contract(value, "SCENARIO-V2")

    def test_semantic_hash_ignores_format_order_and_own_checksum_only(self):
        value = scenario()
        expected = value["stateChecksum"]
        reordered = json.loads(json.dumps(dict(reversed(list(value.items()))), indent=4))
        reordered["stateChecksum"] = "sha256:" + "0" * 64
        self.assertEqual(semantic_checksum(reordered), expected)
        with self.assertRaisesRegex(ReferenceIntegrityError, "content checksum"):
            validate_scenario(reordered)
        reordered["businessIntent"] += " Changed."
        self.assertNotEqual(semantic_checksum(reordered), expected)

    def test_desired_state_and_predicate_linkage_cannot_drift(self):
        value = scenario()
        value["baselineCriteria"]["desiredStateChecksum"] = "sha256:" + "1" * 64
        seal(value)
        with self.assertRaisesRegex(ReferenceIntegrityError, "Desired-state checksum"):
            validate_scenario(value)
        value = scenario()
        value["cp01Verifier"]["predicates"][-1] = deepcopy(value["cp01Verifier"]["predicates"][0])
        seal(value)
        with self.assertRaisesRegex(ReferenceIntegrityError, "exactly once"):
            validate_scenario(value)

    def test_v1_cannot_be_rebound_to_v2_by_changing_id_alone(self):
        current = scenario_identity(scenario())
        historic = {"scenarioId": "DEMO-CASE-CLAIMS-V1", "scenarioVersion": "1.0.0", "scenarioHash": "sha256:" + "1" * 64}
        relabelled = {**historic, "scenarioId": current["scenarioId"]}
        for identity in (historic, relabelled):
            with self.assertRaisesRegex(ReferenceIntegrityError, "Scenario ID/version/hash"):
                assert_scenario_identity_unchanged(identity, current)
        value = packet()
        old_run = deepcopy(value["runManifest"])
        old_run.update(runId="RUN-HISTORICAL-V1", **historic)
        seal(old_run)
        old_evidence = records(value)["evidence-breach"]
        old_evidence["runId"] = old_run["runId"]
        seal(old_evidence)
        with self.assertRaisesRegex(ReferenceIntegrityError, "Scenario ID/version/hash"):
            check_packet(value, extra_runs={old_run["runId"]: old_run})


class RiskSchemaTests(unittest.TestCase):
    def test_issued_projection_action_flows_unchanged_through_policy_and_e05(self):
        sys.path.insert(0, str(ROOT / "apps" / "control-plane"))
        from policy import Policy

        value = packet()
        values = records(value)
        run = value["runManifest"]
        policy = Policy(
            run, scope=run["scope"], root_id=run["rootId"], config_id=run["configId"],
            enabled_capabilities=("read-case",),
        )
        entry = policy.human_entry("browser", capabilities=("read-case",))
        for scene in ("unknown", "risk", "pending"):
            for surface, contract_id in (("overview", "P01"), ("operations", "P05")):
                with self.subTest(scene=scene, surface=surface):
                    projection = values[f"{scene}-{surface}"]
                    validate_contract(projection, contract_id)
                    issued = projection["allowedActions"][0]
                    request = {"capability": issued["capability"], "actionId": issued["actionId"]}
                    result = policy.authorize(entry, request, current_run=run)
                    self.assertTrue(result.allowed, result.reason)
                    attention = values["product-attention"]
                    validate_contract(attention, "E05")
                    self.assertEqual(request["actionId"], issued["actionId"])
                    self.assertEqual(attention["actionId"], request["actionId"])
                    self.assertEqual(attention["activityClass"], result.activity_class)

    def test_artifact_style_action_id_is_rejected_by_projection_policy_and_e05(self):
        sys.path.insert(0, str(ROOT / "apps" / "control-plane"))
        from policy import Policy

        value = packet()
        values = records(value)
        run = value["runManifest"]
        policy = Policy(
            run, scope=run["scope"], root_id=run["rootId"], config_id=run["configId"],
            enabled_capabilities=("read-case",),
        )
        entry = policy.human_entry("browser", capabilities=("read-case",))
        invalid_id = "ACTION-UPPERCASE"
        for name, contract_id in (("risk-overview", "P01"), ("risk-operations", "P05")):
            projection = deepcopy(values[name])
            projection["allowedActions"][0]["actionId"] = invalid_id
            with self.assertRaises(ValidationError):
                validate_contract(projection, contract_id)
        result = policy.authorize(entry, {"capability": "read-case", "actionId": invalid_id}, current_run=run)
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "malformed-request")
        attention = deepcopy(values["product-attention"])
        attention["actionId"] = invalid_id
        with self.assertRaises(ValidationError):
            validate_contract(attention, "E05")

    def test_registry_and_all_positive_examples(self):
        value = packet()
        self.assertEqual(value["exampleOrigin"], "fixture")
        self.assertEqual(len(value["records"]), 25)
        self.assertEqual(set(CONTRACT_NAMES), {"D01", "D22", "E01", "E02", "E03", "E04", "E07", "E08"})
        self.assertEqual(sum(bundle in {"core", "scenario", "risk", "projections"} for bundle, _ in REGISTERED_CONTRACTS.values()), 19)
        self.assertEqual({item["contractId"] for item in value["records"]} - set(CONTRACT_NAMES), {"D03", "D13", "D14", "D15", "D16", "D17", "E05", "P01", "P05", "P06"})
        for item in value["records"]:
            with self.subTest(example=item["name"]):
                self.assertEqual(identify_contract(item["value"]), item["contractId"])
                validate_contract(item["value"], item["contractId"])
        check_packet(value)

    def test_negative_vectors_are_rejected_by_real_schemas(self):
        values = records(packet())
        cases = json.loads((EXAMPLES / "risk-negative-cases.json").read_text(encoding="utf-8"))
        self.assertEqual(cases["exampleOrigin"], "fixture")
        for case in cases["cases"]:
            with self.subTest(case=case["name"]):
                value = scenario() if case["base"] == "scenario" else deepcopy(values[case["base"]])
                contract_id = "SCENARIO-V2" if case["base"] == "scenario" else identify_contract(value)
                target = value
                for key in case["path"][:-1]:
                    target = target[key]
                if case.get("delete"):
                    del target[case["path"][-1]]
                else:
                    target[case["path"][-1]] = case["value"]
                with self.assertRaises(ValidationError):
                    validate_contract(value, contract_id)

    def test_inherited_metadata_is_required_by_json_validation_on_every_new_root(self):
        seen = set()
        for item in packet()["records"]:
            contract_id = item["contractId"]
            if contract_id in CONTRACT_NAMES or contract_id in seen:
                continue
            seen.add(contract_id)
            for field in CORE_REQUIRED:
                with self.subTest(contract=contract_id, missing=field):
                    value = deepcopy(item["value"])
                    del value[field]
                    with self.assertRaises(ValidationError):
                        validate_contract(value, contract_id)
        self.assertEqual(len(seen), 10)

    def test_unknown_missing_and_null_properties_do_not_require_fabricated_observations(self):
        values = records(packet())
        validate_contract(values["missing-binding"], "D14")
        validate_contract(values["unknown-snapshot"], "D15")
        validate_contract(values["unknown-evaluation"], "D17")
        self.assertIsNone(values["unknown-snapshot"]["binding"])
        self.assertEqual(values["unknown-snapshot"]["observations"], [])
        partial = deepcopy(values["risk-snapshot"])
        partial["completeness"] = "partial"
        partial["observations"][0]["properties"] = {"supportsHttpsTrafficOnly": None}
        validate_contract(partial, "D15")
        for name in ("unknown-overview", "risk-overview", "pending-overview"):
            validate_contract(values[name], "P01")
            self.assertIsNone(values[name]["coverage"]["verifiedCount"])
            self.assertIsNone(values[name]["coverage"]["applicableCount"])

    def test_fixture_and_live_origins_are_distinct_labels_not_passing_verdicts(self):
        value = deepcopy(records(packet())["risk-snapshot"])
        for origin in ("fixture", "live-external", "live-local", "replayed", "ux-mock"):
            with self.subTest(origin=origin):
                value["evidence"][0]["origin"] = origin
                validate_contract(value, "D15")
        forged = packet()
        record = records(forged)["risk-snapshot"]
        record["evidence"][0]["origin"] = "live-external"
        seal(record)
        with self.assertRaisesRegex(ReferenceIntegrityError, "Evidence origin mismatch"):
            check_packet(forged)

    def test_human_attention_requires_real_human_attribution_and_valid_activity_class(self):
        values = records(packet())
        self.assertEqual(values["product-attention"]["activityClass"], "product-workflow")
        self.assertEqual(values["operator-attention"]["activityClass"], "demo-operator")
        for actor in (
            {"kind": "agent", "actorId": "AGENT-EXAMPLE"},
            {"kind": "human", "actorId": "another-human", "identityAssurance": "local-demo"},
            {"kind": "human", "actorId": "demo-human", "identityAssurance": "entra-verified"},
        ):
            value = deepcopy(values["product-attention"])
            value["actor"] = actor
            with self.assertRaises(ValidationError):
                validate_contract(value, "E05")
        source = deepcopy(values["product-source-event"])
        source["actor"] = {"kind": "system", "actorId": "SYSTEM-WORKER"}
        seal(source)
        attention = deepcopy(values["product-attention"])
        attention["sourceEvent"]["artifact"]["checksum"] = source["stateChecksum"]
        seal(attention)
        with self.assertRaisesRegex(ReferenceIntegrityError, "no matching human source"):
            check_packet(packet(), selected=[source, attention])

    def test_fixture_authoring_is_reproducible_and_never_an_evaluator(self):
        self.assertEqual(packet(), build_examples())
        self.assertEqual(scenario()["seedProposal"]["authorizationStatus"], "not-authorized")
        self.assertEqual(records(packet())["pending-operations"]["restoration"]["status"], "awaiting-operator")


class ReferenceIntegrityTests(unittest.TestCase):
    def test_mismatched_reference_hash_and_unresolved_ids_fail(self):
        for field, replacement in (("checksum", "sha256:" + "9" * 64), ("artifactId", "OPERATION-NOT-LOADED")):
            with self.subTest(field=field):
                value = packet()
                binding = records(value)["runtime-binding"]
                binding["operationReceipt"]["artifact"][field] = replacement
                seal(binding)
                with self.assertRaisesRegex(ReferenceIntegrityError, "Reference checksum mismatch|Unresolved artifact reference"):
                    check_packet(value)

    def test_bound_baseline_must_match_the_operations_manifest(self):
        value = packet()
        binding = records(value)["runtime-binding"]
        other = deepcopy(value["externalReferences"][0])
        other["artifact"] = {"artifactId": "GENERATION-DIFFERENT", "checksum": "sha256:" + "2" * 64}
        value["externalReferences"].append(other)
        binding["generationManifest"] = other
        seal(binding)
        with self.assertRaisesRegex(ReferenceIntegrityError, "Baseline generationManifest mismatch"):
            check_packet(value)

    def test_observation_cannot_change_bound_resource_or_reference_unlisted_evidence(self):
        for field in ("resourceId", "evidence"):
            value = packet()
            snapshot = records(value)["risk-snapshot"]
            if field == "resourceId":
                snapshot["observations"][0]["resourceId"] = snapshot["observations"][0]["resourceId"].replace("claimsfixturev2", "anotherfixture")
            else:
                snapshot["evidence"] = []
            seal(snapshot)
            with self.assertRaisesRegex(ReferenceIntegrityError, "resourceId mismatch|unlisted snapshot evidence"):
                check_packet(value)

    def test_verifier_hash_and_predicate_ids_must_match_the_v2_scenario(self):
        for field in ("checksum", "predicateId"):
            value = packet()
            evaluation = records(value)["risk-evaluation"]
            if field == "checksum":
                evaluation["verifier"]["checksum"] = "sha256:" + "3" * 64
            else:
                evaluation["predicateResults"][0]["predicateId"] = "PRED-UNSUPPORTED"
            seal(evaluation)
            with self.assertRaisesRegex(ReferenceIntegrityError, "verifier version/checksum mismatch|predicate linkage mismatch"):
                check_packet(value)

    def test_baseline_desired_hash_cannot_be_relabelled_as_v2(self):
        value = packet()
        values = records(value)
        operation = values["baseline-operation"]
        binding = values["runtime-binding"]
        old_desired_hash = semantic_checksum({"publicNetworkAccess": "Disabled"})
        operation["desiredStateChecksum"] = old_desired_hash
        seal(operation)
        binding["desiredStateChecksum"] = old_desired_hash
        binding["operationReceipt"]["artifact"]["checksum"] = operation["stateChecksum"]
        seal(binding)
        with self.assertRaisesRegex(ReferenceIntegrityError, "Baseline desired-state does not match scenario"):
            check_packet(value)

    def test_reversed_window_and_changed_run_mode_are_rejected(self):
        value = packet()
        snapshot = records(value)["risk-snapshot"]
        snapshot["evidenceWindow"]["from"] = "2026-09-12T18:00:00Z"
        seal(snapshot)
        with self.assertRaisesRegex(ReferenceIntegrityError, "window is reversed"):
            check_packet(value)
        value = packet()
        snapshot = records(value)["risk-snapshot"]
        snapshot["runMode"] = "live"
        seal(snapshot)
        with self.assertRaisesRegex(ReferenceIntegrityError, "Artifact/run mode mismatch"):
            check_packet(value)

    def _check_graph(self, graph):
        value = packet()
        canonical = [item["value"] for item in value["records"] if not item["contractId"].startswith("P")]
        seal(graph)
        check_packet(value, selected=[*canonical, graph])

    def test_graph_cannot_invent_a_link_between_existing_artifacts(self):
        graph = deepcopy(records(packet())["risk-graph"])
        nodes = {node["nodeId"]: node for node in graph["nodes"]}
        edge = next(edge for edge in graph["edges"] if edge["edgeId"] == "EDGE-EVALUATION-SNAPSHOT")
        edge.update(fromNodeId="NODE-SNAPSHOT", toNodeId="NODE-EVALUATION")
        edge["support"] = {
            "kind": "artifact-link",
            "source": nodes["NODE-SNAPSHOT"]["source"]["reference"],
            "target": nodes["NODE-EVALUATION"]["source"]["reference"],
        }
        with self.assertRaisesRegex(ReferenceIntegrityError, "source does not reference graph target"):
            self._check_graph(graph)

    def test_graph_rejects_wrong_endpoints_unknown_entities_and_duplicate_ids(self):
        graph = deepcopy(records(packet())["risk-graph"])
        graph["edges"][0]["toNodeId"] = "NODE-DOES-NOT-EXIST"
        with self.assertRaisesRegex(ReferenceIntegrityError, "unknown endpoint"):
            self._check_graph(graph)
        graph = deepcopy(records(packet())["risk-graph"])
        graph["nodes"][0]["source"]["entityId"] = "INTENT-UNRELATED"
        with self.assertRaisesRegex(ReferenceIntegrityError, "Unknown or mismatched"):
            self._check_graph(graph)
        graph = deepcopy(records(packet())["risk-graph"])
        graph["nodes"].append(deepcopy(graph["nodes"][0]))
        with self.assertRaisesRegex(ReferenceIntegrityError, "Duplicate graph node"):
            self._check_graph(graph)

    def test_broken_gap_and_pending_edges_must_match_their_source_kind(self):
        values = records(packet())
        graph = deepcopy(values["risk-graph"])
        edge = next(edge for edge in graph["edges"] if edge["support"]["kind"] == "evaluation")
        edge["status"] = "supported"
        with self.assertRaisesRegex(ReferenceIntegrityError, "disagrees with source evaluation"):
            self._check_graph(graph)
        for name in ("unknown-graph", "pending-graph"):
            graph = deepcopy(values[name])
            edge = next(edge for edge in graph["edges"] if edge["support"]["kind"] == "gap")
            edge["status"] = "supported"
            with self.assertRaisesRegex(ReferenceIntegrityError, "Gap edge cannot claim"):
                self._check_graph(graph)

    def test_accessible_list_is_the_same_graph_not_a_second_story(self):
        graph = deepcopy(records(packet())["risk-graph"])
        graph["listEntries"][0]["relatedEdgeIds"] = []
        with self.assertRaisesRegex(ReferenceIntegrityError, "Graph/list edge mismatch"):
            self._check_graph(graph)
        graph = deepcopy(records(packet())["risk-graph"])
        graph["listEntries"].pop()
        with self.assertRaisesRegex(ReferenceIntegrityError, "Graph/list node mismatch"):
            self._check_graph(graph)

    def test_external_reference_cannot_be_used_as_loaded_graph_proof(self):
        graph = deepcopy(records(packet())["risk-graph"])
        graph["nodes"].append({
            "nodeId": "NODE-UNLOADED-CORRECTION", "nodeType": "correction",
            "label": "An external ID is not loaded canonical proof",
            "source": {"kind": "artifact", "reference": packet()["externalReferences"][2]},
        })
        with self.assertRaisesRegex(ReferenceIntegrityError, "Unresolved artifact reference"):
            self._check_graph(graph)

    def test_no_private_network_requirement_is_introduced_in_v2_verifier(self):
        value = scenario()
        self.assertEqual(value["cp01Verifier"]["requiredEvidenceKinds"], ["resource-configuration"])
        self.assertEqual({p["property"] for p in value["cp01Verifier"]["predicates"]}, set(value["desiredStorageConfiguration"]))
        self.assertEqual(len(value["cp01Verifier"]["predicates"]), 4)


class RiskGeneratedConsumerTests(unittest.TestCase):
    def test_frozen_core_schema_generated_outputs_and_consumers_are_byte_identical(self):
        for path, expected in REGISTRY_MANIFEST["frozenCoreFiles"].items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)

    def test_required_python_metadata_without_site_packages_or_any_fallback(self):
        script = (
            "import importlib.util,json,pathlib,sys; "
            "s=importlib.util.spec_from_file_location('consumer',sys.argv[1]); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "p=json.loads(pathlib.Path(sys.argv[3]).read_text(encoding='utf-8')); "
            "m.check_consumers(pathlib.Path(sys.argv[2]),{x['name']:x['value'] for x in p['records']}); "
            "print('Ten generated roots require all inherited metadata, with no site packages.')"
        )
        result = command(
            sys.executable, "-I", "-S", "-c", script,
            str(ROOT / "tests" / "contracts" / "python_risk_consumer.py"),
            str(GENERATED / "python"), str(EXAMPLES / "risk-examples.json"),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_typescript_cross_bundle_assignability_and_required_metadata(self):
        result = command(
            "node", str(ROOT / "contracts" / "node_modules" / "typescript" / "bin" / "tsc"),
            "--project", str(ROOT / "contracts" / "tsconfig.risk.json"),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class RiskRegenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = WORK / f"test-generation-{uuid.uuid4().hex}"
        cls.output = cls.workspace / "generated"
        cls.workspace.mkdir(parents=True)
        result = cls.generate("all")
        if result.returncode:
            shutil.rmtree(cls.workspace)
            raise AssertionError(result.stdout + result.stderr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.workspace)

    @classmethod
    def generate(cls, bundle, *extra):
        return command(
            sys.executable, str(ROOT / "tools" / "contracts" / "generate.py"),
            "--bundle", bundle, "--output-dir", str(cls.output), *extra,
        )

    def test_all_eight_outputs_regenerate_byte_stably(self):
        result = self.generate("all", "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for bundle in REGISTRY_MANIFEST["bundles"]:
            for language in ("python", "typescript"):
                name = bundle[language]
                self.assertEqual((self.output / name).read_bytes(), (GENERATED / name).read_bytes(), name)

    def test_drift_in_each_new_bundle_is_detected_in_isolation(self):
        for bundle in REGISTRY_MANIFEST["bundles"]:
            if bundle["name"] == "core":
                continue
            target = self.output / bundle["typescript"]
            original = target.read_bytes()
            try:
                target.write_bytes(original + b"\n")
                result = self.generate(bundle["name"], "--check")
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("Generated type drift", result.stderr)
                self.assertEqual(target.read_bytes(), original + b"\n")
            finally:
                target.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
