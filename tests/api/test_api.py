"""Real local HTTP routes over isolated CaseStore state; scenario is fixture input only."""

from copy import deepcopy
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))

from fastapi.testclient import TestClient
from api.app import Config, EFFECTS, IDENTITY, POLICY_REGISTRY, SCOPE, create_app
from api.projection import issue_context_action
from reporting.continuity.graph import build_graph
from state.case_store import seal
from tools.contracts.integrity import semantic_checksum, validate_reference_integrity
from tools.contracts.validate import validate_contract

TOKEN = "synthetic-local-api-test-token-not-a-real-credential"
ORIGIN = "http://127.0.0.1:8765"


class ApiTests(unittest.TestCase):
    def setUp(self):
        EFFECTS.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="test-api-", dir=EFFECTS)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "runs"
        self.config = Config(access_token=TOKEN, data_root=self.root)
        self.app = create_app(self.config)
        self.service = self.app.state.service
        self.client = TestClient(self.app, base_url=ORIGIN, client=("127.0.0.1", 51000))
        self.addCleanup(self.client.close)
        # Stored local setup input, not a canned P01 response or API-create proof.
        self.case_id = "CASE-" + "1" * 32
        manifest = json.loads((ROOT / "contracts" / "examples" / "1.0.0" / "run-manifest.json").read_text())
        manifest.update(runId="RUN-" + "1" * 32, caseId=self.case_id, artifactId="ART-API-TEST-RUN",
                        scope=deepcopy(SCOPE), rootId="ROOT-LOOPBACK-API", configId="CONFIG-LOOPBACK-API",
                        runMode="live", purpose="test", **self.service.identity)
        self.run = self.service.store.create_run(manifest)
        self.case = self.service.store.create_case(self.run["runId"])
        login = self.client.post("/session", headers={"Origin": ORIGIN, "X-Local-Access-Token": TOKEN})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json()["identity"], IDENTITY)
        self.csrf = login.json()["csrfToken"]
        self.headers = {"Origin": ORIGIN, "X-CSRF-Token": self.csrf}

    def create_body(self, key="api-create-example"):
        return {"schemaVersion": "1.0.0", "scenario": self.service.identity, "idempotencyKey": key}

    def ack_body(self, case=None, run=None, key="context-example"):
        case, run = case or self.case, run or self.run
        return {"schemaVersion": "1.0.0", "scenario": self.service.identity,
                "runManifestChecksum": run["stateChecksum"], "expectedRevision": case["logicalRevision"],
                "idempotencyKey": key, "acknowledgement": "known-scenario-context-only"}

    def experience(self):
        return self.client.get(f"/cases/{self.case_id}/experience")

    def assert_error(self, response, status=None):
        if status is not None:
            self.assertEqual(response.status_code, status)
        self.assertGreaterEqual(response.status_code, 400)
        validate_contract(response.json(), "E07")
        self.assertNotIn(TOKEN, response.text)
        self.assertNotIn(self.csrf, response.text)

    def test_real_read_builds_valid_unknown_joined_projection(self):
        response = self.experience()
        self.assertEqual(response.status_code, 200)
        overview = response.json()
        validate_contract(overview, "P01")
        validate_reference_integrity([self.case, overview], {self.run["runId"]: self.run}, self.service.scenario)
        self.assertEqual(overview["logicalRevision"], 0)
        self.assertEqual(overview["operationsRisk"]["riskState"], "unknown")
        self.assertIsNone(overview["operationsRisk"]["binding"])
        self.assertIsNone(overview["coverage"]["verifiedCount"])
        self.assertIsNone(overview["coverage"]["applicableCount"])
        self.assertEqual(len(overview["coverage"]["rows"]), 8)
        self.assertTrue(all(r["status"] == "unknown" and not r["confirmed"] for r in overview["coverage"]["rows"]))
        self.assertTrue(any(e["status"] == "gap" for e in overview["continuityGraph"]["edges"]))
        self.assertEqual(overview["scenarioOrigin"], "fixture")
        self.assertEqual(overview["scenario"]["scenarioId"], "DEMO-CASE-CLAIMS-V2")
        self.assertTrue(any(b["code"] == "historical-scenario" for b in overview["blockers"]))
        self.assertEqual(response.headers["x-demo-actor"], "demo-human")

    def test_read_uses_current_persisted_revision_not_fixture_snapshot(self):
        case = self.service.store.read_case(self.run["runId"])
        self.service.store.commit(self.run["runId"], 0, case)
        response = self.experience()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["logicalRevision"], 1)
        self.assertEqual(response.json()["derivedFrom"]["case"],
                         self.service.store.read_case(self.run["runId"])["stateChecksum"])

    def test_unknown_graph_delegates_to_shared_projection_without_runtime_proof(self):
        with patch("api.projection.build_graph", wraps=build_graph) as shared:
            response = self.experience()
        self.assertEqual(response.status_code, 200)
        shared.assert_called_once()
        overview = response.json()
        arguments = shared.call_args.kwargs
        self.assertEqual(arguments, {
            "run": self.run, "scenario": self.service.scenario, "documents": [],
            "promise_id": "CP-01", "logical_revision": self.case["logicalRevision"],
            "as_of": overview["asOf"], "evaluation_id": None,
            "restoration_pending": False, "external_references": [],
        })
        graph = overview["continuityGraph"]
        self.assertEqual(graph, build_graph(**arguments))
        validate_contract(graph, "P06")
        self.assertEqual(graph["evidence"], [])
        self.assertEqual(graph["artifactRefs"], [])
        self.assertEqual(graph["allowedActions"], [])
        self.assertEqual(
            {node["source"]["expectedContractId"] for node in graph["nodes"] if node["source"]["kind"] == "gap"},
            {"D14", "D17"},
        )
        self.assertFalse(any(node["source"]["kind"] == "artifact" for node in graph["nodes"]))
        self.assertTrue(all(not row["confirmed"] and row["status"] == "unknown"
                            for row in overview["coverage"]["rows"]))

    def test_invalid_case_returns_precontext_e07(self):
        response = self.client.get("/cases/invalid/experience")
        self.assert_error(response, 404)
        self.assertNotIn("caseId", response.json())
        self.assertIn("diagnosticId", response.json())

    def test_session_cookie_and_matching_csrf_required(self):
        anonymous = TestClient(self.app, base_url=ORIGIN, client=("127.0.0.1", 51001))
        self.addCleanup(anonymous.close)
        self.assert_error(anonymous.get(f"/cases/{self.case_id}/experience"), 401)
        self.assert_error(self.client.post("/cases", json=self.create_body(), headers={"Origin": ORIGIN}), 403)
        self.assert_error(self.client.post("/cases", json=self.create_body(),
                                          headers={"Origin": ORIGIN, "X-CSRF-Token": "wrong"}), 403)

    def test_host_origin_peer_and_forwarded_headers_are_strict(self):
        for headers in ({"Host": "localhost:8765"}, {"Origin": "http://attacker.example"},
                        {"Origin": ORIGIN + "/"}, {"X-Forwarded-For": "127.0.0.1"}):
            self.assert_error(self.client.get(f"/cases/{self.case_id}/experience", headers=headers), 403)
        external = TestClient(self.app, base_url=ORIGIN, client=("192.0.2.1", 51001))
        self.addCleanup(external.close)
        self.assert_error(external.post("/session", headers={"Origin": ORIGIN, "X-Local-Access-Token": TOKEN}), 403)
        self.assert_error(self.client.post("/cases", json=self.create_body(),
                                          headers={"X-CSRF-Token": self.csrf}), 403)

    def test_duplicate_security_headers_and_cookies_deny(self):
        self.assert_error(self.client.get(f"/cases/{self.case_id}/experience",
                                          headers=[("host", "127.0.0.1:8765"), ("host", "127.0.0.1:8765")]), 403)
        value = self.client.cookies.get("iti_session")
        self.assert_error(self.client.get(f"/cases/{self.case_id}/experience",
                                          headers={"Cookie": f"iti_session={value}; iti_session={value}"}), 401)
        self.assert_error(self.client.post("/cases", json=self.create_body(),
                                          headers=[("Origin", ORIGIN), ("X-CSRF-Token", self.csrf),
                                                   ("X-CSRF-Token", self.csrf)]), 403)

    def test_expired_or_restarted_sessions_are_not_reused(self):
        for session in self.app.state.sessions.values():
            session["expires"] = 0
        self.assert_error(self.experience(), 401)

    def test_missing_and_bad_bootstrap_token_cannot_mint_session(self):
        self.assert_error(self.client.post("/session", headers={"Origin": ORIGIN}), 401)
        self.assert_error(self.client.post("/session", headers={"Origin": ORIGIN, "X-Local-Access-Token": "wrong"}), 401)

    def test_cookie_flags_and_no_store(self):
        login = self.client.post("/session", headers={"Origin": ORIGIN, "X-Local-Access-Token": TOKEN})
        self.assertEqual(login.status_code, 200)
        cookie = login.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=strict", cookie)
        self.assertEqual(login.headers["cache-control"], "no-store")

    def test_extra_authority_mode_scope_path_fields_fail_create(self):
        before = self.service.store.read_case(self.run["runId"])
        for field, value in (("actorId", "demo-human"), ("channel", "browser"), ("runMode", "live"),
                             ("purpose", "hero"), ("scope", SCOPE), ("path", "..\\outside"),
                             ("transport", "human"), ("caller", {"callerClass": "human"})):
            with self.subTest(field=field):
                response = self.client.post("/cases", json={**self.create_body(), field: value}, headers=self.headers)
                self.assert_error(response, 400)
        self.assertEqual(self.service.store.read_case(self.run["runId"]), before)

    def test_malformed_duplicate_json_and_oversized_body_are_contract_errors(self):
        for payload in ("{", '{"schemaVersion":"1.0.0","schemaVersion":"1.0.0"}', '{"value":NaN}'):
            self.assert_error(self.client.post("/cases", content=payload,
                                              headers={**self.headers, "Content-Type": "application/json"}), 400)
        self.assert_error(self.client.post("/cases", content=" " * 16385,
                                          headers={**self.headers, "Content-Type": "application/json"}), 413)

    def test_missing_policy_seams_fail_closed_without_writing(self):
        registry = json.loads(POLICY_REGISTRY.read_text(encoding="utf-8"))
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        for capability in ("create-case", "acknowledge-run-context"):
            missing = deepcopy(registry)
            missing["capabilities"].pop(capability, None)
            for failure in ("missing", "malformed", "unavailable"):
                with self.subTest(capability=capability, failure=failure):
                    with patch("api.app.POLICY_REGISTRY") as registry_read:
                        if failure == "unavailable":
                            registry_read.read_text.side_effect = OSError("injected unavailable registry")
                        else:
                            registry_read.read_text.return_value = json.dumps(missing) if failure == "missing" else "{"
                        if capability == "create-case":
                            response = self.client.post("/cases", json=self.create_body(), headers=self.headers)
                        else:
                            action = issue_context_action(self.case, self.service.scenario)
                            response = self.client.post(f"/cases/{self.case_id}/actions/{action}",
                                                        json=self.ack_body(), headers=self.headers)
                            if failure == "missing":
                                self.assertEqual(self.experience().json()["allowedActions"], [])
                        self.assert_error(response, 503)
                    after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
                    self.assertEqual(after, before)
                    self.assertEqual(self.service.store.read_case(self.run["runId"]), self.case)

    def test_create_persists_case_and_idempotent_event_receipt(self):
        first = self.client.post("/cases", json=self.create_body(), headers=self.headers)
        self.assertEqual(first.status_code, 201)
        validate_contract(first.json(), "E04")
        duplicate = self.client.post("/cases", json=self.create_body(), headers=self.headers)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json(), first.json())
        read = self.client.get(first.headers["location"])
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json()["logicalRevision"], 1)
        changed = deepcopy(self.create_body())
        changed["scenario"]["scenarioHash"] = "sha256:" + "f" * 64
        self.assert_error(self.client.post("/cases", json=changed, headers=self.headers), 409)

    def test_context_ack_once_keeps_business_promises_and_runtime_unconfirmed(self):
        overview = self.experience().json()
        action = overview["allowedActions"][0]["actionId"]
        response = self.client.post(f"/cases/{self.case_id}/actions/{action}",
                                    json=self.ack_body(), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        validate_contract(response.json(), "E04")
        self.assertEqual(response.json()["eventType"], "run-context-acknowledged")
        duplicate = self.client.post(f"/cases/{self.case_id}/actions/{action}",
                                     json=self.ack_body(), headers=self.headers)
        self.assertEqual(duplicate.json(), response.json())
        self.assertEqual(duplicate.headers["x-idempotent-replay"], "true")
        conflicting = {**self.ack_body(), "runManifestChecksum": "sha256:" + "f" * 64}
        conflict = self.client.post(f"/cases/{self.case_id}/actions/{action}",
                                   json=conflicting, headers=self.headers)
        self.assert_error(conflict, 409)
        self.assertEqual(conflict.json()["code"], "idempotency-conflict")
        stale = self.client.post(f"/cases/{self.case_id}/actions/{action}",
                                json=self.ack_body(key="new-context-request"), headers=self.headers)
        self.assert_error(stale, 409)
        self.assertEqual(stale.json()["code"], "stale-revision")
        case = self.service.store.read_case(self.run["runId"])
        self.assertEqual(case["logicalRevision"], 1)
        self.assertEqual(len(case["events"]), 1)
        current = self.experience().json()
        self.assertEqual(current["allowedActions"], [])
        self.assertTrue(all(not row["confirmed"] and row["status"] == "unknown" for row in current["coverage"]["rows"]))
        self.assertEqual(case["lifecycleState"], "Draft")

    def test_shared_unicode_hashing_and_unicode_creation_key_replay(self):
        self.assertEqual(semantic_checksum({"value": "contexte-\u00e9\u6f22"}),
                         seal({"value": "contexte-\u00e9\u6f22"})["stateChecksum"])
        payload = self.create_body(key="contexte-\u00e9\u6f22")
        first = self.client.post("/cases", json=payload, headers=self.headers)
        self.assertEqual(first.status_code, 201)
        duplicate = self.client.post("/cases", json=payload, headers=self.headers)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(first.json(), duplicate.json())

    def test_unauthorized_action_and_tampered_mode_do_not_mutate(self):
        unauthorized = self.client.post(f"/cases/{self.case_id}/actions/approve-design",
                                        json=self.ack_body(), headers=self.headers)
        self.assert_error(unauthorized, 403)
        response = self.client.post(f"/cases/{self.case_id}/actions/approve-design",
                                    json={**self.ack_body(), "runMode": "live"}, headers=self.headers)
        self.assert_error(response, 400)
        self.assertEqual(self.service.store.read_case(self.run["runId"]), self.case)

    def test_artifact_read_is_checksum_bound_and_case_reachable(self):
        reference = self.service.store.put_artifact(self.run["runId"], {
            "artifactId": "ART-API-METADATA", "runId": self.run["runId"], "caseId": self.case_id,
            "scope": SCOPE, "artifactType": "local-api-create", "requestChecksum": "sha256:" + "a" * 64,
        })
        path = f"/cases/{self.case_id}/artifacts/{reference['artifactId']}"
        self.assert_error(self.client.get(path, params={"checksum": reference["checksum"]}), 404)
        changed = deepcopy(self.case)
        changed["sections"]["api-create"] = reference
        self.service.store.commit(self.run["runId"], 0, changed)
        response = self.client.get(path, params={"checksum": reference["checksum"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["stateChecksum"], reference["checksum"])
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assert_error(self.client.get(path, params={"checksum": "sha256:" + "f" * 64}), 404)
        self.assert_error(self.client.get(path, params={"checksum": "..\\outside"}), 400)

    def test_other_case_artifact_cannot_be_read_by_id(self):
        other = deepcopy(self.run)
        other.update(runId="RUN-" + "2" * 32, caseId="CASE-" + "2" * 32, artifactId="ART-OTHER-RUN")
        other = self.service.store.create_run(other)
        case = self.service.store.create_case(other["runId"])
        reference = self.service.store.put_artifact(other["runId"], {
            "artifactId": "ART-OTHER-CASE", "runId": other["runId"], "caseId": other["caseId"],
            "scope": SCOPE, "content": "synthetic other case",
        })
        case["sections"]["api-create"] = reference
        self.service.store.commit(other["runId"], 0, case)
        response = self.client.get(f"/cases/{self.case_id}/artifacts/{reference['artifactId']}",
                                    params={"checksum": reference["checksum"]})
        self.assert_error(response, 404)

    def test_unimplemented_producer_section_is_not_silently_replaced_with_unknown(self):
        reference = self.service.store.put_artifact(self.run["runId"], {
            "artifactId": "ART-LATER-PRODUCER", "runId": self.run["runId"], "caseId": self.case_id,
            "scope": SCOPE, "content": "synthetic unimplemented producer",
        })
        case = deepcopy(self.case)
        case["sections"]["runtime-binding"] = reference
        self.service.store.commit(self.run["runId"], 0, case)
        self.assert_error(self.experience(), 409)

    def test_incomplete_api_creation_is_recovery_not_an_unknown_success(self):
        pending = deepcopy(self.run)
        suffix = "3" * 32
        pending.update(runId="RUN-" + suffix, caseId="CASE-" + suffix, artifactId="ART-RUN-" + suffix)
        pending = self.service.store.create_run(pending)
        self.service.store.create_case(pending["runId"])
        response = self.client.get(f"/cases/{pending['caseId']}/experience")
        self.assert_error(response, 503)
        self.assertEqual(response.json()["code"], "recovery-required")

    def test_path_traversal_unknown_queries_and_methods_fail(self):
        for path in ("/cases/..%5Coutside/experience", "/cases/invalid/artifacts/..%5Csecret?checksum=x"):
            self.assert_error(self.client.get(path))
        self.assert_error(self.client.get(f"/cases/{self.case_id}/experience?actorId=demo-human"), 400)
        self.assert_error(self.client.delete(f"/cases/{self.case_id}/experience", headers=self.headers), 405)

    def test_tampered_stored_case_fails_instead_of_returning_fixture(self):
        path = self.root / self.run["runId"] / "cases" / self.case_id / "case.json"
        value = json.loads(path.read_text())
        value["lifecycleState"] = "VerifiedRestoration"
        path.write_text(json.dumps(value), encoding="utf-8")
        self.assert_error(self.experience(), 409)

    def test_run_mode_mutation_even_resealed_is_rejected(self):
        path = self.root / self.run["runId"] / "run-manifest.json"
        changed = seal({**self.run, "runMode": "fixture"})
        path.write_text(json.dumps(changed), encoding="utf-8")
        self.assert_error(self.experience())

    def test_config_rejects_external_bind_and_outside_root(self):
        for origin in ("http://0.0.0.0:8765", "http://localhost:8765", "https://127.0.0.1:8765",
                       "http://127.0.0.1:8765/path"):
            with self.assertRaises(ValueError):
                Config(access_token=TOKEN, data_root=self.root, origin=origin)
        with self.assertRaises(ValueError):
            Config(access_token=TOKEN, data_root=ROOT)
        with self.assertRaises(ValueError):
            Config(access_token="short", data_root=self.root)

    def test_actual_loopback_process_starts_and_is_stopped(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        command = [sys.executable, "-B", str(ROOT / "apps" / "control-plane" / "api" / "serve.py"),
                   "--port", str(port), "--data-root", str(self.root)]
        process = subprocess.Popen(command, cwd=ROOT,
                                   env={**os.environ, "INTENT_API_ACCESS_TOKEN": TOKEN},
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 15
            received = None
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    urlopen(f"http://127.0.0.1:{port}/cases/{self.case_id}/experience", timeout=1)
                except HTTPError as error:
                    received = (error.code, json.loads(error.read()))
                    break
                except OSError:
                    time.sleep(0.1)
            self.assertIsNotNone(received)
            self.assertEqual(received[0], 401)
            validate_contract(received[1], "E07")
        finally:
            if process.poll() is None:
                process.terminate()  # Exact test-owned Popen PID, never a name-based process kill.
            process.wait(timeout=10)
            process.stderr.close()
        self.assertIsNotNone(process.returncode)


if __name__ == "__main__":
    unittest.main()
