"""Run history/export tests use injected model data; no model or Azure calls."""

import asyncio
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
from uuid import uuid4
import zipfile

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))
sys.path.insert(0, str(Path(__file__).parent))
from studio.app import create_app, ORIGIN
from studio.service import read_json, write_json
from studio.validation import StudioFailure
from test_model import FakeModel, request


class HistoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = ROOT / ".intent-to-impact" / "studio" / "tests" / ("history-" + uuid4().hex)
        self.root.mkdir(parents=True)
        self.model = FakeModel()
        self.clients = []
        self.app = create_app(self.root / "runs", self.root / "dist", self.model, self.builder)

    async def asyncTearDown(self):
        await self.app.state.service.shutdown()
        for client in self.clients:
            await client.aclose()
        shutil.rmtree(self.root)

    def builder(self, result, option, root):
        build_id = "fixture_" + uuid4().hex
        folder = root / build_id
        folder.mkdir(parents=True)
        with zipfile.ZipFile(folder / "package.zip", "w") as archive:
            archive.writestr("main.bicep", "// Fixture only")
        return {
            "buildId": build_id, "resultId": result["resultId"], "optionId": option,
            "status": "compiled", "compilerVersion": "fixture-compiler", "exitCode": 0,
            "diagnostics": "Injected fixture, no compiler ran",
            "files": [{"path": "main.bicep", "content": "// Fixture only", "sha256": "fixture-only"}],
            "downloadUrl": f"/api/studio/builds/{build_id}/download",
            "limitations": ["Fixture only"], "deploymentStatus": "not-deployed",
        }

    async def client(self):
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app, client=("127.0.0.1", 44000)),
                                   base_url=ORIGIN, headers={"X-Studio-Client": "1"})
        self.clients.append(client)
        response = await client.get("/api/studio/session")
        return client, {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrfToken"]}

    async def create_run(self, client, headers, **updates):
        value = {**request(), "idempotencyKey": uuid4().hex, **updates}
        response = await client.post("/api/studio/analyses", json=value, headers=headers)
        self.assertEqual(response.status_code, 202, response.text)
        await asyncio.gather(*list(self.app.state.service.tasks))
        job = (await client.get("/api/studio/jobs/" + response.json()["jobId"])).json()
        return job, value

    async def test_private_default_history_is_scoped_and_archive_excludes_authentication(self):
        a, headers = await self.client()
        b, _ = await self.client()
        job, value = await self.create_run(a, headers)
        index = await a.get("/api/studio/history")
        self.assertEqual(index.json()["scope"], "session")
        self.assertEqual([run["jobId"] for run in index.json()["runs"]], [job["jobId"]])
        self.assertEqual((await b.get("/api/studio/history")).json()["runs"], [])
        self.assertEqual((await b.get("/api/studio/history/" + job["jobId"])).status_code, 404)
        self.assertEqual((await b.get("/api/studio/history/" + job["jobId"] + "/download")).status_code, 404)
        calls = len(self.model.calls)
        saved = (await a.get("/api/studio/history/" + job["jobId"])).json()
        self.assertEqual(saved["inputs"]["prompt"], value["prompt"])
        archive = await a.get("/api/studio/history/" + job["jobId"] + "/download")
        self.assertEqual(archive.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
            self.assertEqual(z.read("documents/01.txt").decode(), value["documents"][0]["text"])
            inputs = json.loads(z.read("inputs.json"))
            self.assertNotIn("idempotencyKey", inputs)
            self.assertNotIn("consentToModel", inputs)
            run = json.loads(z.read("run.json"))
            self.assertNotIn("owner", run)
            self.assertNotIn("csrf", run)
            self.assertNotIn("sessions.json", z.namelist())
            self.assertEqual(run["job"]["result"], job["result"])
        self.assertEqual(len(self.model.calls), calls)

    async def test_explicit_workspace_history_survives_sessions_and_restart(self):
        self.app = create_app(self.root / "runs", self.root / "dist", self.model, self.builder, history_scope="workspace")
        a, headers = await self.client()
        job, value = await self.create_run(a, headers, title="Earlier workspace run")
        build = await a.post("/api/studio/builds", json={
            "resultId": job["result"]["resultId"], "optionId": "web", "confirmGeneration": True, "idempotencyKey": uuid4().hex,
        }, headers=headers)
        self.assertEqual(build.status_code, 200, build.text)
        self.model.failure = StudioFailure("fixture_failure", "Recorded test failure", 502)
        failed, _ = await self.create_run(a, headers, title="Failed workspace run")
        self.model.failure = None
        before = (self.root / "runs" / "jobs" / job["jobId"] / "input.json").read_bytes()
        await self.app.state.service.shutdown()
        self.app = create_app(self.root / "runs", self.root / "dist", self.model, self.builder, history_scope="workspace")
        b, _ = await self.client()
        calls = len(self.model.calls)
        index = (await b.get("/api/studio/history")).json()
        self.assertEqual(index["scope"], "workspace")
        self.assertEqual(index["runs"][0]["jobId"], failed["jobId"])
        self.assertEqual({row["status"] for row in index["runs"]}, {"succeeded", "failed"})
        saved = (await b.get("/api/studio/history/" + job["jobId"])).json()
        self.assertEqual(saved["inputs"]["prompt"], value["prompt"])
        self.assertEqual(saved["summary"]["compiledPackageCount"], 1)
        metadata = await b.get(f"/api/studio/history/{job['jobId']}/builds/{build.json()['buildId']}")
        self.assertEqual(metadata.json(), build.json())
        self.assertEqual((await b.get(build.json()["downloadUrl"])).status_code, 200)
        wrong = await b.get(f"/api/studio/history/{failed['jobId']}/builds/{build.json()['buildId']}")
        self.assertEqual(wrong.status_code, 404)
        self.assertEqual(len(self.model.calls), calls)
        self.assertEqual((self.root / "runs" / "jobs" / job["jobId"] / "input.json").read_bytes(), before)

    async def test_shared_run_can_be_refined_only_as_a_new_consented_job(self):
        self.app = create_app(self.root / "runs", self.root / "dist", self.model, history_scope="workspace")
        a, headers = await self.client()
        original, value = await self.create_run(a, headers)
        b, other_headers = await self.client()
        revised, _ = await self.create_run(b, other_headers, previousResultId=original["result"]["resultId"],
                                          refinement="Add resilient notification processing")
        self.assertNotEqual(revised["jobId"], original["jobId"])
        self.assertEqual((await a.get("/api/studio/jobs/" + original["jobId"])).json(), original)
        self.assertEqual((await b.get("/api/studio/history/" + revised["jobId"])).json()["inputs"]["previousResultId"],
                         original["result"]["resultId"])

    async def test_history_never_silently_returns_tampered_input_or_unsafe_archive_paths(self):
        client, headers = await self.client()
        job, value = await self.create_run(client, headers, documents=[
            {"id": "doc-1", "name": "..\\outside.txt", "text": "Private repair photos fixture"}
        ])
        response = await client.get("/api/studio/history/" + job["jobId"] + "/download")
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            self.assertIn("documents/01.txt", z.namelist())
            self.assertFalse(any(".." in name or "\\" in name for name in z.namelist()))
        path = self.root / "runs" / "jobs" / job["jobId"] / "input.json"
        data = read_json(path)
        data["effective"]["prompt"] = "Different input without a matching hash"
        write_json(path, data)
        response = await client.get("/api/studio/history")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "history_integrity")


if __name__ == "__main__":
    unittest.main()
