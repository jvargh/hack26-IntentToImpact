"""Bounded D02/D04-D09 schema and reference-comparison tests; all records are fixtures."""

from __future__ import annotations

from copy import deepcopy
import hashlib
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
from tools.contracts.design_integrity import (
    artifact_reference, assert_current_approval_binding, assert_current_inputs, validate_design_references,
)
from tools.contracts.integrity import ReferenceIntegrityError, semantic_checksum
from tools.contracts.validate import BUNDLES, REGISTRY_MANIFEST, REGISTERED_CONTRACTS, identify_contract, validate_contract
from tools.contracts.write_design_examples import build_examples

EXAMPLES = ROOT / "contracts" / "examples" / "1.0.0"
GENERATED = ROOT / "contracts" / "generated" / "1.0.0"
WORK = ROOT / ".intent-to-impact" / "spikes" / "FND-01-02"
DESIGN_IDS = {"D02", "D04", "D05", "D06", "D07", "D08", "D09"}


def packet():
    return json.loads((EXAMPLES / "design-examples.json").read_text(encoding="utf-8"))


def records(value):
    return {item["name"]: item["value"] for item in value["records"]}


def scenario():
    return json.loads((ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json").read_text(encoding="utf-8"))


def seal(value):
    value["stateChecksum"] = semantic_checksum(value)
    return value


def check_packet(value):
    validate_design_references(
        records(value).values(), {value["runManifest"]["runId"]: value["runManifest"]}, scenario(),
        current_bindings=value["currentApprovalBindings"], as_of=value["asOf"],
    )


def compare_approval(value, *, approval=None, binding=None, at=None, event=None):
    values = records(value)
    approved = values["approval-approved"]
    assert_current_approval_binding(
        approval if approval is not None else approved,
        binding if binding is not None else value["currentApprovalBindings"][approved["artifactId"]],
        at if at is not None else value["asOf"],
        attention_event=event if event is not None else values["design-approval-attention"],
    )


def command(*arguments):
    return subprocess.run(
        list(arguments), cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"},
    )


class DesignSchemaTests(unittest.TestCase):
    def test_exact_id_mapping_and_positive_fixture_integrity(self):
        expected = {
            "D02": "Requirements", "D04": "ArchitectureProposal", "D05": "ArchitectureModel",
            "D06": "ArchitectureDecisionRecord", "D07": "Approval", "D08": "ReviewGateEvaluation",
            "D09": "GenerationContract",
        }
        for key, name in expected.items():
            self.assertEqual(REGISTERED_CONTRACTS[key], ("design", name))
        self.assertEqual(REGISTERED_CONTRACTS["D03"], ("risk", "CustomerPromiseContract"))
        value = packet()
        self.assertEqual(value["exampleOrigin"], "fixture")
        self.assertEqual(len(value["records"]), 27)
        for item in value["records"]:
            with self.subTest(record=item["name"]):
                validate_contract(item["value"], item["contractId"])
        check_packet(value)

    def test_unknown_rpo_cannot_count_as_confirmed(self):
        values = records(packet())
        unknown = values["requirements-unknown-rpo"]
        self.assertIsNone(unknown["rpoQuestion"]["valueMinutes"])
        self.assertIsNone(unknown["rpoQuestion"]["confirmation"])
        self.assertNotIn("CP-05", values["promises-unknown-rpo"]["confirmedPromiseIds"])
        unknown["status"] = "confirmed"
        with self.assertRaises(ValidationError):
            validate_contract(unknown, "D02")

    def test_explicit_fifteen_answer_requires_matching_human_confirmation(self):
        value = packet()
        question = records(value)["requirements-confirmed-rpo"]["rpoQuestion"]
        self.assertEqual(question["valueMinutes"], 15)
        self.assertEqual(question["confirmation"]["actor"]["actorId"], "demo-human")
        question["confirmation"]["decisionId"] = "DECISION-FABRICATED"
        seal(records(value)["requirements-confirmed-rpo"])
        with self.assertRaisesRegex(ReferenceIntegrityError, "action/decision binding"):
            check_packet(value)

    def test_existing_d03_cannot_claim_unknown_rpo_confirmed_by_checksum_rebinding(self):
        value = packet()
        promises = records(value)["promises-unknown-rpo"]
        promises["confirmedPromiseIds"].append("CP-05")
        promises["status"] = "confirmed"
        seal(promises)
        validate_contract(promises, "D03")
        with self.assertRaisesRegex(ReferenceIntegrityError, "Unknown RPO cannot be confirmed in D03"):
            check_packet(value)

    def test_negative_vectors_reject_invalid_shapes(self):
        values = records(packet())
        negative = json.loads((EXAMPLES / "design-negative-cases.json").read_text(encoding="utf-8"))
        self.assertEqual(negative["exampleOrigin"], "fixture")
        for case in negative["cases"]:
            with self.subTest(case=case["name"]):
                value = deepcopy(values[case["base"]])
                target = value
                for key in case["path"][:-1]:
                    target = target[key]
                if case.get("delete"):
                    del target[case["path"][-1]]
                else:
                    target[case["path"][-1]] = case["value"]
                with self.assertRaises(ValidationError):
                    validate_contract(value, identify_contract(value))

    def test_every_new_root_requires_all_inherited_metadata_and_closed_shapes(self):
        seen = set()
        required = BUNDLES["core"]["definitions"]["CommonEnvelope"]["required"]
        for item in packet()["records"]:
            kind = item["contractId"]
            if kind not in DESIGN_IDS or kind in seen:
                continue
            seen.add(kind)
            for field in required:
                with self.subTest(contract=kind, field=field):
                    value = deepcopy(item["value"])
                    del value[field]
                    with self.assertRaises(ValidationError):
                        validate_contract(value, kind)
            value = deepcopy(item["value"])
            value["untrustedOverride"] = True
            with self.assertRaises(ValidationError):
                validate_contract(value, kind)
        self.assertEqual(seen, DESIGN_IDS)

    def test_six_gates_and_approval_remain_separate(self):
        values = records(packet())
        pending = values["design-review"]
        blocked = values["blocked-checks-approved-snapshot"]
        self.assertEqual(pending["gate"]["effectiveStatus"], "pass-with-warnings")
        self.assertEqual(pending["gate"]["approvalStatus"], "pending")
        self.assertEqual(blocked["gate"]["effectiveStatus"], "blocked")
        self.assertEqual(blocked["gate"]["approvalStatus"], "approved")
        validate_contract(pending, "D08")
        validate_contract(blocked, "D08")
        for gate in ("requirements-ready", "design-ready", "generation-ready", "delivery-ready", "operation-ready", "remediation-ready"):
            value = deepcopy(pending)
            value["gate"]["gateId"] = gate
            validate_contract(value, "D08")
        blocked["gate"]["effectiveStatus"] = "pass"
        with self.assertRaises(ValidationError):
            validate_contract(blocked, "D08")

    def test_catalog_facts_are_separate_from_engine_eligibility(self):
        values = records(packet())
        proposal = values["architecture-proposal"]
        facts = {option["optionId"]: option["catalogFacts"] for option in proposal["options"]}
        self.assertEqual(facts["OPTION-A"]["monthlyEstimateUsd"], 6000)
        self.assertIsNone(facts["OPTION-A"]["regionalRecoveryProfile"])
        self.assertEqual(facts["OPTION-B"]["monthlyEstimateUsd"], 7200)
        self.assertEqual(scenario()["monthlyBudgetUsd"], 8000)
        self.assertEqual(proposal["recommendedOptionId"], "OPTION-A")
        assessment = {item["optionId"]: item for item in values["design-review"]["review"]["optionAssessments"]}
        self.assertEqual(assessment["OPTION-A"]["eligibility"], "ineligible")
        self.assertEqual(assessment["OPTION-A"]["ruleResults"][0]["status"], "fail")
        self.assertEqual(assessment["OPTION-B"]["eligibility"], "eligible")
        self.assertEqual(values["architecture-model"]["recommendedOptionId"], "OPTION-B")
        proposal["options"][0]["eligibility"] = "eligible"
        with self.assertRaises(ValidationError):
            validate_contract(proposal, "D04")

    def test_agent_findings_cannot_be_used_as_approvals(self):
        values = records(packet())
        finding = values["design-review"]["review"]["findings"][1]
        self.assertEqual(finding["source"], "agent")
        with self.assertRaises(ValidationError):
            validate_contract(finding, "D07")
        approval = deepcopy(values["approval-approved"])
        approval["actor"] = finding["actor"]
        with self.assertRaises(ValidationError):
            validate_contract(approval, "D07")

    def test_adr_selection_is_not_an_approval(self):
        values = records(packet())
        self.assertIsNone(values["adr-proposed"]["decisionReceipt"])
        self.assertEqual(values["adr-recorded"]["decisionReceipt"]["selectedOptionId"], "OPTION-B")
        self.assertEqual(values["approval-pending"]["status"], "pending")
        self.assertIsNone(values["approval-pending"]["actor"])
        validate_contract(values["adr-recorded"], "D06")
        with self.assertRaises(ValidationError):
            validate_contract(values["adr-recorded"], "D07")

    def test_generation_paths_are_bounded_non_executable_descriptors(self):
        original = records(packet())["generation-ready"]
        for path in ("../main.bicep", "/main.bicep", r"C:\main.bicep", r"infra\..\main.bicep", "infra/main.bicep.exe", "./main.bicep"):
            with self.subTest(path=path):
                value = deepcopy(original)
                value["outputs"][0]["relativePath"] = path
                with self.assertRaises(ValidationError):
                    validate_contract(value, "D09")
        self.assertEqual(original["renderMode"], "approved-templates-only")
        self.assertNotIn("command", original)

    def test_unique_schema_keys_and_reproducible_fixture_bytes(self):
        def unique(pairs):
            result = {}
            for key, value in pairs:
                self.assertNotIn(key, result)
                result[key] = value
            return result
        path = ROOT / "contracts" / "schemas" / "1.0.0" / "design.schema.json"
        json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
        self.assertEqual(packet(), build_examples())


class ApprovalBindingTests(unittest.TestCase):
    def test_current_explicit_approval_matches_without_authorizing_an_action(self):
        self.assertIsNone(compare_approval(packet()))

    def test_pending_rejected_stale_expired_records_are_not_current_approval(self):
        value = packet()
        for name in ("approval-pending", "approval-rejected", "approval-stale", "approval-expired"):
            with self.subTest(record=name):
                approval = records(value)[name]
                validate_contract(approval, "D07")
                with self.assertRaisesRegex(ReferenceIntegrityError, "not currently approved"):
                    compare_approval(value, approval=approval)

    def test_expired_or_future_approval_fails_even_if_status_still_says_approved(self):
        for at in ("2026-09-12T19:00:00Z", "2026-09-12T20:00:00Z", "2026-09-12T18:19:00Z"):
            with self.subTest(at=at):
                with self.assertRaisesRegex(ReferenceIntegrityError, "expired, not yet decided"):
                    compare_approval(packet(), at=at)

    def test_revision_subject_action_capability_gate_and_hash_mismatches_fail(self):
        value = packet()
        approved = records(value)["approval-approved"]
        expected = value["currentApprovalBindings"][approved["artifactId"]]
        mutations = {
            "expectedRevision": 2,
            "subject": {"artifactId": "ART-DIFFERENT", "checksum": "sha256:" + "1" * 64},
            "actionId": "approve-different-r2",
            "capability": "apply-local-change",
            "gateId": "delivery-ready",
            "boundChecksums": {"scenario": "sha256:" + "2" * 64},
        }
        for field, replacement in mutations.items():
            with self.subTest(field=field):
                binding = deepcopy(expected)
                binding[field] = replacement
                with self.assertRaisesRegex(ReferenceIntegrityError, "current binding mismatch"):
                    compare_approval(value, binding=binding)

    def test_fabricated_missing_or_changed_human_event_cannot_satisfy_binding(self):
        value = packet()
        approval = deepcopy(records(value)["approval-approved"])
        approval["attentionEvent"]["artifact"]["artifactId"] = "ART-FABRICATED-EVENT"
        seal(approval)
        with self.assertRaisesRegex(ReferenceIntegrityError, "Human event reference mismatch"):
            compare_approval(value, approval=approval)
        event = deepcopy(records(value)["design-approval-attention"])
        event["decisionId"] = "DECISION-UNRELATED"
        seal(event)
        with self.assertRaisesRegex(ReferenceIntegrityError, "Human event reference mismatch"):
            compare_approval(value, event=event)
        with self.assertRaises(ValidationError):
            compare_approval(value, event={})

    def test_standalone_approval_rejects_event_link_from_a_different_scenario(self):
        value = packet()
        for field, replacement in (
            ("scenarioId", "DEMO-CASE-OTHER"),
            ("scenarioVersion", "3.0.0"),
            ("scenarioHash", "sha256:" + "0" * 64),
        ):
            with self.subTest(field=field):
                approval = deepcopy(records(value)["approval-approved"])
                approval["attentionEvent"]["scenario"][field] = replacement
                seal(approval)
                with self.assertRaisesRegex(ReferenceIntegrityError, "Human event reference scenario mismatch"):
                    compare_approval(value, approval=approval)

    def test_corrupted_approval_body_cannot_match_valid_looking_binding(self):
        value = packet()
        approval = deepcopy(records(value)["approval-approved"])
        approval["approvalId"] = "APPROVAL-TAMPERED"
        with self.assertRaisesRegex(ReferenceIntegrityError, "Approval body checksum mismatch"):
            compare_approval(value, approval=approval)


class DesignReferenceTests(unittest.TestCase):
    def test_current_inputs_compare_ids_and_hashes_not_model_claims(self):
        value = packet()
        proposal = deepcopy(records(value)["architecture-proposal"])
        expected = value["currentInputReferences"]["architecture-proposal"]
        assert_current_inputs(proposal, expected)
        proposal["requirements"] = {"artifactId": "ART-OLD-REQUIREMENTS", "checksum": "sha256:" + "3" * 64}
        proposal["derivedFrom"]["requirements"] = proposal["requirements"]["checksum"]
        seal(proposal)
        with self.assertRaisesRegex(ReferenceIntegrityError, "stale-input: requirements"):
            assert_current_inputs(proposal, expected)
        proposal = deepcopy(records(value)["architecture-proposal"])
        proposal["derivedFrom"]["requirements"] = "sha256:" + "4" * 64
        with self.assertRaisesRegex(ReferenceIntegrityError, "Input checksum mismatch"):
            assert_current_inputs(proposal, expected)

    def test_unresolved_or_mismatched_model_source_reference_is_rejected(self):
        value = packet()
        model = records(value)["architecture-model"]
        model["sourceProposal"]["checksum"] = "sha256:" + "5" * 64
        model["derivedFrom"]["sourceProposal"] = model["sourceProposal"]["checksum"]
        seal(model)
        with self.assertRaisesRegex(ReferenceIntegrityError, "Reference checksum mismatch"):
            check_packet(value)

    def test_eligible_label_cannot_contradict_reported_mandatory_failure(self):
        value = packet()
        review = records(value)["design-review"]
        review["review"]["optionAssessments"][0]["eligibility"] = "eligible"
        seal(review)
        with self.assertRaisesRegex(ReferenceIntegrityError, "contradicts reported mandatory"):
            check_packet(value)

    def test_generation_ready_needs_caller_supplied_current_comparison_facts(self):
        value = packet()
        with self.assertRaisesRegex(ReferenceIntegrityError, "Current approval comparison facts"):
            validate_design_references(records(value).values(), {value["runManifest"]["runId"]: value["runManifest"]}, scenario())

    def test_generation_cannot_use_blocked_checks_or_another_selected_option(self):
        value = packet()
        values = records(value)
        plan = values["generation-ready"]
        plan["gateEvaluation"] = artifact_reference(values["blocked-checks-approved-snapshot"])
        plan["derivedFrom"]["gateEvaluation"] = plan["gateEvaluation"]["checksum"]
        seal(plan)
        with self.assertRaisesRegex(ReferenceIntegrityError, "unacceptable checks"):
            check_packet(value)
        value = packet()
        plan = records(value)["generation-ready"]
        plan["selectedOptionId"] = "OPTION-A"
        seal(plan)
        with self.assertRaisesRegex(ReferenceIntegrityError, "selection/decision mismatch"):
            check_packet(value)

    def test_generation_cannot_rewrite_approved_input_or_template_hash(self):
        value = packet()
        plan = records(value)["generation-ready"]
        plan["desiredStateChecksum"] = "sha256:" + "6" * 64
        seal(plan)
        with self.assertRaisesRegex(ReferenceIntegrityError, "desired-state checksum mismatch"):
            check_packet(value)
        value = packet()
        plan = records(value)["generation-ready"]
        plan["outputs"][0]["template"]["checksum"] = "sha256:" + "7" * 64
        seal(plan)
        with self.assertRaisesRegex(ReferenceIntegrityError, "not in the pinned plan"):
            check_packet(value)


class DesignGeneratedConsumerTests(unittest.TestCase):
    def test_all_accepted_schema_type_scenario_and_consumer_bytes_are_preserved(self):
        for path, expected in {**REGISTRY_MANIFEST["frozenCoreFiles"], **REGISTRY_MANIFEST["frozenRiskFiles"]}.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)

    def test_python_metadata_and_checksum_dictionary_requirements_without_site_packages(self):
        script = (
            "import json,runpy,sys,typing; n=runpy.run_path(sys.argv[1]); "
            "names=['Requirements','ArchitectureProposal','ArchitectureModel','ArchitectureDecisionRecord','Approval','ReviewGateEvaluation','GenerationContract']; "
            "required=n['CommonEnvelope'].__required_keys__; "
            "assert required==set(json.loads(sys.argv[2])); "
            "assert all(required <= n[name].__required_keys__ for name in names); "
            "assert all(typing.get_type_hints(n[name],globalns=n)['runId'] is str for name in names); "
            "h=typing.get_type_hints(n['ApprovalSubjectBinding'],globalns=n)['boundChecksums']; "
            "assert typing.get_origin(h) is dict and typing.get_args(h)==(str,str); "
            "print('Seven roots preserve required metadata and actual checksum dictionary typing.')"
        )
        result = command(
            sys.executable, "-I", "-S", "-c", script, str(GENERATED / "python" / "design.py"),
            json.dumps(BUNDLES["core"]["definitions"]["CommonEnvelope"]["required"]),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_typescript_consumer_cross_bundle_and_actor_constraints(self):
        result = command("node", str(ROOT / "contracts" / "node_modules" / "typescript" / "bin" / "tsc"), "--project", str(ROOT / "contracts" / "tsconfig.design.json"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class DesignRegenerationTests(unittest.TestCase):
    def test_design_regenerates_stably_and_detects_isolated_byte_drift(self):
        workspace = WORK / f"test-generation-{uuid.uuid4().hex}"
        output = workspace / "generated"
        workspace.mkdir(parents=True)
        arguments = (
            sys.executable, str(ROOT / "tools" / "contracts" / "generate.py"),
            "--bundle", "design", "--output-dir", str(output),
        )
        try:
            generated = command(*arguments)
            self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
            checked = command(*arguments, "--check")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            for name in ("python/design.py", "typescript/design.d.ts"):
                self.assertEqual((output / name).read_bytes(), (GENERATED / name).read_bytes())
            target = output / "python" / "design.py"
            target.write_bytes(target.read_bytes() + b"\n")
            drift = command(*arguments, "--check")
            self.assertEqual(drift.returncode, 1, drift.stdout + drift.stderr)
            self.assertIn("Generated type drift", drift.stderr)
        finally:
            shutil.rmtree(workspace)


if __name__ == "__main__":
    unittest.main()
