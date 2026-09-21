from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from reporting.continuity.graph import build_graph
from tools.contracts.integrity import ReferenceIntegrityError, semantic_checksum
from tools.contracts.validate import validate_contract

ROOT = Path(__file__).resolve().parents[2]


class ContinuityGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        examples = json.loads(
            (ROOT / "contracts" / "examples" / "1.0.0" / "risk-examples.json").read_text()
        )
        self.scenario = json.loads(
            (ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json").read_text()
        )
        self.named = {record["name"]: record["value"] for record in examples["records"]}
        self.documents = list(self.named.values())
        self.run = examples["runManifest"]
        self.external = examples["externalReferences"]

    def graph(self, **overrides):
        arguments = {
            "run": self.run, "scenario": self.scenario, "documents": self.documents,
            "promise_id": "CP-01", "logical_revision": 0,
            "as_of": "2026-09-12T17:05:00Z",
            "evaluation_id": self.named["risk-evaluation"]["artifactId"],
            "external_references": self.external,
        }
        arguments.update(overrides)
        return build_graph(**arguments)

    def test_breach_has_exact_property_and_supported_source_path(self):
        graph = self.graph()
        validate_contract(graph, "P06")
        broken = [edge for edge in graph["edges"] if edge["status"] == "broken"]
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]["toNodeId"], "NODE-PROMISE")
        self.assertEqual(broken[0]["support"]["reference"]["artifact"]["artifactId"],
                         self.named["risk-evaluation"]["artifactId"])
        evaluation = next(node for node in graph["nodes"] if node["nodeId"] == "NODE-EVALUATION")
        self.assertIn("supportsHttpsTrafficOnly", evaluation["label"])
        self.assertEqual(graph["runMode"], "fixture")

    def test_graph_is_deterministic_for_same_snapshot_and_cutoff(self):
        self.assertEqual(self.graph(), self.graph())

    def test_accessible_list_has_exact_same_nodes_and_edges(self):
        graph = self.graph()
        self.assertEqual(
            {node["nodeId"] for node in graph["nodes"]},
            {row["nodeId"] for row in graph["listEntries"]},
        )
        for row in graph["listEntries"]:
            expected = {
                edge["edgeId"] for edge in graph["edges"]
                if row["nodeId"] in (edge["fromNodeId"], edge["toNodeId"])
            }
            self.assertEqual(set(row["relatedEdgeIds"]), expected)

    def test_pending_restoration_does_not_heal_broken_edge(self):
        graph = self.graph(restoration_pending=True)
        self.assertTrue(any(edge["status"] == "broken" for edge in graph["edges"]))
        self.assertTrue(any(edge["status"] == "pending" for edge in graph["edges"]))
        self.assertTrue(any("verification pending" in node["label"] for node in graph["nodes"]))

    def test_verified_fixture_evaluation_maps_to_supported_without_inventing_a_verdict(self):
        def link(contract_id, record):
            return {
                "contractId": contract_id,
                "artifact": {"artifactId": record["artifactId"], "checksum": record["stateChecksum"]},
                "scenario": deepcopy(self.run_identity),
            }

        self.run_identity = {
            key: self.run[key] for key in ("scenarioId", "scenarioVersion", "scenarioHash")
        }
        evidence = {
            "reference": link("E01", self.named["evidence-baseline"]), "origin": "fixture"
        }
        snapshot = deepcopy(self.named["risk-snapshot"])
        snapshot.update(artifactId="ART-SNAPSHOT-HEALTHY-V2", snapshotId="SNAPSHOT-HEALTHY-V2")
        snapshot["observations"][0]["properties"] = deepcopy(self.scenario["desiredStorageConfiguration"])
        snapshot["observations"][0]["evidence"] = [evidence]
        snapshot["evidence"] = [evidence]
        snapshot["stateChecksum"] = semantic_checksum(snapshot)
        evaluation = deepcopy(self.named["risk-evaluation"])
        evaluation.update(
            artifactId="ART-EVALUATION-HEALTHY-V2", evaluationId="EVALUATION-HEALTHY-V2",
            status="verified", reasonCode="fixture-verified", findingId=None,
            runtimeSnapshot=link("D15", snapshot), evidence=[evidence],
        )
        for predicate in evaluation["predicateResults"]:
            predicate.update(result="pass", reasonCode="fixture-matches", evidence=[evidence])
        evaluation["stateChecksum"] = semantic_checksum(evaluation)
        graph = self.graph(
            documents=[*self.documents, snapshot, evaluation],
            evaluation_id=evaluation["artifactId"],
        )
        edge = next(edge for edge in graph["edges"] if edge["relation"] == "evaluates")
        self.assertEqual(edge["status"], "supported")
        self.assertEqual(graph["evidence"][0]["origin"], "fixture")
        self.assertEqual(graph["allowedActions"], [])

    def test_no_evaluation_builds_explicit_gaps_without_fake_proof(self):
        graph = self.graph(documents=[], evaluation_id=None, external_references=[])
        validate_contract(graph, "P06")
        self.assertEqual(graph["evidence"], [])
        self.assertEqual(graph["artifactRefs"], [])
        self.assertTrue(any(node["source"]["kind"] == "gap" for node in graph["nodes"]))
        self.assertFalse(any(edge["status"] == "broken" for edge in graph["edges"]))
        self.assertTrue(graph["blockers"])

    def test_unknown_evaluation_is_not_verified_or_broken(self):
        graph = self.graph(evaluation_id=self.named["unknown-evaluation"]["artifactId"])
        edge = next(edge for edge in graph["edges"] if edge["relation"] == "evaluates")
        self.assertEqual(edge["status"], "gap")
        self.assertTrue(graph["blockers"])

    def test_declared_verified_runtime_requires_backing_references(self):
        unknown = deepcopy(self.named["unknown-evaluation"])
        unknown.update(artifactId="ART-VERIFIED-WITHOUT-PROOF", status="verified")
        unknown["stateChecksum"] = semantic_checksum(unknown)
        # Use only the direct inputs so existing unrelated example references cannot mask the check.
        records = [
            self.named["promise-contract"],
            self.named["unknown-snapshot"],
            self.named["missing-binding"],
            unknown,
        ]
        with self.assertRaisesRegex(ReferenceIntegrityError, "supporting references"):
            self.graph(documents=records, evaluation_id=unknown["artifactId"])

    def test_missing_selected_evaluation_rejected(self):
        with self.assertRaisesRegex(ReferenceIntegrityError, "Selected evaluation"):
            self.graph(evaluation_id="ART-NOT-LOADED")

    def test_unknown_promise_rejected(self):
        with self.assertRaisesRegex(ValueError, "Promise does not exist"):
            self.graph(promise_id="CP-99")

    def test_other_promise_cannot_use_cp01_evaluation(self):
        with self.assertRaisesRegex(ReferenceIntegrityError, "another promise"):
            self.graph(promise_id="CP-02")

    def test_missing_referenced_evidence_rejected(self):
        records = [
            record for record in self.documents
            if record["artifactId"] != self.named["evidence-breach"]["artifactId"]
        ]
        with self.assertRaises(ReferenceIntegrityError):
            self.graph(documents=records)

    def test_tampered_source_checksum_rejected(self):
        self.named["risk-evaluation"]["reasonCode"] = "unapproved-change"
        with self.assertRaisesRegex(ReferenceIntegrityError, "checksum"):
            self.graph()

    def test_fixture_run_cannot_be_relabelled_live(self):
        changed = deepcopy(self.run)
        changed["runMode"] = "live"
        changed["stateChecksum"] = semantic_checksum(changed)
        with self.assertRaises(ReferenceIntegrityError):
            self.graph(run=changed)

    def test_v1_context_is_not_rebound(self):
        changed = deepcopy(self.run)
        changed["scenarioId"] = "DEMO-CASE-CLAIMS-V1"
        changed["stateChecksum"] = semantic_checksum(changed)
        with self.assertRaisesRegex(ReferenceIntegrityError, "scenario"):
            self.graph(run=changed)

    def test_invalid_revision_and_naive_cutoff_rejected(self):
        with self.assertRaises(ValueError):
            self.graph(logical_revision=True)
        with self.assertRaisesRegex(ValueError, "timezone"):
            self.graph(as_of="2026-09-12T17:05:00")
        with self.assertRaisesRegex(ReferenceIntegrityError, "predates"):
            self.graph(as_of="2026-09-12T17:04:00Z")

    def test_pending_flag_requires_existing_runtime_breach(self):
        with self.assertRaises(ValueError):
            self.graph(evaluation_id=None, restoration_pending=True)
        with self.assertRaises(ValueError):
            self.graph(evaluation_id=self.named["unknown-evaluation"]["artifactId"],
                       restoration_pending=True)

    def test_inputs_are_not_mutated_and_no_io_is_performed(self):
        originals = deepcopy((self.run, self.scenario, self.documents, self.external))
        with patch("socket.socket", side_effect=AssertionError("Network forbidden")), \
             patch("subprocess.run", side_effect=AssertionError("Execution forbidden")), \
             patch.object(Path, "write_text", side_effect=AssertionError("Write forbidden")):
            self.graph()
        self.assertEqual((self.run, self.scenario, self.documents, self.external), originals)


if __name__ == "__main__":
    unittest.main()
