"""Explicit public ACA demo retains CSRF, HTTPS cookies and session-private history."""

import asyncio
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from test_hosting import HostingFixture, PUBLIC_ORIGIN
from test_model import FakeModel, request
from studio.app import create_app


class PublicDemoTests(HostingFixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = replace(self.make_config(), auth_mode="anonymous-demo")
        self.model = FakeModel()
        self.app = create_app(
            hosted_config=self.config, model=self.model,
            hosted_lock=SimpleNamespace(config=self.config, acquired=True, ready=lambda: True),
        )
        self.addAsyncCleanup(self.app.state.service.shutdown)

    def client(self):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app, client=("10.0.0.3", 12345)),
                                 base_url=PUBLIC_ORIGIN, headers={"X-Studio-Client": "1"})

    async def test_anyone_can_establish_session_but_csrf_and_origin_remain_required(self):
        async with self.client() as client:
            session = await client.get("/api/studio/session")
            self.assertEqual(session.status_code, 200)
            self.assertIn("Secure", session.headers["set-cookie"])
            self.assertEqual((await client.post("/api/studio/analyses", json=request())).status_code, 403)
            self.assertEqual((await client.get("/api/studio/session", headers={"Origin": "https://foreign.test"})).status_code, 403)
            posted = await client.post("/api/studio/analyses", json=request(),
                                      headers={"Origin": PUBLIC_ORIGIN, "X-CSRF-Token": session.json()["csrfToken"]})
            self.assertEqual(posted.status_code, 202, posted.text)
            await asyncio.gather(*list(self.app.state.service.tasks))
            self.assertEqual((await client.get("/api/studio/jobs/" + posted.json()["jobId"])).json()["status"], "succeeded")

    async def test_public_visitors_cannot_read_each_others_runs_even_with_forged_principal(self):
        self.assertEqual(self.app.state.service.history_scope, "session")
        async with self.client() as first, self.client() as second:
            s1 = (await first.get("/api/studio/session")).json()
            job = (await first.post("/api/studio/analyses", json=request(),
                                   headers={"Origin": PUBLIC_ORIGIN, "X-CSRF-Token": s1["csrfToken"]})).json()
            await asyncio.gather(*list(self.app.state.service.tasks))
            await second.get("/api/studio/session")
            self.assertEqual((await second.get("/api/studio/history")).json()["runs"], [])
            for path in ("/api/studio/jobs/", "/api/studio/history/"):
                response = await second.get(path + job["jobId"], headers={"X-MS-CLIENT-PRINCIPAL-ID": "forged"})
                self.assertEqual(response.status_code, 404)
            self.assertEqual((await first.get("/api/studio/history")).json()["scope"], "session")


if __name__ == "__main__":
    unittest.main()
