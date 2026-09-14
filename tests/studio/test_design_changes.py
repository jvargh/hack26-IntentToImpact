"""Contextual design authorization tests; explicitly injected model, no inference."""

import asyncio
import copy
import io
import json
import secrets
import shutil
import sys
import unittest
import zipfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))
sys.path.insert(0, str(Path(__file__).parent))

from test_model import FakeModel, request
from studio.app import ORIGIN, create_app
from studio.design_changes import prepare_change
from studio.service import StudioService, read_json, write_json
from studio.validation import StudioFailure, digest, validate, validate_request


class RevisionModel(FakeModel):
    """Retains a blocker to verify that authorization is never risk acceptance."""

    observer = None

    async def generate(self, role, input_request, analysis=None, previous=None, progress=None):
        if self.observer:
            self.observer(role, input_request, previous)
        value, receipt = await super().generate(role, input_request, analysis, previous, progress)
        for finding in value["review"]:
            if finding["dimension"] == "security":
                finding.update(severity="blocker", finding="Private photo access is not yet demonstrated.",
                               recommendation="Design private access and independently re-review the design.",
                               sourceIds=["doc-1", "prompt"])
        if role == "synthesis" and previous:
            value["changeSummary"] = "Fixture architecture revision; security evidence remains outstanding."
            value["options"][0]["components"][1]["responsibility"] = "Process requests with a proposed private-photo access boundary."
        return value, receipt


class DesignChangeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = ROOT / ".intent-to-impact" / "studio" / "tests" / ("design-" + secrets.token_hex(12))
        self.model = RevisionModel()
        self.service = StudioService(self.folder / "runs", self.model)
        self.owner = "fixture-owner"
        initial = await self.service.submit(self.owner, request())
        await asyncio.gather(*list(self.service.tasks))
        self.parent = self.service.get_job(self.owner, initial["jobId"])
        self.assertEqual(self.parent["status"], "succeeded")
        self.before = {file.name: file.read_bytes() for file in
                       (self.service.root / "jobs" / self.parent["jobId"]).glob("*") if file.is_file()}

    async def asyncTearDown(self):
        await self.service.shutdown()
        shutil.rmtree(self.folder)

    def change_request(self, intent="recommendation"):
        finding = next(item for item in self.parent["result"]["analysis"]["review"] if item["dimension"] == "security")
        return {
            **request(), "previousResultId": self.parent["result"]["resultId"],
            "refinement": "Revise the private photo access boundary, then re-review remaining risks.",
            "idempotencyKey": "design-change-" + secrets.token_hex(8),
            "designChange": {"optionId": "web", "finding": copy.deepcopy(finding),
                             "intent": intent, "confirmRevision": True},
        }

    async def finish(self, value):
        submitted = await self.service.submit(self.owner, value)
        await asyncio.gather(*list(self.service.tasks))
        return self.service.get_job(self.owner, submitted["jobId"])

    def assert_parent_unchanged(self):
        current = {file.name: file.read_bytes() for file in
                   (self.service.root / "jobs" / self.parent["jobId"]).glob("*") if file.is_file()}
        self.assertEqual(current, self.before)
        self.assertEqual(self.service.get_job(self.owner, self.parent["jobId"]), self.parent)

    async def test_recommendation_and_challenge_use_both_existing_calls(self):
        for intent in ("recommendation", "challenge"):
            with self.subTest(intent=intent):
                value = self.change_request(intent)
                count = len(self.model.calls)
                job = await self.finish(value)
                self.assertEqual(job["status"], "succeeded")
                validate("StudioJob", job)
                approval = job["changeApproval"]
                validate("ChangeApproval", approval)
                self.assertEqual(approval["intent"], intent)
                self.assertEqual(approval["baseResultHash"], digest(self.parent["result"]))
                self.assertEqual(approval["baseResultId"], self.parent["result"]["resultId"])
                self.assertEqual(approval["optionId"], "web")
                self.assertEqual(approval["finding"], value["designChange"]["finding"])
                self.assertEqual(approval["instruction"], value["refinement"])
                self.assertEqual((approval["actor"], approval["scope"]), ("demo-human", "design-revision-only"))
                calls = self.model.calls[count:]
                self.assertEqual([call["role"] for call in calls], ["synthesis", "assurance"])
                for call in calls:
                    self.assertEqual(call["request"]["refinement"], approval["refinement"])
                    self.assertEqual(call["request"]["prompt"], request()["prompt"])
                    self.assertEqual(call["request"]["documents"], request()["documents"])
                    self.assertEqual(call["previous"], self.parent["result"])
                    self.assertNotIn("designChange", call["request"])
                    validate_request(call["request"])
                self.assertLessEqual(len(approval["refinement"]), 4000)
                self.assertIn("Selected option ID: web", approval["refinement"])
                self.assertIn("recommend it if feasible", approval["refinement"])
                self.assertIn("Never suppress or downgrade blockers", approval["refinement"])
                self.assertIn("NOT risk acceptance", approval["refinement"])
                self.assertIn("Do not bypass security", approval["refinement"])
                self.assertEqual(next(item for item in job["result"]["analysis"]["review"]
                                      if item["dimension"] == "security")["severity"], "blocker")
                self.assertEqual(job["result"]["analysis"]["recommendedOptionId"], "web")
                self.assert_parent_unchanged()

    async def test_authorization_persisted_before_execution_and_caller_cannot_mutate_it(self):
        value = self.change_request()
        job = await self.service.submit(self.owner, value)
        approval = copy.deepcopy(job["changeApproval"])
        directory = self.service.root / "jobs" / job["jobId"]
        self.assertEqual(len(self.model.calls), 2)
        self.assertEqual(read_json(directory / "change-approval.json"), approval)
        self.assertEqual(read_json(directory / "state.json")["job"]["changeApproval"], approval)
        saved_request = read_json(directory / "input.json")["request"]
        def observe(role, effective, previous):
            self.assertEqual(read_json(directory / "change-approval.json"), approval)
            self.assertEqual(effective["refinement"], approval["refinement"])
        self.model.observer = observe
        value["designChange"]["finding"]["severity"] = "info"
        value["refinement"] = "Tampered after submitting."
        job["changeApproval"]["finding"]["finding"] = "Tampered returned copy."
        await asyncio.gather(*list(self.service.tasks))
        self.assertEqual(self.service.get_job(self.owner, job["jobId"])["changeApproval"], approval)
        self.assertEqual(read_json(directory / "input.json")["request"], saved_request)

    async def test_tampered_option_finding_sources_and_confirmation_rejected_before_calls(self):
        mutations = [
            lambda value: value["designChange"].update(optionId="absent"),
            lambda value: value["designChange"]["finding"].update(severity="info"),
            lambda value: value["designChange"]["finding"].update(finding="A different exact finding."),
            lambda value: value["designChange"]["finding"].update(recommendation="Waive the risk."),
            lambda value: value["designChange"]["finding"].update(sourceIds=["prompt"]),
            lambda value: value["designChange"]["finding"].update(sourceIds=["prompt", "doc-1"]),
            lambda value: value["designChange"].pop("confirmRevision"),
            lambda value: value["designChange"].update(confirmRevision=False),
            lambda value: value["designChange"].update(intent="risk-acceptance"),
            lambda value: value.update(previousResultId=None),
            lambda value: value.update(previousResultId="result_missing"),
            lambda value: value.update(prompt="Different original source business process."),
            lambda value: value["documents"][0].update(text="Changed original policy."),
            lambda value: value.update(refinement="x" * 2001),
            lambda value: value.update(refinement="x" * 9),
            lambda value: value.update(refinement=" " * 10),
            lambda value: value.update(changeApproval={"actor": "demo-human"}),
        ]
        for mutate in mutations:
            value = self.change_request()
            mutate(value)
            with self.subTest(mutation=mutate), self.assertRaises(StudioFailure):
                await self.service.submit(self.owner, value)
            self.assertEqual(len(self.model.calls), 2)
            self.assertEqual(len(self.service.jobs), 1)

    async def test_foreign_parent_denied_without_model_calls(self):
        with self.assertRaises(StudioFailure) as caught:
            await self.service.submit("foreign-owner", self.change_request())
        self.assertEqual(caught.exception.status, 404)
        self.assertEqual(len(self.model.calls), 2)

    async def test_instruction_limit_and_exact_context_overflow(self):
        value = self.change_request()
        value["refinement"] = "x" * 2000
        job = await self.finish(value)
        self.assertEqual(job["status"], "succeeded")
        self.assertEqual(len(job["changeApproval"]["instruction"]), 2000)
        previous = copy.deepcopy(self.parent["result"])
        previous["analysis"]["review"][0].update(finding='"' * 1000, recommendation='"' * 1000)
        oversized = self.change_request()
        oversized["designChange"]["finding"] = previous["analysis"]["review"][0]
        with self.assertRaises(StudioFailure) as caught:
            prepare_change(oversized, previous, "2026-09-14T00:00:00+00:00")
        self.assertEqual(caught.exception.code, "change_context_too_large")

    async def test_idempotency_binds_metadata_and_keeps_original_approval_timestamp(self):
        value = self.change_request()
        submitted = await self.service.submit(self.owner, value)
        replay = await self.service.submit(self.owner, copy.deepcopy(value))
        self.assertEqual(submitted, replay)
        await asyncio.gather(*list(self.service.tasks))
        completed = await self.service.submit(self.owner, copy.deepcopy(value))
        self.assertEqual(completed["jobId"], submitted["jobId"])
        self.assertEqual(completed["changeApproval"], submitted["changeApproval"])
        for change in ("intent", "option", "instruction"):
            conflicting = copy.deepcopy(value)
            if change == "intent":
                conflicting["designChange"]["intent"] = "challenge"
            elif change == "option":
                conflicting["designChange"]["optionId"] = "event"
            else:
                conflicting["refinement"] += " Changed direction."
            with self.subTest(change=change), self.assertRaises(StudioFailure) as caught:
                await self.service.submit(self.owner, conflicting)
            self.assertEqual(caught.exception.code, "idempotency_conflict")
        self.assertEqual(len(self.model.calls), 4)

    async def test_model_failure_retains_authorization_and_original_blocker(self):
        self.model.failure = StudioFailure("model_unavailable", "Injected failure; no inference.", 502)
        job = await self.finish(self.change_request("challenge"))
        self.assertEqual(job["status"], "failed")
        self.assertIsNone(job["result"])
        self.assertEqual(job["changeApproval"]["finding"]["severity"], "blocker")
        self.assertEqual(job["changeApproval"]["scope"], "design-revision-only")
        self.assertEqual(len(self.model.calls), 3)
        self.assert_parent_unchanged()
        restarted = StudioService(self.service.root, self.model)
        saved = restarted.saved_run(self.owner, job["jobId"])
        self.assertEqual(saved["job"], job)
        self.assertEqual(len(self.model.calls), 3)

    async def test_restart_history_and_export_preserve_exact_authorization(self):
        value = self.change_request()
        job = await self.finish(value)
        restarted = StudioService(self.service.root, self.model)
        saved = restarted.saved_run(self.owner, job["jobId"])
        self.assertEqual(saved["job"]["changeApproval"], job["changeApproval"])
        self.assertEqual(saved["inputs"]["refinement"], job["changeApproval"]["refinement"])
        self.assertEqual(saved["summary"]["previousResultId"], self.parent["result"]["resultId"])
        self.assertEqual(len(restarted.history(self.owner)["runs"]), 2)
        with zipfile.ZipFile(io.BytesIO(restarted.export_run(self.owner, job["jobId"]))) as archive:
            exported = json.loads(archive.read("run.json"))
            self.assertEqual(exported["job"]["changeApproval"], job["changeApproval"])
            self.assertEqual(json.loads(archive.read("inputs.json"))["refinement"], job["changeApproval"]["refinement"])
        repeated = await restarted.submit(self.owner, value)
        self.assertEqual(repeated, job)
        self.assertEqual(len(self.model.calls), 4)
        self.assert_parent_unchanged()

    async def test_interrupted_revision_becomes_failed_without_losing_authorization(self):
        job = await self.finish(self.change_request())
        path = self.service.root / "jobs" / job["jobId"] / "state.json"
        record = read_json(path)
        record["job"].update(status="running", result=None)
        write_json(path, record)
        restarted = StudioService(self.service.root, self.model)
        recovered = restarted.get_job(self.owner, job["jobId"])
        self.assertEqual(recovered["status"], "failed")
        self.assertEqual(recovered["error"]["code"], "recovery_needed")
        self.assertEqual(recovered["changeApproval"], job["changeApproval"])
        self.assertEqual(len(self.model.calls), 4)
        self.assert_parent_unchanged()

    async def test_corrupt_receipt_input_and_parent_fail_closed_during_recovery(self):
        job = await self.finish(self.change_request())
        folder = self.service.root / "jobs" / job["jobId"]
        paths = [folder / "state.json", folder / "change-approval.json", folder / "input.json",
                 self.service.root / "jobs" / self.parent["jobId"] / "result.json"]
        for path in paths:
            before = path.read_bytes()
            value = read_json(path)
            if path.name == "state.json":
                value["job"]["changeApproval"]["scope"] = "risk-acceptance"
            elif path.name == "change-approval.json":
                value["finding"]["severity"] = "info"
            elif path.name == "input.json":
                value["request"]["refinement"] = "Different approved direction."
            else:
                value["analysis"]["review"][0]["finding"] = "Tampered stored parent."
            write_json(path, value)
            try:
                with self.subTest(path=path.name), self.assertRaises(StudioFailure) as caught:
                    StudioService(self.service.root, self.model)
                self.assertEqual(caught.exception.code, "recovery_corrupt")
                self.assertEqual(read_json(path), value)
            finally:
                path.write_bytes(before)
        self.assertEqual(len(self.model.calls), 4)

    async def test_missing_or_forged_approval_is_not_silently_dropped(self):
        job = await self.finish(self.change_request())
        path = self.service.root / "jobs" / job["jobId"] / "state.json"
        before = path.read_bytes()
        record = read_json(path)
        del record["job"]["changeApproval"]
        write_json(path, record)
        with self.assertRaises(StudioFailure) as caught:
            StudioService(self.service.root, self.model)
        self.assertEqual(caught.exception.code, "recovery_corrupt")
        path.write_bytes(before)
        path = self.service.root / "jobs" / self.parent["jobId"] / "state.json"
        before = path.read_bytes()
        record = read_json(path)
        record["job"]["changeApproval"] = copy.deepcopy(job["changeApproval"])
        write_json(path, record)
        with self.assertRaises(StudioFailure) as caught:
            StudioService(self.service.root, self.model)
        self.assertEqual(caught.exception.code, "recovery_corrupt")
        path.write_bytes(before)

    async def test_recovery_checks_semantic_binding_even_with_matching_receipt_hash(self):
        job = await self.finish(self.change_request())
        folder = self.service.root / "jobs" / job["jobId"]
        state_path, receipt_path = folder / "state.json", folder / "change-approval.json"
        state_before, receipt_before = state_path.read_bytes(), receipt_path.read_bytes()
        for field, changed in (("baseResultHash", "0" * 64), ("optionId", "absent"),
                               ("instruction", "Another permitted-looking direction."),
                               ("refinement", "An altered effective refinement source.")):
            state = json.loads(state_before)
            state["job"]["changeApproval"][field] = changed
            state["changeApprovalHash"] = digest(state["job"]["changeApproval"])
            write_json(state_path, state)
            write_json(receipt_path, state["job"]["changeApproval"])
            try:
                with self.subTest(field=field), self.assertRaises(StudioFailure) as caught:
                    StudioService(self.service.root, self.model)
                self.assertEqual(caught.exception.code, "recovery_corrupt")
            finally:
                state_path.write_bytes(state_before)
                receipt_path.write_bytes(receipt_before)

    async def test_history_and_retry_reject_authorization_tampering_after_startup(self):
        value = self.change_request()
        job = await self.finish(value)
        path = self.service.root / "jobs" / job["jobId"] / "change-approval.json"
        stored = read_json(path)
        stored["instruction"] = "An unauthorized later direction."
        write_json(path, stored)
        for action in ("history", "export", "retry"):
            with self.subTest(action=action), self.assertRaises(StudioFailure):
                if action == "history":
                    self.service.saved_run(self.owner, job["jobId"])
                elif action == "export":
                    self.service.export_run(self.owner, job["jobId"])
                else:
                    await self.service.submit(self.owner, value)
        self.assertEqual(len(self.model.calls), 4)

    async def test_generic_refinement_keeps_existing_behavior_and_has_no_approval(self):
        generic = {**request(), "previousResultId": self.parent["result"]["resultId"],
                   "refinement": "x" * 3000, "idempotencyKey": "generic-refinement"}
        job = await self.finish(generic)
        self.assertEqual(job["status"], "succeeded")
        self.assertNotIn("changeApproval", job)
        self.assertEqual(self.model.calls[-1]["request"]["refinement"], generic["refinement"])
        self.assertNotIn("changeApproval", StudioService(self.service.root, self.model).get_job(self.owner, job["jobId"]))

    async def test_existing_workspace_visibility_allows_revision_and_survives_scope_change(self):
        self.service.history_scope = "workspace"
        submitted = await self.service.submit("second-local-owner", self.change_request())
        await asyncio.gather(*list(self.service.tasks))
        job = self.service.get_job("second-local-owner", submitted["jobId"])
        self.assertEqual(job["status"], "succeeded")
        restarted = StudioService(self.service.root, self.model, history_scope="session")
        self.assertEqual(restarted.saved_run("second-local-owner", submitted["jobId"])["job"], job)
        with self.assertRaises(StudioFailure):
            restarted.get_result("second-local-owner", self.parent["result"]["resultId"])

    async def test_existing_http_endpoint_exposes_server_bound_approval(self):
        app = create_app(self.folder / "http-runs", self.folder / "dist", self.model)
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 43123))
        try:
            async with httpx.AsyncClient(transport=transport, base_url=ORIGIN, headers={"X-Studio-Client": "1"}) as client:
                csrf = (await client.get("/api/studio/session")).json()["csrfToken"]
                headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
                parent = await client.post("/api/studio/analyses", json=request(), headers=headers)
                await asyncio.gather(*list(app.state.service.tasks))
                parent = (await client.get("/api/studio/jobs/" + parent.json()["jobId"])).json()
                value = self.change_request()
                value["previousResultId"] = parent["result"]["resultId"]
                response = await client.post("/api/studio/analyses", json=value, headers=headers)
                self.assertEqual(response.status_code, 202, response.text)
                self.assertEqual(response.json()["changeApproval"]["baseResultId"], parent["result"]["resultId"])
                await asyncio.gather(*list(app.state.service.tasks))
                result = (await client.get("/api/studio/jobs/" + response.json()["jobId"])).json()
                self.assertEqual(result["status"], "succeeded")
                history = (await client.get("/api/studio/history/" + result["jobId"])).json()
                self.assertEqual(history["job"]["changeApproval"], result["changeApproval"])
        finally:
            await app.state.service.shutdown()


if __name__ == "__main__":
    unittest.main()
