from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from itertools import product
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

import bootstrap  # noqa: F401
from fixtures import AS_OF, evaluate_arguments, fixture_input, link, refresh, unicode_fixture_input
from engines.drift import evaluate_cp01, project_coverage, reduce_coverage
from engines.drift.evaluator import _source_state, _time
from jsonschema import ValidationError
from state.case_store import CaseStore, StoreError, canonical_bytes, seal
from tools.contracts.integrity import ReferenceIntegrityError, semantic_checksum, validate_reference_integrity
from tools.contracts.validate import fragment_validator, validate_contract


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.inputs = fixture_input()

    def evaluate(self, inputs=None, **overrides):
        inputs = inputs or self.inputs
        output = evaluate_cp01(inputs, **evaluate_arguments(**overrides))
        validate_contract(output, "D17")
        self.assertEqual(output["stateChecksum"], semantic_checksum(output))
        validate_reference_integrity(
            [inputs.promise_contract, *([inputs.binding] if inputs.binding else []),
             *([inputs.snapshot] if inputs.snapshot else []),
             *inputs.evidence, *inputs.operations, output],
            {inputs.run["runId"]: inputs.run}, inputs.scenario, inputs.external_references,
        )
        self.assertEqual(output["runMode"], inputs.run["runMode"])
        for evidence in output["evidence"]:
            self.assertEqual(evidence["origin"], "fixture")
        return output

    def test_complete_confirmed_bound_fresh_fixture_is_verified(self):
        result = self.evaluate()
        self.assertEqual(result["status"], "verified")
        self.assertEqual([item["result"] for item in result["predicateResults"]], ["pass"] * 4)
        self.assertIsNone(result["findingId"])
        self.assertEqual(result["verifier"]["checksum"], semantic_checksum(self.inputs.scenario["cp01Verifier"]))

    def test_deterministic_hash_and_inputs_unchanged(self):
        before = deepcopy(self.inputs)
        self.assertEqual(canonical_bytes(self.evaluate()), canonical_bytes(self.evaluate()))
        self.assertEqual(self.inputs, before)

    def test_order_of_evidence_and_observations_does_not_change_hash(self):
        reordered = replace(self.inputs, evidence=tuple(reversed(self.inputs.evidence)),
                            trusted_sources=tuple(reversed(self.inputs.trusted_sources)))
        self.assertEqual(self.evaluate(), self.evaluate(reordered))

    def test_each_explicit_property_mismatch_breaches(self):
        changes = {"publicNetworkAccess": "Disabled", "supportsHttpsTrafficOnly": False,
                   "allowBlobPublicAccess": True, "minimumTlsVersion": "TLS1_1"}
        for key, value in changes.items():
            with self.subTest(property=key):
                inputs = deepcopy(self.inputs)
                inputs.snapshot["observations"][0]["properties"][key] = value
                result = self.evaluate(refresh(inputs))
                self.assertEqual(result["status"], "breached")
                self.assertEqual(sum(item["result"] == "fail" for item in result["predicateResults"]), 1)

    def test_explicit_mismatch_beats_other_unknown_predicate(self):
        self.inputs.snapshot["observations"][0]["properties"].update(
            supportsHttpsTrafficOnly=False, minimumTlsVersion=None)
        self.inputs.snapshot["completeness"] = "partial"
        result = self.evaluate(refresh(self.inputs))
        self.assertEqual(result["status"], "breached")
        self.assertEqual(result["predicateResults"][-1]["result"], "unknown")

    def test_property_cartesian_product_never_fills_missing_or_null(self):
        properties = list(self.inputs.scenario["desiredStorageConfiguration"])
        variants = {
            "publicNetworkAccess": ["Enabled", "Disabled", None, "MISSING"],
            "supportsHttpsTrafficOnly": [True, False, None, "MISSING"],
            "allowBlobPublicAccess": [False, True, None, "MISSING"],
            "minimumTlsVersion": ["TLS1_2", "TLS1_0", None, "MISSING"],
        }
        for values in product(range(4), repeat=4):
            inputs = deepcopy(self.inputs)
            inputs.snapshot["observations"][0]["properties"] = {
                name: variants[name][index] for name, index in zip(properties, values) if index != 3
            }
            with self.subTest(variants=values):
                expected = "breached" if 1 in values else "unknown" if any(v in {2, 3} for v in values) else "verified"
                self.assertEqual(self.evaluate(refresh(inputs))["status"], expected)

    def test_missing_and_null_have_distinct_reasons(self):
        self.inputs.snapshot["observations"][0]["properties"]["supportsHttpsTrafficOnly"] = None
        null = self.evaluate(refresh(self.inputs))
        del self.inputs.snapshot["observations"][0]["properties"]["supportsHttpsTrafficOnly"]
        missing = self.evaluate(refresh(self.inputs))
        self.assertEqual(null["predicateResults"][1]["reasonCode"], "null-property")
        self.assertEqual(missing["predicateResults"][1]["reasonCode"], "missing-property")
        self.assertNotEqual(null["stateChecksum"], missing["stateChecksum"])

    def test_integer_boolean_impersonation_rejected(self):
        for property_name in ("supportsHttpsTrafficOnly", "allowBlobPublicAccess"):
            for value in (0, 1):
                with self.subTest(property=property_name, value=value):
                    inputs = deepcopy(self.inputs)
                    inputs.snapshot["observations"][0]["properties"][property_name] = value
                    with self.assertRaises(ValidationError):
                        self.evaluate(refresh(inputs))

    def test_missing_partial_failed_snapshots_cannot_verify(self):
        for completeness in ("partial", "missing", "failed"):
            with self.subTest(completeness=completeness):
                inputs = deepcopy(self.inputs)
                inputs.snapshot["completeness"] = completeness
                self.assertEqual(self.evaluate(refresh(inputs))["status"], "unknown")
        self.assertEqual(self.evaluate(replace(self.inputs, snapshot=None,
            trusted_sources=tuple(ref for ref in self.inputs.trusted_sources if ref["contractId"] == "E01")))["status"], "unknown")

    def test_missing_observations_and_collection_gaps_are_unknown(self):
        for field, value in (("observations", []), ("collectionErrors", ["provider-unavailable"]),
                             ("missingEvidenceKinds", ["resource-configuration"])):
            inputs = deepcopy(self.inputs)
            inputs.snapshot[field] = value
            self.assertEqual(self.evaluate(refresh(inputs))["status"], "unknown")

    def test_no_binding_does_not_invent_one(self):
        inputs = refresh(replace(self.inputs, binding=None))
        result = self.evaluate(inputs)
        self.assertEqual(result["status"], "unknown")
        self.assertIsNone(result["binding"])

    def test_nonbound_or_gapped_binding_cannot_verify(self):
        for state in ("missing", "stale", "unknown"):
            inputs = deepcopy(self.inputs)
            inputs.binding["bindingState"] = state
            self.assertEqual(self.evaluate(refresh(inputs))["status"], "unknown")
        self.inputs.binding["gaps"] = ["operator-unconfirmed"]
        self.assertEqual(self.evaluate(refresh(self.inputs))["status"], "unknown")

    def test_unconfirmed_promise_never_uses_scripted_confirmation(self):
        for field, value in (("confirmedPromiseIds", []), ("confirmationDecisionId", None), ("status", "draft")):
            inputs = deepcopy(self.inputs)
            inputs.promise_contract[field] = value
            self.assertEqual(self.evaluate(refresh(inputs))["reasonCode"], "promise-unconfirmed")

    def test_expired_prior_proof_is_stale(self):
        result = self.evaluate(as_of="2026-09-12T17:10:00Z")
        self.assertEqual(result["status"], "stale")
        self.assertTrue(result["evidence"])
        self.assertEqual({item["result"] for item in result["predicateResults"]}, {"unknown"})

    def test_age_limit_independent_of_valid_until(self):
        for evidence in self.inputs.evidence:
            evidence["validUntil"] = None
        inputs = refresh(self.inputs)
        self.assertEqual(self.evaluate(inputs, as_of="2026-09-12T17:10:00Z")["status"], "verified")
        self.assertEqual(self.evaluate(inputs, as_of="2026-09-12T17:10:01Z")["status"], "stale")

    def test_stale_flag_does_not_become_fresh(self):
        for evidence in self.inputs.evidence:
            evidence["evidenceState"] = "stale"
        self.assertEqual(self.evaluate(refresh(self.inputs))["status"], "stale")

    def test_fresh_partial_predicates_do_not_hide_expired_prior_proof(self):
        inputs = deepcopy(self.inputs)
        current = inputs.evidence[-1]
        prior = deepcopy(current)
        prior["artifactId"] = "EVIDENCE-PRIOR-HTTPS"
        prior["supportedAssertionIds"] = ["PRED-HTTPS-REQUIRED"]
        prior["evidenceState"] = "stale"
        prior = seal(prior)
        current["supportedAssertionIds"].remove("PRED-HTTPS-REQUIRED")
        evidence_link = {"reference": link("E01", prior, inputs.scenario), "origin": "fixture"}
        inputs.snapshot["evidence"].append(evidence_link)
        inputs.snapshot["observations"][0]["evidence"].append(evidence_link)
        inputs = replace(inputs, evidence=(*inputs.evidence, prior))
        result = self.evaluate(refresh(inputs))
        self.assertEqual(result["status"], "stale")
        self.assertEqual([item["result"] for item in result["predicateResults"]],
                         ["pass", "unknown", "pass", "pass"])

    def test_expired_mismatch_is_not_a_current_breach(self):
        self.inputs.snapshot["observations"][0]["properties"]["supportsHttpsTrafficOnly"] = False
        self.assertEqual(self.evaluate(refresh(self.inputs), as_of="2026-09-12T17:10:01Z")["status"], "unknown")

    def test_fixture_cannot_satisfy_live_or_replay(self):
        for mode in ("live", "replay"):
            inputs = deepcopy(self.inputs)
            for document in (inputs.run, inputs.promise_contract, inputs.binding, inputs.snapshot, *inputs.operations):
                document["runMode"] = mode
            if mode == "replay":
                inputs.run["sourceRunId"] = "RUN-REPLAY-SOURCE"
            result = self.evaluate(refresh(inputs))
            self.assertEqual(result["status"], "unknown")
            self.assertFalse(result["evidence"])

    def test_live_local_is_not_provider_configuration_proof(self):
        inputs = deepcopy(self.inputs)
        for document in (inputs.run, inputs.promise_contract, inputs.binding, inputs.snapshot, *inputs.operations):
            document["runMode"] = "live"
        for evidence in inputs.evidence:
            evidence["origin"] = "live-local"
        self.assertEqual(self.evaluate(refresh(inputs))["status"], "unknown")

    def test_origin_matrix_uses_explicit_synthetic_metadata_not_provider_proof(self):
        # Exercise the pure eligibility seam; no D17 live success is recorded.
        for mode, origin, eligible in (
            ("live", "live-external", True), ("live", "fixture", False),
            ("fixture", "fixture", True), ("replay", "replayed", True),
            ("fixture", "live-external", False), ("live", "replayed", False),
        ):
            inputs = deepcopy(self.inputs)
            inputs.run["runMode"] = mode
            source = deepcopy(inputs.evidence[-1])
            source["origin"] = origin
            source = seal(source)
            inputs = replace(inputs, evidence=(source,),
                trusted_sources=(link("E01", source, inputs.scenario),))
            self.assertEqual(_source_state(inputs, source, _time(AS_OF)) == "eligible", eligible)

    def test_design_delivery_never_receive_runtime_success(self):
        for phase in ("design", "delivery"):
            result = self.evaluate(phase=phase)
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(result["reasonCode"], "unsupported-phase")

    def test_missing_trust_is_unknown_not_structural_authenticity(self):
        self.assertEqual(self.evaluate(replace(self.inputs, trusted_sources=()))["reasonCode"], "untrusted-snapshot")
        only_snapshot = tuple(ref for ref in self.inputs.trusted_sources if ref["contractId"] == "D15")
        result = self.evaluate(replace(self.inputs, trusted_sources=only_snapshot))
        self.assertEqual(result["status"], "unknown")
        self.assertFalse(result["evidence"])

    def test_evidence_ineligible_unknown_partial_missing_failed(self):
        for field, values in {
            "eligibility": ("unknown", "ineligible"),
            "completeness": ("partial", "missing"),
            "evidenceState": ("partial", "missing", "failed"),
        }.items():
            for value in values:
                inputs = deepcopy(self.inputs)
                for evidence in inputs.evidence:
                    evidence[field] = value
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.evaluate(refresh(inputs))["status"], "unknown")

    def test_missing_provenance_rejected(self):
        for field in ("origin", "sourceChecksum", "collector", "observedAt"):
            inputs = deepcopy(self.inputs)
            del inputs.evidence[-1][field]
            with self.subTest(field=field), self.assertRaises((ValidationError, KeyError)):
                self.evaluate(inputs)

    def test_assertion_ids_are_not_inferred_from_a_snapshot(self):
        self.inputs.evidence[-1]["supportedAssertionIds"] = []
        self.assertEqual(self.evaluate(refresh(self.inputs))["status"], "unknown")

    def test_unresolved_and_fabricated_references_rejected(self):
        missing = replace(self.inputs, evidence=self.inputs.evidence[:1])
        with self.assertRaises(ReferenceIntegrityError):
            self.evaluate(missing)
        inputs = deepcopy(self.inputs)
        inputs.snapshot["observations"][0]["evidence"][0]["reference"]["artifact"]["checksum"] = "sha256:" + "0" * 64
        inputs = replace(inputs, snapshot=seal(inputs.snapshot), trusted_sources=())
        with self.assertRaises(ReferenceIntegrityError):
            self.evaluate(inputs)

    def test_trusted_reference_pin_must_match_loaded_record(self):
        inputs = deepcopy(self.inputs)
        inputs.trusted_sources[-1]["artifact"]["checksum"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ReferenceIntegrityError, "Trusted source reference"):
            self.evaluate(inputs)

    def test_input_checksum_tamper_rejected(self):
        self.inputs.snapshot["observations"][0]["properties"]["supportsHttpsTrafficOnly"] = False
        with self.assertRaisesRegex(ReferenceIntegrityError, "checksum"):
            self.evaluate()

    def test_scope_case_run_scenario_and_purpose_mismatch_rejected(self):
        variants = (
            ("caseId", "CASE-OTHER"), ("runId", "RUN-OTHER"), ("purpose", "hero"),
            ("scope", {**self.inputs.run["scope"], "scopeId": "SCOPE-OTHER"}),
            ("scenario", {**self.inputs.snapshot["scenario"], "scenarioHash": "sha256:" + "0" * 64}),
        )
        for field, value in variants:
            inputs = deepcopy(self.inputs)
            inputs.snapshot[field] = value
            with self.subTest(field=field), self.assertRaises(ReferenceIntegrityError):
                self.evaluate(refresh(inputs))

    def test_e01_v1_run_cannot_be_rebound_by_a_v2_link(self):
        inputs = deepcopy(self.inputs)
        inputs.evidence[-1]["runId"] = "RUN-HISTORICAL-V1"
        with self.assertRaisesRegex(ReferenceIntegrityError, "trusted run"):
            self.evaluate(refresh(inputs))
        inputs = deepcopy(self.inputs)
        inputs.run["scenarioId"] = "DEMO-CASE-CLAIMS-V1"
        with self.assertRaises(ReferenceIntegrityError):
            self.evaluate(refresh(inputs))

    def test_wrong_resource_component_and_desired_hash_rejected(self):
        for target, field, value in (
            ("binding", "componentId", "CMP-OTHER"),
            ("binding", "desiredStateChecksum", "sha256:" + "0" * 64),
            ("observation", "resourceId", self.inputs.binding["resourceId"] + "other"),
        ):
            inputs = deepcopy(self.inputs)
            document = inputs.binding if target == "binding" else inputs.snapshot["observations"][0]
            document[field] = value
            with self.subTest(field=field), self.assertRaises(ReferenceIntegrityError):
                self.evaluate(refresh(inputs))

    def test_unacknowledged_baseline_cannot_verify(self):
        for field, value in (("result", "unknown"), ("operation", "seed")):
            inputs = deepcopy(self.inputs)
            inputs.operations[0][field] = value
            with self.assertRaises(ReferenceIntegrityError):
                self.evaluate(refresh(inputs))

    def test_future_or_prebinding_evidence_cannot_verify(self):
        for field, value in (
            ("observedAt", "2026-09-12T17:05:01Z"),
            ("observedAt", "2026-09-12T17:04:59Z"),
            ("retrievedAt", "2026-09-12T17:05:01Z"),
            ("retrievedAt", "2026-09-12T17:04:59Z"),
            ("validUntil", "2026-09-12T17:04:59Z"),
        ):
            inputs = deepcopy(self.inputs)
            for evidence in inputs.evidence:
                evidence[field] = value
            self.assertEqual(self.evaluate(refresh(inputs))["status"], "unknown")

    def test_ambiguous_observations_do_not_silently_choose_one(self):
        other = deepcopy(self.inputs.snapshot["observations"][0])
        other["properties"]["supportsHttpsTrafficOnly"] = False
        self.inputs.snapshot["observations"].append(other)
        result = self.evaluate(refresh(self.inputs))
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["predicateResults"][1]["reasonCode"], "conflicting-observations")

    def test_wrong_clock_revision_or_phase_rejected(self):
        for override in ({"as_of": "2026-09-12T17:05:00"}, {"logical_revision": True},
                         {"logical_revision": -1}, {"phase": "deployment"}):
            with self.assertRaises(ValueError):
                self.evaluate(**override)

    def test_no_runtime_file_or_network_access(self):
        with patch("builtins.open", side_effect=AssertionError("No file I/O")), \
             patch("socket.socket", side_effect=AssertionError("No networking")):
            self.assertEqual(self.evaluate()["status"], "verified")

    def test_output_is_consumable_by_existing_continuity_graph(self):
        from reporting.continuity.graph import build_graph

        self.inputs.snapshot["observations"][0]["properties"]["supportsHttpsTrafficOnly"] = False
        inputs = refresh(self.inputs)
        evaluation = self.evaluate(inputs)
        graph = build_graph(
            run=inputs.run, scenario=inputs.scenario,
            documents=[inputs.promise_contract, inputs.binding, inputs.snapshot,
                       *inputs.evidence, *inputs.operations, evaluation],
            promise_id="CP-01", logical_revision=0, as_of=AS_OF,
            evaluation_id=evaluation["artifactId"],
            external_references=list(inputs.external_references),
        )
        validate_contract(graph, "P06")
        self.assertTrue(any(edge["status"] == "broken" for edge in graph["edges"]))
        evaluation_node = next(node for node in graph["nodes"] if node["nodeType"] == "evaluation")
        self.assertIn("supportsHttpsTrafficOnly", evaluation_node["label"])

    def test_unicode_store_policy_integrity_evaluator_graph_interoperability(self):
        from policy import Policy
        from reporting.continuity.graph import build_graph

        inputs = unicode_fixture_input()
        owned_root = (
            bootstrap.ROOT / ".intent-to-impact" / "spikes" / "ENG-03-01"
            / ("unicode-store-" + uuid4().hex)
        )
        owned_root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, owned_root)
        store = CaseStore(owned_root / "runs")
        run = store.create_run(inputs.run)
        self.assertEqual(run, inputs.run)
        case = store.create_case(run["runId"])
        policy = Policy(
            store.read_run(run["runId"]), scope=run["scope"],
            root_id=run["rootId"], config_id=run["configId"],
            enabled_capabilities=["read-case"],
        )
        entry = policy.system_entry(
            "worker", "SYSTEM-UNICODE-INTEGRATION", capabilities=["read-case"],
        )
        decision = policy.authorize(
            entry, {"capability": "read-case"}, current_run=store.read_run(run["runId"]),
        )
        self.assertTrue(decision.allowed)
        authorization = decision.authorization_context
        validate_contract(authorization, "E08")
        self.assertEqual(authorization["caller"]["callerClass"], "system")
        self.assertEqual(authorization["permittedCapabilities"], ["read-case"])
        self.assertNotIn("humanInitiator", authorization)

        records = [
            inputs.promise_contract, *inputs.evidence, *inputs.operations,
            inputs.binding, inputs.snapshot, authorization,
        ]
        references = {}
        loaded = {}
        for record in records:
            self.assertEqual(record["stateChecksum"], semantic_checksum(record))
            self.assertEqual(record["stateChecksum"], seal(record)["stateChecksum"])
            reference = store.put_artifact(run["runId"], record)
            self.assertEqual(reference["checksum"], record["stateChecksum"])
            references[record["artifactId"]] = reference
            loaded[record["artifactId"]] = store.read_artifact(run["runId"], reference)
            self.assertEqual(loaded[record["artifactId"]], record)
        inputs = replace(
            inputs, run=store.read_run(run["runId"]),
            promise_contract=loaded[inputs.promise_contract["artifactId"]],
            binding=loaded[inputs.binding["artifactId"]],
            snapshot=loaded[inputs.snapshot["artifactId"]],
            evidence=tuple(loaded[item["artifactId"]] for item in inputs.evidence),
            operations=tuple(loaded[item["artifactId"]] for item in inputs.operations),
        )
        evaluation = self.evaluate(inputs)
        self.assertEqual(evaluation["status"], "verified")
        coverage = project_coverage(inputs, evaluation)
        fragment_validator("projections", "CoverageSummary").validate(coverage)
        self.assertEqual(coverage["verifiedCount"], 1)
        graph = build_graph(
            run=inputs.run, scenario=inputs.scenario,
            documents=[*loaded.values(), evaluation], promise_id="CP-01",
            logical_revision=0, as_of=AS_OF, evaluation_id=evaluation["artifactId"],
            external_references=list(inputs.external_references),
        )
        validate_contract(graph, "P06")
        self.assertTrue(any(
            edge["relation"] == "evaluates" and edge["status"] == "supported"
            for edge in graph["edges"]
        ))
        for record in (evaluation, graph):
            reference = store.put_artifact(run["runId"], record)
            self.assertEqual(reference["checksum"], record["stateChecksum"])
            references[record["artifactId"]] = reference
        case["sections"] = {artifact_id.lower(): reference for artifact_id, reference in references.items()}
        committed = store.commit(run["runId"], 0, case)
        restarted = CaseStore(store.root)
        self.assertEqual(restarted.read_case(run["runId"]), committed)
        self.assertEqual(committed["stateChecksum"], semantic_checksum(committed))
        restored = [
            restarted.read_artifact(run["runId"], reference)
            for reference in committed["sections"].values()
        ]
        self.assertEqual(len(restored), len(records) + 2)
        for record in restored:
            self.assertEqual(record["scope"], run["scope"])
            self.assertEqual(record["stateChecksum"], semantic_checksum(record))
            self.assertEqual(record["stateChecksum"], seal(record)["stateChecksum"])
        resource = inputs.binding["resourceId"]
        self.assertIn("/resourceGroups/rg-caf\u00e9-\u6f22/", resource)
        self.assertEqual(run["scope"]["resourceIds"], [resource])
        self.assertEqual(inputs.operations[0]["resourceIds"], [resource])
        self.assertEqual(inputs.snapshot["observations"][0]["resourceId"], resource)
        validate_reference_integrity(
            restored, {run["runId"]: restarted.read_run(run["runId"])},
            inputs.scenario, inputs.external_references,
        )

        wrong_reference = {**references[evaluation["artifactId"]], "artifactId": "ART-TAMPERED"}
        with self.assertRaisesRegex(StoreError, "reference"):
            restarted.read_artifact(run["runId"], wrong_reference)
        tampered = deepcopy(inputs)
        tampered.snapshot["observations"][0]["properties"]["supportsHttpsTrafficOnly"] = False
        with self.assertRaisesRegex(ReferenceIntegrityError, "checksum"):
            self.evaluate(tampered)
        tampered = deepcopy(evaluation)
        tampered["runtimeSnapshot"]["artifact"]["checksum"] = "sha256:" + "0" * 64
        tampered = seal(tampered)
        with self.assertRaisesRegex(ReferenceIntegrityError, "Reference checksum"):
            validate_reference_integrity(
                [*loaded.values(), tampered], {run["runId"]: run},
                inputs.scenario, inputs.external_references,
            )


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.inputs = fixture_input()

    def test_all_eight_unknowns_remain_in_denominator(self):
        coverage = project_coverage(self.inputs, None)
        self.assertEqual(coverage["applicableCount"], len(self.inputs.promise_contract["promises"]))
        self.assertEqual(coverage["verifiedCount"], 0)
        self.assertEqual(coverage["assessmentState"], "partial")
        self.assertTrue(all(row["status"] == "unknown" for row in coverage["rows"]))
        self.assertFalse(next(row for row in coverage["rows"] if row["promiseId"] == "CP-05")["confirmed"])

    def test_only_cp01_can_be_verified_by_this_engine(self):
        output = evaluate_cp01(self.inputs, **evaluate_arguments())
        coverage = project_coverage(self.inputs, output)
        fragment_validator("projections", "CoverageSummary").validate(coverage)
        self.assertEqual(coverage["verifiedCount"], 1)
        self.assertEqual(coverage["applicableCount"], 8)
        self.assertTrue(all(row["status"] == "unknown" for row in coverage["rows"][1:]))

    def test_design_success_cannot_increase_runtime_coverage(self):
        output = evaluate_cp01(self.inputs, **evaluate_arguments(phase="design"))
        coverage = project_coverage(self.inputs, output)
        self.assertEqual(coverage["verifiedCount"], 0)
        self.assertTrue(all(row["evaluation"] is None for row in coverage["rows"]))

    def test_arbitrary_schema_valid_success_or_exception_is_not_proof(self):
        output = evaluate_cp01(self.inputs, **evaluate_arguments())
        for changes in (
            {"promiseId": "CP-02"}, {"reasonCode": "approved-exception"},
            {"status": "not-applicable", "notApplicableDecision": {"artifactId": "DECISION-EXCEPTION", "checksum": "sha256:" + "0" * 64}},
        ):
            forged = seal({**output, **changes})
            validate_contract(forged, "D17")
            with self.assertRaises(ReferenceIntegrityError):
                project_coverage(self.inputs, forged)

    def test_current_input_mismatch_rejects_an_old_success(self):
        output = evaluate_cp01(self.inputs, **evaluate_arguments())
        self.inputs.snapshot["observations"][0]["properties"]["supportsHttpsTrafficOnly"] = False
        with self.assertRaises(ReferenceIntegrityError):
            project_coverage(refresh(self.inputs), output)

    def test_reducer_has_no_fixed_seven_or_eight_counts(self):
        rows = project_coverage(self.inputs, None)["rows"]
        reference = link("D17", evaluate_cp01(self.inputs, **evaluate_arguments()), self.inputs.scenario)
        # Reducer inputs represent trusted upstream rows, not invented provider proof.
        for count in range(len(rows) + 1):
            selected = deepcopy(rows[:count])
            for verified in range(count + 1):
                candidate = deepcopy(selected)
                for row in candidate[:verified]:
                    row.update(status="verified", confirmed=True, evaluation=reference)
                result = reduce_coverage(candidate)
                self.assertEqual(result["applicableCount"], count)
                self.assertEqual(result["verifiedCount"], verified)
                if not count:
                    self.assertEqual(result["assessmentState"], "not-assessed")

    def test_approved_not_applicable_excludes_but_never_verifies(self):
        rows = project_coverage(self.inputs, None)["rows"]
        reference = link("D17", evaluate_cp01(self.inputs, **evaluate_arguments()), self.inputs.scenario)
        for row in rows:
            row.update(status="not-applicable", evaluation=reference, reasonCode="trusted-upstream-exclusion")
        result = reduce_coverage(rows)
        self.assertEqual(result["assessmentState"], "not-assessed")
        self.assertEqual(result["applicableCount"], 0)
        self.assertEqual(result["verifiedCount"], 0)

    def test_stale_and_unknown_remain_applicable(self):
        rows = project_coverage(self.inputs, None)["rows"][:2]
        rows[0].update(status="stale",
            evaluation=link("D17", evaluate_cp01(self.inputs, **evaluate_arguments(as_of="2026-09-12T17:10:00Z")), self.inputs.scenario))
        result = reduce_coverage(rows)
        self.assertEqual((result["applicableCount"], result["verifiedCount"]), (2, 0))

    def test_duplicate_unconfirmed_and_unsourced_success_rejected(self):
        rows = project_coverage(self.inputs, None)["rows"]
        with self.assertRaises(ReferenceIntegrityError):
            reduce_coverage([rows[0], rows[0]])
        rows[0]["status"] = "verified"
        with self.assertRaises(ReferenceIntegrityError):
            reduce_coverage(rows)
        rows[0]["evaluation"] = link("D17", evaluate_cp01(self.inputs, **evaluate_arguments()), self.inputs.scenario)
        rows[0]["confirmed"] = False
        with self.assertRaises(ReferenceIntegrityError):
            reduce_coverage(rows)


if __name__ == "__main__":
    unittest.main()
