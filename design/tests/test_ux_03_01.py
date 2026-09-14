import copy
import unittest

from jsonschema import Draft202012Validator

from validation import (
    DesignValidationError, load, validate_record, validate_review_package,
)


class ReviewRecordTests(unittest.TestCase):
    def setUp(self):
        self.schema = load(r"design\reviews\ux-record.schema.json")
        self.checkpoints = load(r"design\reviews\checkpoint-agendas.v1.json")
        self.decisions = [load(fr"design\decisions\UXD-{n:03}.json") for n in (1, 2)]

    def check(self):
        validate_review_package(self.checkpoints, self.decisions, self.schema)

    def complete_technical_reviews(self, record, actor_type="agent"):
        record["technicalReviews"]["status"] = "complete"
        record["technicalReviews"]["records"] = [
            {"actorType": actor_type, "actorRef": "TEST-ONLY-assigned-reviewer",
             "role": role, "disposition": "approved", "recordedAt": "2026-09-12T21:00:00Z",
             "subjectVersion": "1.0.0", "evidenceRef": f"TEST-ONLY-NOT-REAL-review-{role}"}
            for role in record["technicalReviews"]["requiredRoles"]
        ]

    def gate_candidate(self):
        record = copy.deepcopy(self.checkpoints[0])
        record["gateState"] = "passed"
        record["agendaState"] = "reviewed"
        record["openDecisionRefs"] = []
        record["evidenceRefs"] = ["TEST-ONLY-NOT-REAL-checkpoint-evidence"]
        self.complete_technical_reviews(record)
        record["humanApproval"] = {
            "status": "approved",
            "decisions": [{
                "actorType": "human", "actorRef": "demo-human",
                "purpose": "product-ux-acceptance", "decision": "approved",
                "recordedAt": "2026-09-12T21:00:00Z", "subjectVersion": "1.0.0",
                "evidenceRef": "TEST-ONLY-NOT-REAL-human-confirmation",
            }],
        }
        return record

    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(self.schema)

    def test_six_pending_agendas_and_decision_records_validate(self):
        self.check()

    def test_missing_meaningful_rationale_fails(self):
        del self.decisions[0]["rationale"]
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            self.check()

    def test_unknown_fields_cannot_hide_an_approval(self):
        self.decisions[0]["selfApproved"] = True
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            self.check()

    def test_illustrative_record_cannot_be_approved(self):
        self.decisions[0]["state"] = "approved"
        self.complete_technical_reviews(self.decisions[0])
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            self.check()

    def test_agent_cannot_satisfy_product_human_slot(self):
        record = self.gate_candidate()
        record["humanApproval"]["decisions"][0]["actorType"] = "agent"
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            validate_record(record, self.schema)

    def test_arbitrary_actor_cannot_replace_the_demo_human(self):
        record = self.gate_candidate()
        record["humanApproval"]["decisions"][0]["actorRef"] = "implementation-orchestrator"
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            validate_record(record, self.schema)

    def test_technical_reviews_may_be_agent_or_human(self):
        for actor_type in ("agent", "human"):
            with self.subTest(actor_type=actor_type):
                record = copy.deepcopy(self.decisions[1])
                record["state"] = "approved"
                self.complete_technical_reviews(record, actor_type)
                report = validate_record(record, self.schema)
                self.assertEqual(report["structuralValidation"], "passed")
                self.assertFalse(report["acceptanceEstablished"])

    def test_one_reviewer_can_cover_all_lanes_with_one_product_human(self):
        record = self.gate_candidate()
        report = validate_record(record, self.schema)
        self.assertEqual(report["structuralValidation"], "passed")
        self.assertEqual(len({r["actorRef"] for r in record["technicalReviews"]["records"]}), 1)
        self.assertEqual(len(record["humanApproval"]["decisions"]), 1)
        self.assertFalse(report["acceptanceEstablished"])

    def test_fake_evidence_and_self_claimed_human_identity_cannot_establish_acceptance(self):
        record = self.gate_candidate()
        report = validate_record(record, self.schema)
        self.assertEqual(report["structuralValidation"], "passed")
        self.assertFalse(report["acceptanceEstablished"])
        self.assertEqual(report["evidenceAuthenticity"], "unverified")
        self.assertIn("actual assigned-reviewer evidence", report["acceptanceBlocker"])
        self.assertIn("genuine demo-human", report["acceptanceBlocker"])

    def test_closed_record_requires_mock_and_live_alignment(self):
        record = copy.deepcopy(self.decisions[1])
        record["state"] = "closed"
        self.complete_technical_reviews(record)
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            validate_record(record, self.schema)

    def test_missing_required_technical_lane_evidence_fails(self):
        record = self.gate_candidate()
        record["technicalReviews"]["records"].pop()
        with self.assertRaisesRegex(DesignValidationError, "missing required technical review evidence"):
            validate_record(record, self.schema)

    def test_missing_or_empty_reviewer_evidence_fails(self):
        for evidence in (None, "", "   "):
            with self.subTest(evidence=evidence):
                record = self.gate_candidate()
                review = record["technicalReviews"]["records"][0]
                if evidence is None:
                    del review["evidenceRef"]
                else:
                    review["evidenceRef"] = evidence
                with self.assertRaisesRegex(DesignValidationError, "schema validation"):
                    validate_record(record, self.schema)

    def test_missing_human_evidence_or_decision_fails(self):
        record = self.gate_candidate()
        del record["humanApproval"]["decisions"][0]["evidenceRef"]
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            validate_record(record, self.schema)
        record = self.gate_candidate()
        record["humanApproval"]["decisions"] = []
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            validate_record(record, self.schema)

    def test_unresolved_technical_review_cannot_be_complete(self):
        record = self.gate_candidate()
        record["technicalReviews"]["records"][0]["disposition"] = "changes-requested"
        with self.assertRaisesRegex(DesignValidationError, "unresolved technical review"):
            validate_record(record, self.schema)

    def test_duplicate_lane_review_cannot_replace_a_missing_lane(self):
        record = self.gate_candidate()
        record["technicalReviews"]["records"][-1]["role"] = record["technicalReviews"]["records"][0]["role"]
        with self.assertRaisesRegex(DesignValidationError, "duplicate role"):
            validate_record(record, self.schema)

    def test_pending_ux_decision_cannot_have_completed_technical_reviews(self):
        self.complete_technical_reviews(self.decisions[1])
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            self.check()

    def test_complete_technical_reviews_do_not_replace_product_approval(self):
        record = self.gate_candidate()
        record["humanApproval"] = {"status": "pending", "decisions": []}
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            validate_record(record, self.schema)

    def test_product_approval_cannot_replace_technical_review(self):
        record = self.gate_candidate()
        record["technicalReviews"]["status"] = "pending"
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            validate_record(record, self.schema)

    def test_rejected_product_decision_cannot_approve_checkpoint(self):
        record = self.gate_candidate()
        record["humanApproval"]["decisions"][0]["decision"] = "rejected"
        with self.assertRaisesRegex(DesignValidationError, "rejected human decision"):
            validate_record(record, self.schema)

    def test_no_extra_human_personas_are_required_or_allowed(self):
        record = self.gate_candidate()
        record["humanApproval"]["decisions"].append(copy.deepcopy(record["humanApproval"]["decisions"][0]))
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            validate_record(record, self.schema)

    def test_real_foundation_package_cannot_claim_test_only_reviews(self):
        self.checkpoints[0] = self.gate_candidate()
        with self.assertRaisesRegex(DesignValidationError, "no completed technical review"):
            self.check()

    def test_gate_with_open_findings_or_no_checkpoint_evidence_fails(self):
        for field, value in (("openDecisionRefs", ["UXD-002"]), ("evidenceRefs", [])):
            with self.subTest(field=field):
                record = self.gate_candidate()
                record[field] = value
                with self.assertRaisesRegex(DesignValidationError, "schema validation"):
                    validate_record(record, self.schema)

    def test_wrong_gate_id_missing_or_duplicate_checkpoint_fails(self):
        original = copy.deepcopy(self.checkpoints)
        self.checkpoints[0]["gateId"] = "GATE-UX02"
        with self.assertRaisesRegex(DesignValidationError, "ID mismatch"):
            self.check()
        self.checkpoints = original[:-1]
        with self.assertRaisesRegex(DesignValidationError, "exactly six"):
            self.check()
        self.checkpoints = copy.deepcopy(original)
        self.checkpoints[-1] = copy.deepcopy(self.checkpoints[0])
        with self.assertRaisesRegex(DesignValidationError, "duplicate"):
            self.check()

    def test_participants_and_prerequisites_cannot_be_removed(self):
        original = copy.deepcopy(self.checkpoints)
        self.checkpoints[0]["participantRoles"].remove("Stakeholder")
        with self.assertRaisesRegex(DesignValidationError, "participants"):
            self.check()
        self.checkpoints = original
        self.checkpoints[0]["prerequisiteIds"].remove("MOCK-02-01")
        with self.assertRaisesRegex(DesignValidationError, "prerequisites"):
            self.check()

    def test_contract_decision_requires_A_review(self):
        self.decisions[1]["technicalReviews"]["requiredRoles"].remove("A")
        with self.assertRaisesRegex(DesignValidationError, "reviewer missing"):
            self.check()

    def test_checkpoint_technical_lanes_cannot_be_removed_or_made_human_slots(self):
        self.checkpoints[0]["technicalReviews"]["requiredRoles"].remove("A")
        with self.assertRaisesRegex(DesignValidationError, "technical review lanes"):
            self.check()
        self.checkpoints[0]["technicalReviews"]["requiredRoles"].append("Stakeholder")
        with self.assertRaisesRegex(DesignValidationError, "schema validation"):
            self.check()

    def test_dangling_component_or_decision_reference_fails(self):
        self.decisions[0]["componentIds"].append("ImaginaryComponent")
        with self.assertRaisesRegex(DesignValidationError, "unknown UXD component"):
            self.check()
        self.decisions[0]["componentIds"].pop()
        self.checkpoints[0]["openDecisionRefs"].append("UXD-999")
        with self.assertRaisesRegex(DesignValidationError, "unknown checkpoint decision"):
            self.check()


if __name__ == "__main__":
    unittest.main()
