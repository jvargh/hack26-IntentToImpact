"""Fixture-only ACA tests; no server, Azure CLI, or model request is started."""

import asyncio
import base64
import json
import os
import secrets
import shutil
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))
sys.path.insert(0, str(Path(__file__).parent))

from test_model import FakeModel, request
from studio.app import COOKIE, ORIGIN, SESSION_TTL, create_app
from studio.bundle import Blocked, _compiler
from studio.hosted_lock import HostedWorkerLock
from studio.hosting import HostedConfig, load_hosted_config
from studio.model_client import FoundryModelClient, SUBSCRIPTION
from studio import serve

PUBLIC_ORIGIN = "https://studio.greenfield.eastus.azurecontainerapps.io"
OID = "11111111-1111-4111-8111-111111111111"
OTHER_OID = "22222222-2222-4222-8222-222222222222"
TENANT = "33333333-3333-4333-8333-333333333333"
CLIENT_ID = "44444444-4444-4444-8444-444444444444"


def principal_headers(oid=OID, tenant=TENANT, **changes):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "http://schemas.microsoft.com/identity/claims/objectidentifier", "val": oid},
            {"typ": "http://schemas.microsoft.com/identity/claims/tenantid", "val": tenant},
        ],
    }
    principal.update(changes)
    return {
        "X-MS-CLIENT-PRINCIPAL": base64.b64encode(json.dumps(principal).encode()).decode(),
        "X-MS-CLIENT-PRINCIPAL-ID": oid,
        "X-Studio-Client": "1",
    }


class HostingFixture:
    def make_config(self):
        self.folder = ROOT / ".intent-to-impact" / "studio" / "tests" / secrets.token_hex(12)
        self.folder.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.folder)
        self.env_patch = patch.dict(os.environ, {"STUDIO_HOSTING": ""})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.runs = self.folder / "runs"
        self.runs.mkdir()
        return HostedConfig(PUBLIC_ORIGIN, frozenset({OID}), TENANT, CLIENT_ID,
                            self.runs, Path(sys.executable).resolve())

    def environment(self):
        return {
            "STUDIO_HOSTING": "aca",
            "STUDIO_PUBLIC_ORIGIN": self.config.public_origin,
            "STUDIO_ALLOWED_OBJECT_IDS": ",".join(sorted(self.config.allowed_object_ids)),
            "STUDIO_TENANT_ID": self.config.tenant_id,
            "STUDIO_MANAGED_IDENTITY_CLIENT_ID": self.config.managed_identity_client_id,
            "STUDIO_DATA_ROOT": str(self.config.data_root),
            "STUDIO_BICEP_PATH": str(self.config.bicep_path),
        }


class ConfigTests(HostingFixture, unittest.TestCase):
    def setUp(self):
        self.config = self.make_config()

    def test_public_demo_is_explicit_and_invalid_modes_fail_closed(self):
        self.assertEqual(load_hosted_config(self.environment()).auth_mode, "entra")
        self.assertEqual(load_hosted_config({**self.environment(), "STUDIO_AUTH_MODE": "anonymous-demo"}).auth_mode, "anonymous-demo")
        with self.assertRaises(ValueError):
            load_hosted_config({**self.environment(), "STUDIO_AUTH_MODE": "disabled"})
        self.assertIsNone(load_hosted_config({"STUDIO_AUTH_MODE": "anonymous-demo"}))

    def test_only_explicit_aca_enables_hosting(self):
        self.assertIsNone(load_hosted_config({}))
        self.assertIsNone(load_hosted_config({"STUDIO_PUBLIC_ORIGIN": PUBLIC_ORIGIN}))
        self.assertIsNone(load_hosted_config({"STUDIO_HOSTING": "local"}))
        self.assertEqual(load_hosted_config(self.environment()), self.config)
        for value in ("ACA", "acaa", " aca"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                load_hosted_config({"STUDIO_HOSTING": value})

    def test_missing_settings_fail_closed(self):
        for name in self.environment():
            if name == "STUDIO_HOSTING":
                continue
            env = self.environment()
            del env[name]
            with self.subTest(name=name), self.assertRaises(ValueError):
                load_hosted_config(env)

    def test_malformed_origins_and_placeholder_fail_closed(self):
        for origin in (
            "http://studio.greenfield.eastus.azurecontainerapps.io",
            PUBLIC_ORIGIN + "/", PUBLIC_ORIGIN + ":443", PUBLIC_ORIGIN + "?x=1",
            PUBLIC_ORIGIN + "#x", PUBLIC_ORIGIN.upper(), "https://127.0.0.1",
            "https://<app-fqdn>", "https://your-app.azurecontainerapps.io",
            "https://studio.example.com", "https://studio.invalid", "https://localhost",
            "https://user@studio.greenfield.eastus.azurecontainerapps.io",
        ):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                replace(self.config, public_origin=origin)

    def test_invalid_uuid_sets_and_paths_fail_closed(self):
        changes = [
            {"STUDIO_ALLOWED_OBJECT_IDS": ""}, {"STUDIO_ALLOWED_OBJECT_IDS": "*"},
            {"STUDIO_ALLOWED_OBJECT_IDS": OID + ","}, {"STUDIO_ALLOWED_OBJECT_IDS": OID + ", " + OTHER_OID},
            {"STUDIO_ALLOWED_OBJECT_IDS": OID + "," + OID},
            {"STUDIO_TENANT_ID": "wrong"}, {"STUDIO_MANAGED_IDENTITY_CLIENT_ID": "wrong"},
            {"STUDIO_DATA_ROOT": "relative"}, {"STUDIO_DATA_ROOT": str(self.folder / "absent")},
            {"STUDIO_DATA_ROOT": str(self.config.bicep_path)},
            {"STUDIO_BICEP_PATH": "bicep"}, {"STUDIO_BICEP_PATH": str(self.folder / "missing")},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                load_hosted_config({**self.environment(), **change})
        with patch("studio.hosting.os.access", return_value=False), self.assertRaises(ValueError):
            load_hosted_config(self.environment())

    def test_production_factory_requires_lock_before_recovery(self):
        with patch.dict(os.environ, self.environment()), patch("studio.app.StudioService") as service:
            with self.assertRaisesRegex(RuntimeError, "worker lock"):
                create_app()
            service.assert_not_called()

    def test_configured_compiler_retains_version_floor_and_never_falls_back(self):
        result = SimpleNamespace(stdout="Bicep CLI version 0.47.16 (fixture)", stderr="", returncode=0)
        with patch("studio.bundle.subprocess.run", return_value=result) as run:
            path, version, receipt = _compiler(self.config.bicep_path)
        self.assertEqual(path, self.config.bicep_path)
        self.assertIn("0.47.16", version)
        self.assertEqual(receipt["exitCode"], 0)
        self.assertEqual(run.call_args.args[0], [str(self.config.bicep_path), "--version"])
        self.assertFalse(run.call_args.kwargs["shell"])
        for result in (
            SimpleNamespace(stdout="Bicep CLI version 0.1.0", stderr="", returncode=0),
            SimpleNamespace(stdout="unexpected", stderr="", returncode=0),
            SimpleNamespace(stdout="Bicep CLI version 0.47.16", stderr="", returncode=1),
        ):
            with patch("studio.bundle.subprocess.run", return_value=result) as run, self.assertRaises(Blocked):
                _compiler(self.config.bicep_path)
            self.assertEqual(run.call_count, 1)
        with self.assertRaises(Blocked):
            _compiler(Path("bicep"))

    def test_hosted_environment_selects_only_configured_compiler(self):
        result = SimpleNamespace(stdout="Bicep CLI version 0.47.16", stderr="", returncode=0)
        with patch.dict(os.environ, self.environment()), patch("studio.bundle.subprocess.run", return_value=result) as run:
            self.assertEqual(_compiler()[0], self.config.bicep_path)
        self.assertEqual(run.call_count, 1)

    def test_local_compiler_paths_ignore_hosted_path_override(self):
        result = SimpleNamespace(stdout="Bicep CLI version 0.47.16", stderr="", returncode=0)
        with patch.dict(os.environ, {"STUDIO_BICEP_PATH": "ignored"}), \
                patch("studio.bundle.COMPILER_PATHS", (self.config.bicep_path,)), \
                patch("studio.bundle.subprocess.run", return_value=result):
            self.assertEqual(_compiler()[0], self.config.bicep_path)

    def test_serve_acquires_before_factory_and_holds_lock_through_uvicorn(self):
        lock = Mock()
        lock.acquired = False

        def enter():
            lock.acquired = True
            return lock

        def exit_lock(*_):
            lock.acquired = False

        context = Mock(__enter__=Mock(side_effect=enter), __exit__=Mock(side_effect=exit_lock))

        def factory(**kwargs):
            self.assertTrue(lock.acquired)
            self.assertIs(kwargs["hosted_lock"], lock)
            self.assertEqual(kwargs["hosted_config"], self.config)
            return "fixture-app"

        def run(app, **kwargs):
            self.assertTrue(lock.acquired)
            self.assertEqual(app, "fixture-app")
            self.assertEqual((kwargs["host"], kwargs["port"]), ("0.0.0.0", 8080))
            self.assertIs(kwargs["proxy_headers"], False)

        with patch("studio.serve.load_hosted_config", return_value=self.config), \
                patch("studio.serve.HostedWorkerLock", return_value=context), \
                patch("studio.serve.create_app", side_effect=factory), \
                patch("studio.serve.uvicorn.run", side_effect=run), \
                patch("studio.serve.load_history_scope", side_effect=AssertionError("Local setting used")):
            serve.main()
        self.assertFalse(lock.acquired)

    def test_local_entrypoint_does_not_lock_or_change_binding(self):
        with patch("studio.serve.HostedWorkerLock", side_effect=AssertionError("Local lock")), \
                patch("studio.serve.load_history_scope", return_value="session"), \
                patch("studio.serve.create_app", return_value="local-app") as factory, \
                patch("studio.serve.uvicorn.run") as run:
            serve.main()
        factory.assert_called_once_with(history_scope="session")
        self.assertEqual((run.call_args.kwargs["host"], run.call_args.kwargs["port"]), ("127.0.0.1", 5173))
        self.assertIs(run.call_args.kwargs["proxy_headers"], False)

    @unittest.skipUnless(sys.platform == "linux", "Real flock requires Linux; run in the ACA image.")
    def test_real_linux_lock_excludes_second_worker_and_releases_on_exit(self):
        first, second = HostedWorkerLock(self.config), HostedWorkerLock(self.config)
        self.assertFalse(first.ready())
        with first:
            self.assertTrue(first.ready())
            with self.assertRaisesRegex(RuntimeError, "single-worker lock"):
                with second:
                    self.fail("Second worker entered")
        self.assertFalse(first.ready())
        with second:
            self.assertTrue(second.ready())
        self.assertTrue((self.runs / ".studio-worker.lock").is_file())


class HostedApiTests(HostingFixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = self.make_config()
        self.dist = self.folder / "dist"
        self.dist.mkdir()
        (self.dist / "index.html").write_text("<html>hosted fixture</html>", encoding="utf-8")
        (self.dist / "app.js").write_text("export default 1;", encoding="utf-8")
        self.lock = SimpleNamespace(config=self.config, acquired=True, ready=lambda: True)
        self.model = FakeModel()
        self.app = create_app(static_root=self.dist, model=self.model,
                              hosted_config=self.config, hosted_lock=self.lock)
        self.client = self.new_client(principal_headers())
        self.addAsyncCleanup(self.client.aclose)
        self.addAsyncCleanup(self.app.state.service.shutdown)

    def new_client(self, headers=None, app=None, base_url=PUBLIC_ORIGIN):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app or self.app, client=("10.0.0.3", 42000)),
                                 base_url=base_url, headers=headers or {})

    async def test_https_session_secure_cookie_and_workspace_history(self):
        response = await self.client.get("/api/studio/session")
        self.assertEqual(response.status_code, 200, response.text)
        for attribute in ("Secure", "HttpOnly", "SameSite=strict", f"Max-Age={SESSION_TTL}", "Path=/api/studio"):
            self.assertIn(attribute, response.headers["set-cookie"])
        self.assertEqual(self.app.state.service.history_scope, "workspace")
        self.assertEqual((await self.client.get("/api/studio/session")).json(), response.json())
        self.assertEqual((await self.client.get("/")).status_code, 200)
        self.assertEqual((await self.client.get("/app.js")).status_code, 200)

    async def test_anonymous_requests_and_replayed_cookie_never_access_data(self):
        await self.client.get("/api/studio/session")
        async with self.new_client({"X-Studio-Client": "1"}) as anonymous:
            anonymous.cookies.update(self.client.cookies)
            for path in ("/api/studio/session", "/api/studio/history", "/api/studio/health",
                         "/api/studio/history/missing/download", "/app.js"):
                response = await anonymous.get(path)
                self.assertEqual(response.status_code, 401, (path, response.text))
                self.assertNotIn("set-cookie", response.headers)
            response = await anonymous.get("/", headers={"Accept": "text/html"})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["location"], "/.auth/login/aad")
            self.assertEqual((await anonymous.post("/api/studio/analyses", json=request())).status_code, 401)
        self.assertEqual(self.model.calls, [])
        self.assertEqual(self.app.state.service.jobs, {})

    async def test_wrong_principals_tenants_idp_and_header_mismatch_are_forbidden(self):
        headers = [
            principal_headers(oid=OTHER_OID), principal_headers(tenant=OTHER_OID),
            principal_headers(auth_typ="github"),
            {**principal_headers(), "X-MS-CLIENT-PRINCIPAL-ID": OTHER_OID},
            {**principal_headers(), "X-MS-CLIENT-PRINCIPAL-IDP": "github"},
            {**principal_headers(), "X-MS-CLIENT-PRINCIPAL": "not-base64!"},
            {"X-MS-CLIENT-PRINCIPAL-ID": OID},
            {"X-MS-CLIENT-PRINCIPAL": principal_headers()["X-MS-CLIENT-PRINCIPAL"]},
            principal_headers(claims=[]), principal_headers(claims="invalid"),
            principal_headers(claims=[{"typ": "oid", "val": OID}, {"typ": "tid", "val": TENANT},
                                     {"typ": "tid", "val": OTHER_OID}]),
        ]
        for identity in headers:
            async with self.new_client(identity) as client:
                for path in ("/", "/api/studio/session"):
                    response = await client.get(path)
                    self.assertEqual(response.status_code, 403, response.text)
                    self.assertNotIn("set-cookie", response.headers)

    async def test_short_claim_names_are_supported(self):
        headers = principal_headers(claims=[{"typ": "oid", "val": OID}, {"typ": "tid", "val": TENANT}])
        async with self.new_client(headers) as client:
            self.assertEqual((await client.get("/api/studio/session")).status_code, 200)

    async def test_host_origin_and_forwarding_are_exact(self):
        for headers in (
            {"Host": "127.0.0.1:8080"}, {"Host": self.config.host + ":443"},
            {"Origin": ORIGIN}, {"Origin": PUBLIC_ORIGIN + "/"},
            {"Forwarded": "host=" + self.config.host}, {"X-Original-URL": "/healthz"},
            {"X-Forwarded-Unknown": "443"}, {"X-Rewrite-URL": "/"},
            {"X-Forwarded-Proto": "http"}, {"X-Forwarded-Proto": "https,http"},
            {"X-Forwarded-Host": "foreign.azurecontainerapps.io"},
            {"X-Forwarded-For": "not-an-ip"},
        ):
            with self.subTest(headers=headers):
                self.assertEqual((await self.client.get("/api/studio/session", headers=headers)).status_code, 403)
        response = await self.client.get("/api/studio/session", headers={
            "Origin": PUBLIC_ORIGIN, "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": self.config.host, "X-Forwarded-For": "203.0.113.2, 10.0.0.5, ::1",
            "X-Forwarded-Port": "443", "X-Forwarded-Client-Cert": "ignored-envoy-metadata",
            "X-Forwarded-Path": "/untrusted-and-unused-path",
        })
        self.assertEqual(response.status_code, 200)

    async def test_duplicate_security_and_auth_headers_are_rejected(self):
        for name, value in (
            ("host", self.config.host), ("origin", PUBLIC_ORIGIN),
            ("cookie", "x=y"), ("x-csrf-token", "x"), ("x-studio-client", "1"),
            ("x-ms-client-principal", principal_headers()["X-MS-CLIENT-PRINCIPAL"]),
            ("x-ms-client-principal-id", OID), ("authorization", "Bearer fixture"),
            ("x-forwarded-for", "10.0.0.1"), ("x-forwarded-proto", "https"),
        ):
            response = await self.client.get("/api/studio/session", headers=[(name, value), (name, value)])
            self.assertEqual(response.status_code, 400, (name, response.text))

    async def test_csrf_client_header_and_session_required_then_valid_analysis(self):
        session = await self.client.get("/api/studio/session")
        csrf = session.json()["csrfToken"]
        for headers in ({}, {"Origin": PUBLIC_ORIGIN}, {"X-CSRF-Token": csrf},
                        {"Origin": PUBLIC_ORIGIN, "X-CSRF-Token": "wrong"},
                        {"Origin": PUBLIC_ORIGIN, "X-CSRF-Token": csrf, "X-Studio-Client": ""}):
            response = await self.client.post("/api/studio/analyses", json=request(), headers=headers)
            self.assertEqual(response.status_code, 403)
        async with self.new_client(principal_headers()) as fresh:
            self.assertEqual((await fresh.get("/api/studio/history")).status_code, 401)
        response = await self.client.post("/api/studio/analyses", json=request(),
                                          headers={"Origin": PUBLIC_ORIGIN, "X-CSRF-Token": csrf})
        self.assertEqual(response.status_code, 202, response.text)
        await asyncio.gather(*list(self.app.state.service.tasks))
        self.assertEqual([call["role"] for call in self.model.calls], ["synthesis", "assurance"])
        async with self.new_client(principal_headers()) as fresh:
            await fresh.get("/api/studio/session")
            history = await fresh.get("/api/studio/history")
            self.assertEqual(history.status_code, 200)
            self.assertIn(response.json()["jobId"], history.text)

    async def test_healthz_is_minimal_and_bypasses_auth_host_and_session(self):
        async with self.new_client(base_url="http://10.0.0.8:8080") as probe:
            response = await probe.get("/healthz")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"ready": True})
            self.assertNotIn("set-cookie", response.headers)
            self.assertEqual((await probe.head("/healthz")).content, b"")
            self.lock.ready = lambda: False
            self.assertEqual((await probe.get("/healthz")).status_code, 503)
            self.assertEqual((await probe.head("/healthz")).status_code, 503)
            self.assertEqual((await probe.post("/healthz")).status_code, 403)
        self.assertEqual(self.app.state.sessions.items, {})

    async def test_unlocked_injected_factory_never_reports_ready(self):
        app = create_app(model=FakeModel(), hosted_config=self.config)
        self.addAsyncCleanup(app.state.service.shutdown)
        async with self.new_client(app=app) as client:
            self.assertEqual((await client.get("/healthz")).status_code, 503)

    async def test_local_mode_does_not_trust_identity_or_proxy_and_cookie_is_unchanged(self):
        app = create_app(self.folder / "local-runs", self.dist, FakeModel())
        self.addAsyncCleanup(app.state.service.shutdown)
        async with self.new_client(principal_headers(), app=app, base_url=ORIGIN) as remote:
            self.assertEqual((await remote.get("/api/studio/session")).status_code, 403)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 42000)),
                                     base_url=ORIGIN, headers={"X-Studio-Client": "1"}) as local:
            response = await local.get("/api/studio/session")
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("Secure", response.headers["set-cookie"])
            self.assertEqual(app.state.service.history_scope, "session")
            self.assertEqual((await local.get("/api/studio/session", headers={"X-Forwarded-Proto": "https"})).status_code, 403)


class ManagedAuthTests(HostingFixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = self.make_config()

    async def test_hosted_credential_uses_explicit_identity_without_cli_preflight(self):
        factory = Mock(return_value="fixture-credential")
        model = FoundryModelClient(hosted_config=self.config, credential_factory=factory)
        with patch("studio.model_client.verify_identity", side_effect=AssertionError("CLI called")):
            self.assertEqual(await model._credential(), "fixture-credential")
        factory.assert_called_once_with(client_id=CLIENT_ID)

    async def test_hosted_default_credential_is_managed_identity(self):
        with patch("azure.identity.aio.ManagedIdentityCredential") as credential, \
                patch("studio.model_client.verify_identity", side_effect=AssertionError("CLI called")):
            self.assertIs(await FoundryModelClient(hosted_config=self.config)._credential(), credential.return_value)
        credential.assert_called_once_with(client_id=CLIENT_ID)

    async def test_local_credential_keeps_preflight_and_subscription(self):
        factory = Mock(return_value="fixture-credential")
        with patch("studio.model_client.verify_identity") as preflight:
            self.assertEqual(await FoundryModelClient(credential_factory=factory)._credential(), "fixture-credential")
        preflight.assert_called_once_with()
        factory.assert_called_once_with(subscription=SUBSCRIPTION, process_timeout=20)


if __name__ == "__main__":
    unittest.main()
