"""HTTP/security/persistence tests with an explicitly injected fixture model."""

import asyncio
import copy
import json
import secrets
import shutil
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))
sys.path.insert(0, str(Path(__file__).parent))

from test_model import FakeModel, request
from studio.app import COOKIE, MAX_REQUEST_BYTES, ORIGIN, create_app
from studio.service import StudioService, read_json, write_json
from studio.validation import StudioFailure, digest, validate


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = ROOT / ".intent-to-impact" / "studio" / "tests" / secrets.token_hex(12)
        self.folder.mkdir(parents=True)
        self.dist = self.folder / "dist"
        self.dist.mkdir()
        (self.dist / "index.html").write_text("<html>studio fixture</html>", encoding="utf-8")
        (self.dist / "app.js").write_text("export default 1;", encoding="utf-8")
        self.model = FakeModel()
        self.app = create_app(self.folder / "runs", self.dist, self.model, self.fake_builder)
        self.service = self.app.state.service
        self.client = self.new_client()
        session = await self.client.get("/api/studio/session")
        self.csrf = session.json()["csrfToken"]
        self.headers = {"Origin": ORIGIN, "X-CSRF-Token": self.csrf}
        self.build_calls = 0

    async def asyncTearDown(self):
        await self.service.shutdown()
        await self.client.aclose()
        shutil.rmtree(self.folder)

    def new_client(self, peer="127.0.0.1", app=None):
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app or self.app, client=(peer, 43210)),
            base_url=ORIGIN, headers={"X-Studio-Client": "1"},
        )

    def fake_builder(self, result, option_id, output_root):
        self.build_calls += 1
        build_id = "build_fixture_" + str(self.build_calls)
        path = output_root / build_id
        path.mkdir(parents=True)
        with zipfile.ZipFile(path / "package.zip", "w") as package:
            package.writestr("README.txt", "Fixture only; not compiler proof.")
            package.writestr("main.bicep", "// Unit-test fixture, not actual compiler output.")
        return {
            "buildId": build_id, "resultId": result["resultId"], "optionId": option_id,
            "status": "compiled", "compilerVersion": "fixture-test-compiler", "exitCode": 0,
            "diagnostics": "Injected test result; no compiler executed.",
            "files": [{"path": "main.bicep", "content": "// Unit-test fixture, not actual compiler output.", "sha256": "fixture-only"}],
            "downloadUrl": f"/api/studio/builds/{build_id}/download",
            "limitations": ["Fixture only."], "deploymentStatus": "not-deployed",
        }

    async def submit(self, value=None):
        return await self.client.post("/api/studio/analyses", json=value or request(), headers=self.headers)

    async def completed(self, value=None):
        submitted = await self.submit(value)
        self.assertEqual(submitted.status_code, 202, submitted.text)
        await asyncio.gather(*list(self.service.tasks))
        response = await self.client.get("/api/studio/jobs/" + submitted.json()["jobId"])
        self.assertEqual(response.status_code, 200)
        validate("StudioJob", response.json())
        return response.json()

    async def test_success_requires_two_separate_calls_and_real_stage_events(self):
        job = await self.completed()
        self.assertEqual(job["status"], "succeeded")
        self.assertEqual([call["role"] for call in self.model.calls], ["synthesis", "assurance"])
        self.assertEqual([event["stage"] for event in job["events"] if "Fixture" not in event["message"]],
                         ["intake", "synthesis", "assurance", "complete"])
        self.assertEqual(job["result"]["analysis"]["review"][0]["finding"], "Independent fixture assurance.")
        self.assertNotEqual(*[receipt["responseId"] for receipt in job["result"]["modelReceipts"]])
        folder = self.service.root / "jobs" / job["jobId"]
        self.assertEqual(read_json(folder / "result.json"), job["result"])
        self.assertEqual(read_json(folder / "state.json")["resultHash"], digest(job["result"]))

    async def test_corrupt_recovery_records_stop_without_discarding_history(self):
        job = await self.completed()
        path = self.service.root / "jobs" / job["jobId"] / "state.json"
        before = path.read_bytes()
        path.write_bytes(b"{")
        with self.assertRaises(StudioFailure) as caught:
            StudioService(self.service.root, self.model)
        self.assertEqual(caught.exception.code, "recovery_corrupt")
        self.assertEqual(path.read_bytes(), b"{")
        path.write_bytes(before)
        build_path = self.service.root / "build-records" / "corrupt.json"
        build_path.parent.mkdir(exist_ok=True)
        build_path.write_bytes(b"{")
        with self.assertRaises(StudioFailure) as caught:
            StudioService(self.service.root, self.model)
        self.assertEqual(caught.exception.code, "recovery_corrupt")
        self.assertEqual(build_path.read_bytes(), b"{")

    async def test_blocked_build_cannot_expose_a_success_download(self):
        job = await self.completed()
        def blocked_builder(*args):
            result = self.fake_builder(*args)
            result["status"] = "blocked"
            return result
        self.service.bundle_builder = blocked_builder
        response = await self.client.post("/api/studio/builds", json={
            "resultId": job["result"]["resultId"], "optionId": "web",
            "confirmGeneration": True, "idempotencyKey": "blocked-build-key",
        }, headers=self.headers)
        self.assertEqual(response.status_code, 502, response.text)
        self.assertEqual(response.json()["code"], "invalid_build")
        download = await self.client.get("/api/studio/builds/build_fixture_1/download")
        self.assertEqual(download.status_code, 404)

    async def test_cookie_and_health_contract(self):
        response = await self.client.get("/api/studio/session")
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=strict", cookie)
        self.assertEqual(response.json()["csrfToken"], self.csrf)
        health = await self.client.get("/api/studio/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(set(health.json()), {"ready", "model", "message"})
        self.assertNotIn("Access-Control-Allow-Origin", health.headers)

    async def test_foreign_origins_hosts_forwarding_and_preflight_rejected(self):
        for headers in (
            {"Origin": "https://attacker.invalid"}, {"Origin": "null"}, {"Host": "localhost:5173"},
            {"Host": "127.0.0.1:9999"}, {"Forwarded": "for=127.0.0.1"},
            {"X-Forwarded-For": "127.0.0.1"}, {"X-Original-URL": "/api/studio/session"},
        ):
            with self.subTest(headers=headers):
                response = await self.client.get("/api/studio/session", headers=headers)
                self.assertEqual(response.status_code, 403)
        response = await self.client.options("/api/studio/analyses")
        self.assertEqual(response.status_code, 405)
        async with self.new_client(peer="10.0.0.2") as foreign:
            self.assertEqual((await foreign.get("/api/studio/session")).status_code, 403)

    async def test_mutations_require_cookie_exact_origin_csrf_and_client_header(self):
        for headers in ({}, {"Origin": ORIGIN}, {"X-CSRF-Token": self.csrf},
                        {"Origin": ORIGIN, "X-CSRF-Token": "wrong"}):
            self.assertEqual((await self.client.post("/api/studio/analyses", json=request(), headers=headers)).status_code, 403)
        async with self.new_client() as unowned:
            self.assertEqual((await unowned.post("/api/studio/analyses", json=request(), headers=self.headers)).status_code, 401)
            self.assertEqual((await unowned.get("/api/studio/health")).status_code, 401)
        self.assertEqual((await self.client.get("/api/studio/health", headers={"X-Studio-Client": ""})).status_code, 403)
        self.assertEqual(self.model.calls, [])

    async def test_duplicate_security_headers_rejected(self):
        response = await self.client.get("/api/studio/session", headers=[("Host", "127.0.0.1:5173"), ("Host", "evil")])
        self.assertEqual(response.status_code, 400)

    async def test_session_expiry_and_capacity(self):
        for session in self.app.state.sessions.items.values():
            session["expires"] = 0
        self.assertEqual((await self.client.get("/api/studio/health")).status_code, 401)
        with patch("studio.app.MAX_SESSIONS", 0):
            self.assertEqual((await self.client.get("/api/studio/session")).status_code, 429)

    async def test_invalid_json_media_and_request_byte_limits(self):
        response = await self.client.post("/api/studio/analyses", content='{"title":1,"title":2}',
                                          headers={**self.headers, "Content-Type": "application/json"})
        self.assertEqual(response.status_code, 400)
        response = await self.client.post("/api/studio/analyses", content="{}", headers=self.headers)
        self.assertEqual(response.status_code, 415)
        response = await self.client.post("/api/studio/analyses", content="a" * (MAX_REQUEST_BYTES + 1),
                                          headers={**self.headers, "Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.model.calls, [])

    async def test_streamed_body_bound_without_content_length(self):
        async def chunks():
            yield b"a" * MAX_REQUEST_BYTES
            yield b"b"
        response = await self.client.post("/api/studio/analyses", content=chunks(),
                                          headers={**self.headers, "Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)

    async def test_invalid_request_is_not_sent_to_model(self):
        value = request()
        value["consentToModel"] = False
        response = await self.submit(value)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.model.calls, [])

    async def test_http_errors_use_canonical_error_contract(self):
        response = await self.client.post("/api/studio/no-such-route", json={}, headers=self.headers)
        self.assertEqual(response.status_code, 405)
        validate("StudioError", response.json())
        self.assertEqual(response.json()["code"], "method_not_allowed")

    async def test_changed_idempotency_conflicts_unchanged_replays(self):
        job = await self.completed()
        replay = await self.submit()
        self.assertEqual(replay.status_code, 202)
        self.assertEqual(replay.json()["jobId"], job["jobId"])
        response = await self.submit({**request(), "prompt": request()["prompt"] + " Changed."})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(self.model.calls), 2)

    async def test_refinement_creates_distinct_immutable_result(self):
        original = await self.completed()
        snapshot = copy.deepcopy(original["result"])
        value = {**request(), "idempotencyKey": "fixture-revision-2",
                 "previousResultId": snapshot["resultId"], "refinement": "Add delayed pickup reminders."}
        revised = await self.completed(value)
        self.assertEqual(revised["status"], "succeeded")
        self.assertNotEqual(revised["result"]["resultId"], snapshot["resultId"])
        self.assertEqual(self.model.calls[2]["previous"], snapshot)
        self.assertEqual(self.service.get_result(next(iter(self.app.state.sessions.items)), snapshot["resultId"]), snapshot)
        conflicting = {**value, "idempotencyKey": "fixture-revision-3", "prompt": "A different original business."}
        self.assertEqual((await self.submit(conflicting)).status_code, 409)

    async def test_cross_session_job_refinement_build_and_download_denied(self):
        job = await self.completed()
        body = {"resultId": job["result"]["resultId"], "optionId": "web", "confirmGeneration": True,
                "idempotencyKey": "fixture-build-key"}
        build = await self.client.post("/api/studio/builds", json=body, headers=self.headers)
        self.assertEqual(build.status_code, 200, build.text)
        async with self.new_client() as stranger:
            session = await stranger.get("/api/studio/session")
            headers = {"Origin": ORIGIN, "X-CSRF-Token": session.json()["csrfToken"]}
            self.assertEqual((await stranger.get("/api/studio/jobs/" + job["jobId"])).status_code, 404)
            self.assertEqual((await stranger.post("/api/studio/builds", json=body, headers=headers)).status_code, 404)
            self.assertEqual((await stranger.get(build.json()["downloadUrl"])).status_code, 404)
            revision = {**request(), "previousResultId": job["result"]["resultId"], "refinement": "Change pickup."}
            self.assertEqual((await stranger.post("/api/studio/analyses", json=revision, headers=headers)).status_code, 404)

    async def test_refinement_provenance_survives_both_model_passes(self):
        original = await self.completed()
        self.assertNotIn("refinement", {source["id"] for source in original["result"]["sources"]})
        generate = self.model.generate
        async def cite_refinement(role, *args, **kwargs):
            value, receipt = await generate(role, *args, **kwargs)
            if role == "synthesis":
                value["requirements"][0]["sourceIds"] = ["refinement"]
            value["review"][0]["sourceIds"] = ["refinement"]
            return value, receipt
        self.model.generate = cite_refinement
        revised = await self.completed({
            **request(), "previousResultId": original["result"]["resultId"],
            "refinement": "Add delayed pickup reminders.", "idempotencyKey": "fixture-refinement-provenance",
        })
        self.assertEqual(revised["status"], "succeeded")
        self.assertIn({"id": "refinement", "name": "Refinement instruction"}, revised["result"]["sources"])
        self.assertEqual(revised["result"]["analysis"]["requirements"][0]["sourceIds"], ["refinement"])
        self.assertEqual(revised["result"]["analysis"]["review"][0]["sourceIds"], ["refinement"])
        self.assertEqual(self.model.calls[2]["request"]["prompt"], request()["prompt"])

    async def test_refinement_source_cannot_be_fabricated_without_revision(self):
        generate = self.model.generate
        async def fabricate(role, *args, **kwargs):
            value, receipt = await generate(role, *args, **kwargs)
            value["requirements"][0]["sourceIds"] = ["refinement"]
            return value, receipt
        self.model.generate = fabricate
        job = await self.completed()
        self.assertEqual(job["status"], "failed")
        self.assertEqual(job["error"]["code"], "invalid_references")
        self.assertIsNone(job["result"])
        self.assertEqual(len(self.model.calls), 1)

    async def test_build_idempotency_and_safe_download(self):
        job = await self.completed()
        body = {"resultId": job["result"]["resultId"], "optionId": "web", "confirmGeneration": True,
                "idempotencyKey": "fixture-build-key"}
        response = await self.client.post("/api/studio/builds", json=body, headers=self.headers)
        validate("BuildResult", response.json())
        repeated = await self.client.post("/api/studio/builds", json=body, headers=self.headers)
        self.assertEqual(response.json(), repeated.json())
        self.assertEqual(self.build_calls, 1)
        conflicting = await self.client.post("/api/studio/builds", json={**body, "optionId": "event"}, headers=self.headers)
        self.assertEqual(conflicting.status_code, 409)
        downloaded = await self.client.get(response.json()["downloadUrl"])
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.headers["content-type"], "application/zip")
        self.assertEqual(downloaded.content[:2], b"PK")
        with self.assertRaises(StudioFailure):
            self.service.download(next(iter(self.app.state.sessions.items)), "..\\secret")

    async def test_bad_build_path_is_rejected(self):
        job = await self.completed()
        original_builder = self.service.bundle_builder
        def unsafe(*args):
            result = original_builder(*args)
            result["downloadUrl"] = "https://attacker.invalid/secret"
            return result
        self.service.bundle_builder = unsafe
        body = {"resultId": job["result"]["resultId"], "optionId": "web", "confirmGeneration": True,
                "idempotencyKey": "fixture-unsafe-build"}
        response = await self.client.post("/api/studio/builds", json=body, headers=self.headers)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["code"], "invalid_build")

    async def test_failure_has_no_generated_analysis_or_fallback(self):
        self.model.failure = StudioFailure("model_access_denied", "Denied safely.", 503)
        job = await self.completed()
        self.assertEqual(job["status"], "failed")
        self.assertIsNone(job["result"])
        self.assertEqual(job["error"]["code"], "model_access_denied")
        self.assertEqual(len(self.model.calls), 1)
        self.assertFalse((self.service.root / "jobs" / job["jobId"] / "result.json").exists())

    async def test_invalid_model_source_refs_fail_before_assurance(self):
        original = self.model.generate
        async def invalid(*args, **kwargs):
            value, receipt = await original(*args, **kwargs)
            value["requirements"][0]["sourceIds"] = ["foreign"]
            return value, receipt
        self.model.generate = invalid
        job = await self.completed()
        self.assertEqual(job["status"], "failed")
        self.assertEqual(job["error"]["code"], "invalid_references")
        self.assertEqual(len(self.model.calls), 1)

    async def test_assurance_failure_preserves_first_receipt_not_result(self):
        original = self.model.generate
        async def failure(role, *args, **kwargs):
            if role == "assurance":
                raise StudioFailure("model_timeout", "Assurance timed out.", 504, True)
            return await original(role, *args, **kwargs)
        self.model.generate = failure
        job = await self.completed()
        self.assertEqual(job["status"], "failed")
        folder = self.service.root / "jobs" / job["jobId"]
        self.assertTrue((folder / "synthesis-receipt.json").exists())
        self.assertFalse((folder / "result.json").exists())

    async def test_invalid_assurance_source_and_duplicate_receipt_fail_closed(self):
        original = self.model.generate
        async def invalid(role, *args, **kwargs):
            value, receipt = await original(role, *args, **kwargs)
            if role == "assurance":
                value["review"][0]["sourceIds"] = ["foreign"]
            return value, receipt
        self.model.generate = invalid
        job = await self.completed()
        self.assertEqual(job["error"]["code"], "invalid_references")
        self.assertIsNone(job["result"])
        async def repeated_receipt(role, *args, **kwargs):
            value, receipt = await original(role, *args, **kwargs)
            receipt["responseId"] = "fixture-repeated-response"
            return value, receipt
        self.model.generate = repeated_receipt
        second = await self.completed({**request(), "idempotencyKey": "fixture-duplicate-receipt"})
        self.assertEqual(second["error"]["code"], "invalid_receipt")
        self.assertIsNone(second["result"])

    async def test_scheduled_input_is_immutable_to_caller_mutation(self):
        value = request()
        owner = next(iter(self.app.state.sessions.items))
        job = await self.service.submit(owner, value)
        value["documents"][0]["text"] = "Changed after submission."
        await asyncio.gather(*list(self.service.tasks))
        self.assertEqual(self.model.calls[0]["request"]["documents"][0]["text"], request()["documents"][0]["text"])
        self.assertEqual(self.service.get_job(owner, job["jobId"])["status"], "succeeded")

    async def test_concurrency_job_limits_and_cancellation(self):
        self.model.delay = 100
        first = await self.submit()
        second = await self.submit({**request(), "idempotencyKey": "fixture-other-key"})
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 429)
        await asyncio.sleep(0)
        await self.service.shutdown()
        job = await self.client.get("/api/studio/jobs/" + first.json()["jobId"])
        self.assertEqual(job.json()["status"], "failed")
        self.assertEqual(job.json()["error"]["code"], "cancelled")
        with patch("studio.service.MAX_JOBS", 1):
            self.assertEqual((await self.submit({**request(), "idempotencyKey": "fixture-limit-key"})).status_code, 429)

    async def test_total_job_timeout(self):
        self.model.delay = 0.1
        with patch("studio.service.JOB_TIMEOUT", 0.01):
            job = await self.completed()
        self.assertEqual(job["error"]["code"], "job_timeout")
        self.assertIsNone(job["result"])

    async def test_recovery_and_durable_owned_results(self):
        job = await self.completed()
        owner = next(iter(self.app.state.sessions.items))
        restored = StudioService(self.service.root, self.model)
        self.assertEqual(restored.get_result(owner, job["result"]["resultId"]), job["result"])
        state_path = self.service.root / "jobs" / job["jobId"] / "state.json"
        record = read_json(state_path)
        record["job"].update(status="running", result=None)
        write_json(state_path, record)
        restarted = StudioService(self.service.root, self.model)
        self.assertEqual(restarted.get_job(owner, job["jobId"])["error"]["code"], "recovery_needed")
        self.assertEqual(len(self.model.calls), 2)

    async def test_storage_limit_and_path_traversal(self):
        with patch("studio.service.MAX_BYTES", 1):
            self.assertEqual((await self.submit()).status_code, 429)
        with self.assertRaises(StudioFailure):
            self.service._path("..", "..", "outside")
        for path in ("/.env", "/%2e%2e/.env", "/studio.schema.json", "/api/studio/no-such-route", "/app.py"):
            with self.subTest(path=path):
                response = await self.client.get(path)
                self.assertEqual(response.status_code, 404)
        self.assertEqual((await self.client.get("/")).status_code, 200)
        self.assertEqual((await self.client.get("/a-spa-route")).status_code, 200)
        self.assertEqual((await self.client.get("/app.js")).status_code, 200)

    async def test_secure_fixed_loopback_launcher(self):
        from studio import serve
        with patch.object(serve, "create_app", return_value="fixture-app"), patch.object(serve.uvicorn, "run") as run:
            serve.main()
        self.assertEqual(run.call_args.kwargs["host"], "127.0.0.1")
        self.assertEqual(run.call_args.kwargs["port"], 5173)
        self.assertFalse(run.call_args.kwargs["proxy_headers"])


if __name__ == "__main__":
    unittest.main()
