"""Schema-2/V3 fixture and declared-proof-source tests, not a runtime evaluator."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from jsonschema import ValidationError
from tools.contracts.integrity import ReferenceIntegrityError, semantic_checksum
from tools.contracts.nsp_integrity import (
    assert_established_boundary_sources, validate_v3_reference_integrity, validate_v3_scenario,
)
from tools.contracts.registry_support import verify_historical_artifacts, verify_local_schema_references
from tools.contracts.validate import (
    BUNDLES, REGISTRY_MANIFEST, REGISTERED_CONTRACTS, VERSION_CONTRACTS, VERSION_REGISTRIES,
    fragment_validator, identify_contract, validate_contract, validator,
)
from tools.contracts.write_nsp_examples import build_examples

FOLDER = ROOT / "contracts" / "examples" / "2.0.0"
OUTPUT = ROOT / "contracts" / "generated" / "2.0.0"
WORK = ROOT / ".intent-to-impact" / "spikes" / "FND-01-03" / "LOCAL-09"


def scenario():
    return json.loads((ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V3.json").read_text(encoding="utf-8"))


def packet():
    return json.loads((FOLDER / "nsp-examples.json").read_text(encoding="utf-8"))


def values(p):
    return {item["name"]: item["value"] for item in p["records"]}


def seal(value):
    value["stateChecksum"] = semantic_checksum(value)
    return value


def check(p, *, require_live=False, extra_runs=None):
    validate_v3_reference_integrity(
        values(p).values(), {p["runManifest"]["runId"]: p["runManifest"], **(extra_runs or {})},
        scenario(), p["externalReferences"], require_live=require_live, as_of=p["asOf"],
    )


def verified_fixture_claim(p):
    records = values(p)
    source = records["desired-snapshot"]
    claim = deepcopy(records["desired-evaluation"])
    claim.update(artifactId="ART-VERIFIED-TEST-V3", evaluationId="EVALUATION-VERIFIED-TEST-V3", status="verified", reasonCode="fixture-shape-only")
    claim["predicateResults"] = [
        {"predicateId": name, "result": "pass", "reasonCode": "fixture-shape-only", "evidence": deepcopy(claim["evidence"])}
        for name in scenario()["cp01Verifier"]["assertionIds"]
    ]
    claim["boundaryEvidence"] = {
        "binding": deepcopy(claim["binding"]), "snapshot": deepcopy(claim["runtimeSnapshot"]),
        "observation": deepcopy(source["observation"]),
    }
    seal(claim)
    p["records"].append({"name": "verified-test", "contractId": "D17", "schemaVersion": "2.0.0", "value": claim})
    return claim


class VersionSelectionTests(unittest.TestCase):
    def test_legacy_defaults_and_explicit_successor_selection(self):
        self.assertEqual(len(REGISTERED_CONTRACTS), 26)
        self.assertEqual(len(VERSION_CONTRACTS["2.0.0"]), 17)
        value = values(packet())["desired-snapshot"]
        validate_contract(value, "D15", schema_version="2.0.0")
        with self.assertRaises(ValidationError):
            validate_contract(value, "D15")
        with self.assertRaisesRegex(ValueError, "explicit selection"):
            identify_contract(value)
        self.assertEqual(identify_contract(value, schema_version="2.0.0"), "D15")
        with self.assertRaises(ValueError):
            validator("D22", schema_version="2.0.0")
        validate_contract(packet()["runManifest"], "D22")

    def test_unknown_versions_and_scenarios_fail_closed(self):
        for version in ("3.0.0", "2.1.0", "latest", ""):
            with self.subTest(version=version), self.assertRaises(ValueError):
                validate_contract(values(packet())["desired-snapshot"], "D15", schema_version=version)
        for field, bad in (("scenarioId", "DEMO-CASE-CLAIMS-V2"), ("scenarioVersion", "2.0.0"), ("scenarioHash", "sha256:" + "0" * 64)):
            p = packet()
            record = values(p)["desired-snapshot"]
            record["scenario"][field] = bad
            seal(record)
            with self.subTest(field=field), self.assertRaises((ValidationError, ReferenceIntegrityError)):
                check(p)

    def test_v2_evaluation_and_evidence_cannot_be_rebound_to_v3(self):
        old = json.loads((ROOT / "contracts" / "examples" / "1.0.0" / "risk-examples.json").read_text(encoding="utf-8"))
        old_values = {item["name"]: item["value"] for item in old["records"]}
        old_eval = deepcopy(old_values["risk-evaluation"])
        with self.assertRaises(ValidationError):
            validate_contract(old_eval, "D17", schema_version="2.0.0")
        old_eval["scenario"]["scenarioId"] = "DEMO-CASE-CLAIMS-V3"
        seal(old_eval)
        p = packet()
        p["records"].append({"name": "old-evaluation", "contractId": "D17", "schemaVersion": "1.0.0", "value": old_eval})
        with self.assertRaisesRegex(ReferenceIntegrityError, "legacy domain/evaluation"):
            check(p, extra_runs={old["runManifest"]["runId"]: old["runManifest"]})
        p = packet()
        p["records"].append({"name": "old-evidence", "contractId": "E01", "schemaVersion": "1.0.0", "value": old_values["evidence-breach"]})
        with self.assertRaisesRegex(ReferenceIntegrityError, "not bound to the V3"):
            check(p, extra_runs={old["runManifest"]["runId"]: old["runManifest"]})

    def test_reference_target_version_and_checksum_are_binding(self):
        for field, replacement in (("schemaVersion", "1.0.0"), ("checksum", "sha256:" + "2" * 64)):
            p = packet()
            snapshot = values(p)["desired-snapshot"]
            if field == "checksum":
                snapshot["binding"]["artifact"][field] = replacement
            else:
                snapshot["binding"][field] = replacement
            seal(snapshot)
            with self.subTest(field=field), self.assertRaises((ValidationError, ReferenceIntegrityError)):
                check(p)
        p = packet()
        snapshot = values(p)["desired-snapshot"]
        snapshot["evidence"][0]["reference"]["schemaVersion"] = "2.0.0"
        seal(snapshot)
        with self.assertRaises(ValidationError):
            check(p)

    def test_schema_and_scenario_versions_and_hashes_are_distinct(self):
        value = scenario()
        validate_v3_scenario(value)
        self.assertEqual(value["schemaVersion"], "2.0.0")
        self.assertEqual(value["scenarioVersion"], "3.0.0")
        self.assertEqual(value["desiredStorageConfiguration"]["publicNetworkAccess"], "SecuredByPerimeter")
        self.assertEqual(value["desiredNspConfiguration"]["accessMode"], "Enforced")
        self.assertEqual(value["desiredNspConfiguration"]["inboundAccessRules"], [])
        self.assertEqual(value["desiredNspConfiguration"]["outboundAccessRules"], [])
        self.assertEqual(len({row["promiseId"] for row in value["promises"]}), 8)
        self.assertIsNone(value["rpoMinutes"])
        self.assertEqual(value["scriptedRpoAnswerMinutes"], 15)
        self.assertEqual([row["monthlyEstimateUsd"] for row in value["candidates"]], [6000, 7200])
        self.assertEqual(value["monthlyBudgetUsd"], 8000)
        self.assertIsNone(value["candidates"][0]["regionalRecoveryProfile"])
        self.assertTrue(all(item is None for item in value["operatorBinding"].values()))
        self.assertIsNone(value["seedProposal"])
        self.assertEqual(value["restorationAuthorization"], "not-authorized")

    def test_schema_sources_are_local_registered_and_never_fetch_network_refs(self):
        source = ROOT / "contracts" / "schemas" / "2.0.0" / "envelope.schema.json"
        verify_local_schema_references(source)
        for reference in ("https://example.invalid/remote.json", "file:///C:/outside.json", "../../../../outside.json"):
            with self.subTest(reference=reference):
                with patch("tools.contracts.registry_support.registries", return_value=VERSION_REGISTRIES), patch.object(Path, "read_text", return_value=json.dumps({"$ref": reference})):
                    with self.assertRaises(ValueError):
                        verify_local_schema_references(source)


class NspObservationTests(unittest.TestCase):
    def setUp(self):
        self.p = packet()
        self.records = values(self.p)
        self.observation = deepcopy(self.records["desired-snapshot"]["observation"])
        self.resources = self.records["binding-established-fixture"]["resources"]

    def test_all_new_fixtures_validate_without_inventing_live_proof(self):
        check(self.p)
        self.assertEqual(self.p["exampleOrigin"], "fixture")
        self.assertEqual(self.p, build_examples())
        self.assertNotIn("verified", [row["value"].get("status") for row in self.p["records"] if row["contractId"] == "D17"])
        for item in self.p["records"]:
            validate_contract(item["value"], item["contractId"], schema_version=item["schemaVersion"])

    def test_published_negative_vectors_reject_without_zero_or_version_fallbacks(self):
        cases = json.loads((FOLDER / "negative-cases.json").read_text(encoding="utf-8"))
        self.assertEqual(cases["exampleOrigin"], "fixture")
        for case in cases["cases"]:
            value = deepcopy(self.records["desired-snapshot"])
            target = value
            for key in case["path"][:-1]:
                target = target[key]
            if case.get("delete"):
                del target[case["path"][-1]]
            else:
                target[case["path"][-1]] = case["value"]
            with self.subTest(case=case["name"]), self.assertRaises((ValidationError, ReferenceIntegrityError)):
                if case["validation"] == "schema":
                    validate_contract(value, "D15", schema_version="2.0.0")
                else:
                    assert_established_boundary_sources(value["observation"], self.resources)

    def test_complete_declared_sources_are_representable_but_not_automatically_evaluated(self):
        assert_established_boundary_sources(self.observation, self.resources)
        self.assertEqual(self.records["desired-evaluation"]["status"], "unknown")

    def test_secured_by_perimeter_string_alone_cannot_claim_verified_boundary(self):
        snapshot = self.records["unknown-snapshot"]
        self.assertEqual(snapshot["observation"]["storage"]["value"]["publicNetworkAccess"], "SecuredByPerimeter")
        validate_contract(snapshot, "D15", schema_version="2.0.0")
        with self.assertRaises(ValidationError):
            assert_established_boundary_sources(snapshot["observation"], self.resources)
        claim = deepcopy(self.records["unknown-evaluation"])
        claim["status"] = "verified"
        with self.assertRaises(ValidationError):
            validate_contract(claim, "D17", schema_version="2.0.0")

    def test_missing_partial_failed_stale_and_null_members_never_qualify(self):
        for member in ("storage", "perimeter", "profile", "association", "configuration"):
            for state in ("missing", "partial", "failed", "stale"):
                observed = deepcopy(self.observation)
                observed[member]["observationState"] = state
                if state == "missing":
                    observed[member].update(value=None, observedAt=None)
                with self.subTest(member=member, state=state), self.assertRaises(ValidationError):
                    assert_established_boundary_sources(observed, self.resources)
            observed = deepcopy(self.observation)
            observed[member]["value"] = None
            with self.assertRaises(ValidationError):
                assert_established_boundary_sources(observed, self.resources)
            observed = deepcopy(self.observation)
            del observed[member]
            with self.assertRaises(ValidationError):
                assert_established_boundary_sources(observed, self.resources)

    def test_missing_rule_collections_do_not_default_to_zero(self):
        for member in ("profileAccessRules", "effectiveAccessRules"):
            for state in ("missing", "partial", "failed", "stale"):
                observed = deepcopy(self.observation)
                observed[member]["collectionState"] = state
                observed[member]["items"] = None if state == "missing" else []
                with self.subTest(member=member, state=state), self.assertRaises(ValidationError):
                    assert_established_boundary_sources(observed, self.resources)
            for bad in (None, 0):
                observed = deepcopy(self.observation)
                observed[member]["items"] = bad
                with self.assertRaises(ValidationError):
                    assert_established_boundary_sources(observed, self.resources)
            observed = deepcopy(self.observation)
            del observed[member]["items"]
            with self.assertRaises(ValidationError):
                assert_established_boundary_sources(observed, self.resources)
            observed = deepcopy(self.observation)
            observed[member]["nextLink"] = "https://example.invalid/next-page"
            with self.assertRaises(ValidationError):
                assert_established_boundary_sources(observed, self.resources)

    def test_any_external_rule_in_either_source_or_direction_disqualifies_the_claim(self):
        for source in ("profileAccessRules", "effectiveAccessRules"):
            for direction in ("Inbound", "Outbound", None):
                observed = deepcopy(self.observation)
                observed[source]["items"] = [{"name": "external-rule-fixture", "direction": direction}]
                fragment_validator("nsp", "NspObservationSet", schema_version="2.0.0").validate(observed)
                with self.subTest(source=source, direction=direction), self.assertRaises(ValidationError):
                    assert_established_boundary_sources(observed, self.resources)

    def test_transition_learning_audit_and_null_modes_are_observable_but_not_enforced(self):
        for member in ("association", "configuration"):
            for mode in ("Transition", "Learning", "Audit", None):
                observed = deepcopy(self.observation)
                observed[member]["value"]["accessMode"] = mode
                fragment_validator("nsp", "NspObservationSet", schema_version="2.0.0").validate(observed)
                with self.subTest(member=member, mode=mode), self.assertRaises(ValidationError):
                    assert_established_boundary_sources(observed, self.resources)

    def test_unsafe_storage_flags_and_unapproved_profile_do_not_qualify(self):
        changes = {
            "publicNetworkAccess": "Enabled", "supportsHttpsTrafficOnly": False,
            "allowBlobPublicAccess": True, "allowSharedKeyAccess": True, "minimumTlsVersion": "TLS1_0",
            "skuName": "Standard_GRS", "accessTier": "Cool", "isHnsEnabled": True,
            "networkDefaultAction": "Allow", "networkBypass": "AzureServices",
        }
        for field, value in changes.items():
            observed = deepcopy(self.observation)
            observed["storage"]["value"][field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                assert_established_boundary_sources(observed, self.resources)

    def test_wrong_targets_profiles_names_guids_and_versions_fail_relationship_checks(self):
        changes = (
            ("association", "privateLinkResourceId", self.resources["storageId"].replace("claimsfixturev3", "anotherfixture")),
            ("association", "profileId", self.resources["profileId"].replace("profilefixture", "otherprofile")),
            ("configuration", "perimeterId", self.resources["perimeterId"].replace("perimeterfixture", "otherperimeter")),
            ("configuration", "perimeterGuid", "22222222-2222-2222-2222-222222222222"),
            ("configuration", "profileName", "otherprofile"),
            ("configuration", "associationName", "otherassociation"),
            ("configuration", "accessRulesVersion", "0"),
            ("profile", "name", "not-the-observed-id"),
        )
        for member, field, value in changes:
            observed = deepcopy(self.observation)
            observed[member]["value"][field] = value
            with self.subTest(member=member, field=field), self.assertRaises(ReferenceIntegrityError):
                assert_established_boundary_sources(observed, self.resources)
        for collection in ("profileAccessRules", "effectiveAccessRules"):
            observed = deepcopy(self.observation)
            observed[collection]["accessRulesVersion"] = "0"
            with self.assertRaises(ReferenceIntegrityError):
                assert_established_boundary_sources(observed, self.resources)

    def test_pending_failed_or_issue_bearing_effective_configuration_is_not_established(self):
        for field, value in (
            ("provisioningState", "Creating"), ("provisioningState", "Failed"),
            ("provisioningState", None), ("provisioningIssues", None),
            ("provisioningIssues", [{"name": "PropagationFailure", "issueType": "ConfigurationPropagationFailure", "severity": "Error"}]),
            ("accessRulesVersion", None),
        ):
            observed = deepcopy(self.observation)
            observed["configuration"]["value"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                assert_established_boundary_sources(observed, self.resources)

    def test_unknown_binding_cannot_be_used_as_established_resources(self):
        unknown = self.records["binding-unknown"]
        validate_contract(unknown, "D14", schema_version="2.0.0")
        with self.assertRaises(ValidationError):
            assert_established_boundary_sources(self.observation, unknown["resources"])
        changed = deepcopy(unknown)
        changed["bindingState"] = "bound"
        with self.assertRaises(ValidationError):
            validate_contract(changed, "D14", schema_version="2.0.0")

    def test_wrong_observation_source_ids_and_unsupported_states_are_rejected(self):
        p = packet()
        source = values(p)["desired-snapshot"]
        source["observation"]["profile"]["value"]["id"] = self.resources["profileId"].replace("profilefixture", "otherprofile")
        seal(source)
        with self.assertRaisesRegex(ReferenceIntegrityError, "source profile ID mismatch"):
            check(p)
        for field, bad in (("completeness", "not-run"), ("runMode", "demo")):
            value = deepcopy(self.records["desired-snapshot"])
            value[field] = bad
            with self.assertRaises(ValidationError):
                validate_contract(value, "D15", schema_version="2.0.0")

    def test_verified_fixture_claim_requires_source_equality_and_cannot_be_live(self):
        claim = verified_fixture_claim(self.p)
        check(self.p)
        with self.assertRaisesRegex(ReferenceIntegrityError, "not live proof"):
            check(self.p, require_live=True)
        claim["boundaryEvidence"]["observation"]["profile"]["value"]["accessRulesVersion"] = "9"
        seal(claim)
        with self.assertRaisesRegex(ReferenceIntegrityError, "differs from its source"):
            check(self.p)

    def test_replay_keeps_original_sources_and_is_never_live_proof(self):
        claim = verified_fixture_claim(self.p)
        original = self.p["runManifest"]
        replay = deepcopy(original)
        replay.update(runId="RUN-REPLAY-NSP-V3", runMode="replay", sourceRunId=original["runId"])
        seal(replay)
        claim.update(runId=replay["runId"], runMode="replay")
        seal(claim)
        check(self.p, extra_runs={replay["runId"]: replay})
        with self.assertRaisesRegex(ReferenceIntegrityError, "not live proof"):
            check(self.p, require_live=True, extra_runs={replay["runId"]: replay})

    def test_source_origin_and_freshness_cannot_be_relabelled(self):
        claim = verified_fixture_claim(self.p)
        claim["evidence"][0]["origin"] = "live-external"
        seal(claim)
        with self.assertRaisesRegex(ReferenceIntegrityError, "origin does not match"):
            check(self.p)
        p = packet()
        verified_fixture_claim(p)
        p["asOf"] = "2026-09-13T02:10:00Z"
        with self.assertRaisesRegex(ReferenceIntegrityError, "stale|freshness|expired"):
            check(p)

    def test_missing_declared_assertion_does_not_qualify_a_verified_claim(self):
        claim = verified_fixture_claim(self.p)
        claim["predicateResults"].pop()
        seal(claim)
        with self.assertRaisesRegex(ReferenceIntegrityError, "omits a declared"):
            check(self.p)


class NspDesignGraphTests(unittest.TestCase):
    def test_successor_approval_keeps_the_accepted_human_event_scenario_guard(self):
        from tools.contracts.design_integrity import assert_current_approval_binding

        p = packet()
        approval = deepcopy(values(p)["approval-pending"])
        human = {"kind": "human", "actorId": "demo-human", "identityAssurance": "local-demo"}
        event = {
            "schemaVersion": "1.0.0", "artifactType": "human-attention-event", "artifactId": "ART-HUMAN-V3-TEST",
            "runId": approval["runId"], "caseId": approval["caseId"], "scope": deepcopy(approval["scope"]),
            "caseRevisionAtWrite": 0, "createdAt": p["asOf"], "updatedAt": p["asOf"],
            "derivedFrom": {}, "scenario": deepcopy(p["scenario"]), "runMode": "fixture", "purpose": "test",
            "eventId": "EVENT-HUMAN-V3-TEST", "attentionId": "ATTENTION-HUMAN-V3-TEST", "stepId": "STEP-HUMAN-V3-TEST",
            "questionId": None, "decisionId": "DECISION-HUMAN-V3-TEST", "activityClass": "product-workflow",
            "actionId": approval["binding"]["actionId"], "attentionKind": "approved", "actor": human,
            "occurredAt": p["asOf"], "durationSeconds": None, "correlationId": "CORRELATION-HUMAN-V3-TEST",
            "sourceEvent": {"contractId": "E04", "artifact": {"artifactId": "EVENT-SOURCE-FIXTURE", "checksum": "sha256:" + "0" * 64}, "scenario": deepcopy(p["scenario"])},
        }
        seal(event)
        approval.update(
            status="approved", actor=human, decisionId=event["decisionId"], decidedAt=p["asOf"],
            attentionEvent={"contractId": "E05", "artifact": {"artifactId": event["artifactId"], "checksum": event["stateChecksum"]}, "scenario": deepcopy(p["scenario"])},
        )
        seal(approval)
        assert_current_approval_binding(approval, approval["binding"], p["asOf"], attention_event=event, schema_version="2.0.0")
        with self.assertRaises(ValidationError):
            assert_current_approval_binding(approval, approval["binding"], p["asOf"], attention_event=event)
        approval["attentionEvent"]["scenario"]["scenarioHash"] = "sha256:" + "5" * 64
        seal(approval)
        with self.assertRaisesRegex(ReferenceIntegrityError, "reference scenario mismatch"):
            assert_current_approval_binding(approval, approval["binding"], p["asOf"], attention_event=event, schema_version="2.0.0")

    def test_design_family_is_explicit_v3_and_rpo_still_requires_confirmation(self):
        p = packet()
        records = values(p)
        self.assertEqual({row["contractId"] for row in p["records"] if row["schemaVersion"] == "2.0.0"}, set(VERSION_CONTRACTS["2.0.0"]) - {"SCENARIO-V3"})
        proposal = records["architecture-proposal"]
        self.assertEqual([option["catalogFacts"]["monthlyEstimateUsd"] for option in proposal["options"]], [6000, 7200])
        self.assertEqual({component["kind"] for component in proposal["options"][0]["components"]}, {"storage", "perimeter", "profile", "association"})
        unknown = deepcopy(records["requirements-unknown"])
        unknown["status"] = "confirmed"
        with self.assertRaises(ValidationError):
            validate_contract(unknown, "D02", schema_version="2.0.0")
        approval = deepcopy(records["approval-pending"])
        approval["actor"] = {"kind": "agent", "actorId": "AGENT-NOT-HUMAN"}
        with self.assertRaises(ValidationError):
            validate_contract(approval, "D07", schema_version="2.0.0")
        self.assertIsNone(records["adr-proposed"]["decisionReceipt"])
        self.assertEqual(records["generation-draft"]["status"], "draft")

    def test_graph_cannot_invent_missing_members_or_mismatched_relationships(self):
        for scene in ("unknown", "pending"):
            p = packet()
            graph = values(p)[f"{scene}-graph"]
            edge = next(edge for edge in graph["edges"] if edge["support"]["kind"] == "gap")
            edge["status"] = "supported"
            seal(graph)
            subset = [row["value"] for row in p["records"] if not row["contractId"].startswith("P")] + [graph]
            with self.assertRaisesRegex(ReferenceIntegrityError, "cannot imply proof"):
                validate_v3_reference_integrity(subset, {p["runManifest"]["runId"]: p["runManifest"]}, scenario(), p["externalReferences"])
        p = packet()
        graph = values(p)["desired-graph"]
        edge = next(edge for edge in graph["edges"] if edge["support"]["kind"] == "nsp-relationship")
        edge["support"]["toMember"] = "perimeter"
        seal(graph)
        subset = [row["value"] for row in p["records"] if not row["contractId"].startswith("P")] + [graph]
        with self.assertRaisesRegex(ReferenceIntegrityError, "endpoint mismatch"):
            validate_v3_reference_integrity(subset, {p["runManifest"]["runId"]: p["runManifest"]}, scenario(), p["externalReferences"])

    def test_accessible_graph_list_and_scoped_ids_are_bound(self):
        p = packet()
        graph = values(p)["desired-graph"]
        graph["listEntries"].pop()
        seal(graph)
        subset = [row["value"] for row in p["records"] if not row["contractId"].startswith("P")] + [graph]
        with self.assertRaisesRegex(ReferenceIntegrityError, "Graph/list node mismatch"):
            validate_v3_reference_integrity(subset, {p["runManifest"]["runId"]: p["runManifest"]}, scenario(), p["externalReferences"])

    def test_graph_edge_scenario_and_embedded_projection_context_cannot_drift(self):
        p = packet()
        graph = values(p)["desired-graph"]
        graph["edges"][0]["support"]["scenario"]["scenarioHash"] = "sha256:" + "4" * 64
        seal(graph)
        subset = [row["value"] for row in p["records"] if not row["contractId"].startswith("P")] + [graph]
        with self.assertRaisesRegex(ReferenceIntegrityError, "Graph edge scenario mismatch"):
            validate_v3_reference_integrity(subset, {p["runManifest"]["runId"]: p["runManifest"]}, scenario(), p["externalReferences"])
        p = packet()
        overview = values(p)["desired-overview"]
        overview["operationsRisk"]["caseId"] = "CASE-OTHER"
        seal(overview["operationsRisk"])
        seal(overview)
        with self.assertRaisesRegex(ReferenceIntegrityError, "Embedded projection caseId mismatch"):
            check(p)


class NspGeneratedTests(unittest.TestCase):
    def test_all_successor_roots_require_canonical_metadata_and_version(self):
        seen = set()
        required = BUNDLES["core"]["definitions"]["CommonEnvelope"]["required"]
        for item in packet()["records"]:
            if item["schemaVersion"] != "2.0.0" or item["contractId"] in seen:
                continue
            seen.add(item["contractId"])
            for field in required:
                value = deepcopy(item["value"])
                del value[field]
                with self.subTest(contract=item["contractId"], field=field), self.assertRaises(ValidationError):
                    validate_contract(value, item["contractId"], schema_version="2.0.0")
        self.assertEqual(len(seen), 16)

    def test_frozen_legacy_bytes_and_v2_hash_are_preserved(self):
        verify_historical_artifacts(VERSION_REGISTRIES["2.0.0"])
        for path, expected in {**REGISTRY_MANIFEST["frozenCoreFiles"], **REGISTRY_MANIFEST["frozenRiskFiles"]}.items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected, path)
        old = json.loads((ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json").read_text(encoding="utf-8"))
        self.assertEqual(old["stateChecksum"], "sha256:a140b136272f077c82dcd1d38e8e2c13b0aa7aea192be2a80112ccc744213e9a")

    def test_python_metadata_uses_schema2_not_inherited_schema1_and_no_site_packages(self):
        script = (
            "import json,pathlib,runpy,sys,typing; r=json.loads(pathlib.Path(sys.argv[1]).read_text()); "
            "base=pathlib.Path(sys.argv[2]); required=set(json.loads(sys.argv[3])); "
            "count=0; "
            "\nfor b in r['bundles']:\n"
            " n=runpy.run_path(str(base/b['python']))\n"
            " for cid,name in b['contracts'].items():\n"
            "  if cid=='SCENARIO-V3': continue\n"
            "  model=n[name]; hints=typing.get_type_hints(model,globalns=n,include_extras=True)\n"
            "  assert required <= model.__required_keys__, name\n"
            "  assert typing.get_args(hints['schemaVersion'])==('2.0.0',), (name,hints['schemaVersion'])\n"
            "  assert hints['runId'] is str and hints['caseRevisionAtWrite'] is int\n"
            "  assert all(hints[k] is not typing.Any for k in required)\n"
            "  count+=1\n"
            "assert count==16\nprint('Sixteen successor roots require schema2 metadata; stdlib-only imports pass.')"
        )
        result = subprocess.run([
            sys.executable, "-I", "-S", "-c", script, str(ROOT / "contracts" / "registry" / "2.0.0.json"),
            str(OUTPUT), json.dumps(BUNDLES["core"]["definitions"]["CommonEnvelope"]["required"]),
        ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_typescript_version_separation_and_required_collections_compile(self):
        result = subprocess.run(["node", str(ROOT / "contracts" / "node_modules" / "typescript" / "bin" / "tsc"), "--project", str(ROOT / "contracts" / "tsconfig.nsp.json")], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_successor_generation_is_stable_and_detects_isolated_drift(self):
        work = WORK / f"test-generation-{uuid.uuid4().hex}"
        output = work / "generated"
        work.mkdir(parents=True)
        args = [
            sys.executable, str(ROOT / "tools" / "contracts" / "generate.py"), "--schema-version", "2.0.0",
            "--bundle", "all", "--output-dir", str(output),
        ]
        try:
            for extra in ([], ["--check"]):
                result = subprocess.run(args + extra, cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for bundle in VERSION_REGISTRIES["2.0.0"]["bundles"]:
                for language in ("python", "typescript"):
                    self.assertEqual((output / bundle[language]).read_bytes(), (OUTPUT / bundle[language]).read_bytes())
            target = output / "python" / "risk.py"
            target.write_bytes(target.read_bytes() + b"\n")
            result = subprocess.run(args + ["--check"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Generated type drift", result.stderr)
        finally:
            shutil.rmtree(work)


if __name__ == "__main__":
    unittest.main()
