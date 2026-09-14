"""Synthetic model fixtures; only TestRealCompiler provides live-local compiler evidence."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import unittest
from unittest.mock import patch
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("studio_bundle_under_test",
                                            ROOT / "apps" / "control-plane" / "studio" / "bundle.py")
bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle)
EVIDENCE_ROOT = ROOT / ".intent-to-impact" / "spikes" / "STUDIO-BUNDLE"


def fixture():
    """Deliberately fake model output, never a live-model integration receipt."""
    def component(identifier, kind, service):
        return {"id": identifier, "kind": kind, "service": service, "label": identifier,
                "responsibility": "Implement the requested workflow.", "requirementIds": ["r1", "r2"]}

    def edge(source, target):
        return {"id": f"{source}-{target}", "source": source, "target": target, "label": "Integrates"}

    def option(identifier, components, pairs):
        return {"id": identifier, "name": identifier, "rationale": "Synthetic unit-test fixture.",
                "tradeoffs": ["Application implementation is separate."], "costNotes": "No cost estimate.",
                "components": components, "connections": [edge(*p) for p in pairs]}

    web = option("web", [
        component("browser", "client", "Browser"), component("web", "appservice", "Azure App Service"),
        component("objects", "storage", "Azure Blob Storage"), component("vault", "keyvault", "Azure Key Vault"),
        component("partner", "external", "External HTTPS API"),
    ], [("browser", "web"), ("web", "objects"), ("web", "vault"), ("web", "partner")])
    events = option("events", [
        component("browser", "client", "Browser"), component("api", "appservice", "Azure App Service"),
        component("jobs", "servicebus", "Azure Service Bus"), component("worker", "functions", "Azure Functions"),
        component("results", "storage", "Azure Blob Storage"), component("vault", "keyvault", "Azure Key Vault"),
    ], [("browser", "api"), ("api", "jobs"), ("jobs", "worker"), ("worker", "results"), ("worker", "vault")])
    return {
        "resultId": "synthetic-test-result", "inputHash": hashlib.sha256(b"synthetic test input").hexdigest(),
        "createdAt": "2026-09-13T00:00:00Z", "origin": "live-model",
        "analysis": {
            "title": "Synthetic fixture; not live-model proof", "summary": "Tests only.",
            "businessProcess": ["Accept", "Process"],
            "requirements": [
                {"id": "r1", "text": "Accept requests", "sourceIds": ["prompt"]},
                {"id": "r2", "text": "Persist results", "sourceIds": ["document"]},
            ],
            "assumptions": [], "questions": [], "options": [web, events],
            "recommendedOptionId": "web",
            "review": [{"dimension": d, "severity": "warning", "finding": "Synthetic fixture",
                        "recommendation": "Run target preflight", "sourceIds": ["prompt"]}
                       for d in ["business", "security", "reliability", "performance", "cost",
                                 "integration", "compliance", "operations", "delivery"]],
            "changeSummary": "Synthetic test fixture",
        },
        "modelReceipts": [
            {"role": "synthesis", "model": "fake-unit-test-model", "responseId": "fake-synthesis", "durationMs": 0},
            {"role": "assurance", "model": "fake-unit-test-model", "responseId": "fake-assurance", "durationMs": 0},
        ],
        "sources": [{"id": "prompt", "name": "Synthetic prompt"}, {"id": "document", "name": "Synthetic document"}],
    }


def files(receipt):
    return {f["path"]: f["content"] for f in receipt["files"]}


class TestBundle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_root = EVIDENCE_ROOT / ("unit-" + uuid.uuid4().hex)

    @staticmethod
    def fake_run(command, **kwargs):
        """Process stub, explicitly NOT real compiler evidence."""
        if command[-1] == "--version":
            return subprocess.CompletedProcess(command, 0, "Bicep CLI version 0.47.16 (fake-unit-test)", "")
        Path(command[-1]).write_text(json.dumps({"resources": [{"type": "Fake.UnitTest/resource"}]}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    def generate(self, result=None, option="web"):
        with patch.object(bundle.subprocess, "run", side_effect=self.fake_run):
            return bundle.build_bundle(result or fixture(), option, self.output_root)

    def test_backend_canonical_service_tokens_are_valid_catalog_aliases(self):
        value = fixture()
        aliases = {"client": "Client", "appservice": "AppService", "functions": "Functions",
                   "storage": "Storage", "servicebus": "ServiceBus", "keyvault": "KeyVault"}
        for option in value["analysis"]["options"]:
            for component in option["components"]:
                if component["kind"] in aliases:
                    component["service"] = aliases[component["kind"]]
        receipt = self.generate(value, "events")
        self.assertEqual(receipt["status"], "compiled", receipt["diagnostics"])

    def test_existing_external_callback_preserves_authenticated_ingress(self):
        value = fixture()
        value["analysis"]["options"][0]["connections"].append({
            "id": "provider-callback", "source": "partner", "target": "web", "label": "Authenticated completion callback",
        })
        receipt = self.generate(value)
        self.assertEqual(receipt["status"], "compiled", receipt["diagnostics"])
        source = files(receipt)["main.bicep"]
        caller = bundle._symbol("partner") + "_callerClientId"
        self.assertIn(f"param {caller} string", source)
        self.assertIn("requireAuthentication: true", source)
        self.assertIn("unauthenticatedClientAction: 'Return401'", source)
        self.assertGreaterEqual(source.count(caller), 2)
        manifest = json.loads(files(receipt)["manifest.json"])
        callback = next(edge for edge in manifest["mapping"]["connections"] if edge["id"] == "provider-callback")
        self.assertEqual(callback["callerClientIdParameter"], caller)
        self.assertIn("adapter", callback["applicationPrerequisite"])
        parameters = json.loads(files(receipt)["main.parameters.json"])
        self.assertNotIn(caller, parameters["parameters"])

    def test_inbound_only_external_does_not_require_an_unused_api_url(self):
        value = fixture()
        option = value["analysis"]["options"][0]
        option["connections"] = [edge for edge in option["connections"] if edge["target"] != "partner"]
        option["connections"].append({"id": "callback-only", "source": "partner", "target": "web", "label": "Authenticated callback"})
        receipt = self.generate(value)
        self.assertEqual(receipt["status"], "compiled", receipt["diagnostics"])
        source = files(receipt)["main.bicep"]
        self.assertNotIn(f"param {bundle._symbol('partner')}_url string", source)
        self.assertIn(f"param {bundle._symbol('partner')}_callerClientId string", source)

    def test_actual_backend_build_root_is_accepted_without_allowing_arbitrary_studio_paths(self):
        root = ROOT / ".intent-to-impact" / "studio" / "runs" / "builds"
        build_id = "unit-path-" + uuid.uuid4().hex
        directory = bundle._build_dir(root, build_id)
        try:
            self.assertEqual(directory, root / build_id)
            with self.assertRaises(bundle.Blocked):
                bundle._build_dir(ROOT / ".intent-to-impact" / "studio" / "runs" / "jobs", uuid.uuid4().hex)
        finally:
            directory.rmdir()

    def test_schema_receipt_and_zip_hashes(self):
        from jsonschema import Draft7Validator
        receipt = self.generate()
        self.assertEqual(receipt["status"], "compiled", receipt["diagnostics"])
        self.assertEqual(receipt["deploymentStatus"], "not-deployed")
        schema = json.loads(bundle.SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft7Validator(dict(schema, **{"$ref": "#/definitions/BuildResult"})).validate(receipt)
        self.assertRegex(receipt["buildId"], r"^[0-9a-f]{32}$")
        self.assertEqual(receipt["downloadUrl"], f"/api/studio/builds/{receipt['buildId']}/download")
        package = self.output_root / receipt["buildId"] / "package.zip"
        with zipfile.ZipFile(package) as archive:
            self.assertEqual(set(archive.namelist()), set(files(receipt)))
            for entry in receipt["files"]:
                self.assertNotIn("..", entry["path"])
                self.assertNotIn("\\", entry["path"])
                self.assertNotIn("/", entry["path"])
                self.assertEqual(hashlib.sha256(archive.read(entry["path"])).hexdigest(), entry["sha256"])
        manifest = json.loads(files(receipt)["manifest.json"])
        self.assertEqual(manifest["inputHash"], fixture()["inputHash"])
        self.assertEqual(manifest["modelReceipts"][0]["sha256"],
                         bundle._hash(bundle._json(fixture()["modelReceipts"][0])))
        self.assertEqual(len(manifest["mapping"]["components"]), 5)
        self.assertEqual(len(manifest["mapping"]["connections"]), 4)
        for path, digest in manifest["fileHashes"].items():
            self.assertEqual(digest, bundle._hash(files(receipt)[path]))

    def test_topologies_are_different_and_every_component_is_mapped(self):
        first, second = self.generate(option="web"), self.generate(option="events")
        self.assertNotEqual(first["buildId"], second["buildId"])
        web, event = files(first)["main.bicep"], files(second)["main.bicep"]
        self.assertNotEqual(web, event)
        self.assertNotIn("Microsoft.ServiceBus/namespaces@", web)
        self.assertIn("Microsoft.ServiceBus/namespaces@", event)
        self.assertIn("functionapp,linux", event)
        self.assertNotIn("functionapp,linux", web)
        manifest = json.loads(files(second)["manifest.json"])
        self.assertEqual({c["componentId"] for c in manifest["mapping"]["components"]},
                         {c["id"] for c in fixture()["analysis"]["options"][1]["components"]})
        symbols = [s for c in manifest["mapping"]["components"] for s in c["symbols"]]
        self.assertEqual(len(symbols), len(set(symbols)))
        self.assertIn("bus-sender", {r["role"] for r in manifest["mapping"]["roleAssignments"]})
        self.assertIn("bus-receiver", {r["role"] for r in manifest["mapping"]["roleAssignments"]})

    def test_malicious_labels_remain_data_not_code_or_paths(self):
        result = fixture()
        payload = "'\n}\nresource owned 'x/y@1' = {}\n// ${loadTextContent('C:\\secret')}"
        result["analysis"]["options"][0]["components"][1]["label"] = payload[:100]
        result["analysis"]["options"][0]["connections"][0]["label"] = payload
        receipt = self.generate(result)
        self.assertEqual(receipt["status"], "compiled", receipt["diagnostics"])
        self.assertNotIn("loadTextContent", files(receipt)["main.bicep"])
        self.assertNotIn("resource owned", files(receipt)["main.bicep"])
        manifest = json.loads(files(receipt)["manifest.json"])
        self.assertEqual(manifest["selectedOption"]["components"][1]["label"], payload[:100])

    def test_unselected_duplicate_pairs_and_self_connections_do_not_block_build(self):
        for topology in ("duplicate", "self"):
            with self.subTest(topology=topology):
                result = fixture()
                other = result["analysis"]["options"][1]
                edge = dict(other["connections"][1], id="unselected-extra")
                if topology == "self":
                    edge["target"] = edge["source"]
                other["connections"].append(edge)
                original = bundle._json(result)
                receipt = self.generate(result, "web")
                self.assertEqual(receipt["status"], "compiled", receipt["diagnostics"])
                self.assertEqual(bundle._json(result), original)
                manifest = json.loads(files(receipt)["manifest.json"])
                self.assertEqual(manifest["selectedOption"], result["analysis"]["options"][0])
                self.assertEqual(manifest["resultSha256"], bundle._hash(original))
                self.assertNotIn(edge["id"], {e["id"] for e in manifest["mapping"]["connections"]})

    def test_selected_duplicate_pairs_and_self_connections_have_actionable_errors(self):
        for topology in ("duplicate", "self"):
            with self.subTest(topology=topology):
                result = fixture()
                option = result["analysis"]["options"][1]
                first = option["connections"][1]
                edge = dict(first, id="selected-extra")
                if topology == "self":
                    edge["target"] = edge["source"]
                option["connections"].append(edge)
                original = bundle._json(result)
                with patch.object(bundle.subprocess, "run") as process:
                    receipt = bundle.build_bundle(result, "events", self.output_root)
                self.assertEqual(receipt["status"], "blocked")
                self.assertIsNone(receipt["downloadUrl"])
                self.assertIn("Selected option events", receipt["diagnostics"])
                self.assertIn(edge["id"], receipt["diagnostics"])
                self.assertIn(f"{edge['source']} -> {edge['target']}", receipt["diagnostics"])
                if topology == "duplicate":
                    self.assertIn(first["id"], receipt["diagnostics"])
                    self.assertIn("Consolidate parallel logical operations", receipt["diagnostics"])
                else:
                    self.assertIn("Remove the edge", receipt["diagnostics"])
                self.assertEqual(bundle._json(result), original)
                self.assertFalse((self.output_root / receipt["buildId"] / "package.zip").exists())
                process.assert_not_called()

    def test_queue_consume_label_does_not_silently_grant_receiver(self):
        result = fixture()
        edge = result["analysis"]["options"][1]["connections"][2]
        edge.update(source="worker", target="jobs", label="Produce work")
        baseline = self.generate(result, "events")
        edge["label"] = "Consume queue messages; abandon/dead-letter on failure"
        original = bundle._json(result)
        receipt = self.generate(result, "events")
        self.assertEqual(receipt["status"], "compiled", receipt["diagnostics"])
        self.assertEqual(files(receipt)["main.bicep"], files(baseline)["main.bicep"])
        self.assertEqual(bundle._json(result), original)
        manifest = json.loads(files(receipt)["manifest.json"])
        worker_roles = {r["role"] for r in manifest["mapping"]["roleAssignments"]
                        if r["applicationComponentId"] == "worker"}
        self.assertIn("bus-sender", worker_roles)
        self.assertNotIn("bus-receiver", worker_roles)
        warning = next(item for item in receipt["limitations"] if item.startswith("WARNING: Queue"))
        for phrase in ("never labels", "Data Sender", "Data Receiver", "opposite directed edges",
                       "does not verify queue handlers"):
            self.assertIn(phrase, warning)
        self.assertIn(warning, manifest["limitations"])
        self.assertIn("**WARNING — queue direction", files(receipt)["README.md"])
        self.assertEqual(next(e for e in manifest["mapping"]["connections"] if e["id"] == edge["id"])["label"],
                         edge["label"])

    def test_opposite_queue_edges_share_settings_but_have_distinct_roles(self):
        result = fixture()
        result["analysis"]["options"][1]["connections"].append(
            {"id": "worker-produces", "source": "worker", "target": "jobs", "label": "Produce follow-up work"})
        receipt = self.generate(result, "events")
        self.assertEqual(receipt["status"], "compiled", receipt["diagnostics"])
        mapping = json.loads(files(receipt)["manifest.json"])["mapping"]
        roles = [(r["scopeSymbol"], r["applicationComponentId"], r["role"]) for r in mapping["roleAssignments"]]
        self.assertEqual(len(roles), len(set(roles)))
        self.assertEqual({role for _, app, role in roles if app == "worker" and role.startswith("bus-")},
                         {"bus-sender", "bus-receiver"})
        for key in next(edge for edge in mapping["connections"] if edge["id"] == "worker-produces")["settings"]:
            # API and worker each get one copy, even though the worker has two directions.
            self.assertEqual(files(receipt)["main.bicep"].count(f"{{ name: '{key}',"), 2)

    def test_regeneration_preserves_previous_package_and_original_result(self):
        result = fixture()
        other = result["analysis"]["options"][1]
        other["connections"].append(dict(other["connections"][1], id="unselected-parallel-operation"))
        original = bundle._json(result)
        first = self.generate(result)
        package = self.output_root / first["buildId"] / "package.zip"
        original_package = package.read_bytes()
        second = self.generate(result)
        self.assertEqual(first["status"], "compiled", first["diagnostics"])
        self.assertEqual(second["status"], "compiled", second["diagnostics"])
        self.assertNotEqual(first["buildId"], second["buildId"])
        self.assertNotEqual(first["downloadUrl"], second["downloadUrl"])
        self.assertEqual(package.read_bytes(), original_package)
        self.assertTrue((self.output_root / second["buildId"] / "package.zip").is_file())
        self.assertEqual(files(first)["main.bicep"], files(second)["main.bicep"])
        self.assertEqual(bundle._json(result), original)

    def test_invalid_inputs_are_blocked_without_compilation(self):
        mutations = [
            lambda r: r["analysis"]["requirements"][0].update(sourceIds=["missing"]),
            lambda r: r["analysis"]["options"][0]["components"][1].update(requirementIds=["missing"]),
            lambda r: r["analysis"]["options"][0]["connections"][0].update(target="missing"),
            lambda r: r["analysis"]["options"][1]["connections"][0].update(target="missing"),
            lambda r: r["analysis"]["options"][1]["connections"][0].pop("label"),
            lambda r: r["analysis"]["options"][1]["connections"][1].update(id="browser-api"),
            lambda r: r["analysis"]["options"][1]["components"][1].update(requirementIds=["missing"]),
            lambda r: r["analysis"]["options"][0]["components"][1].update(id="browser"),
            lambda r: r["analysis"]["options"][0]["components"][1].update(id="../bad"),
            lambda r: r["analysis"]["options"][0]["components"][1].update(kind="sql"),
            lambda r: r["analysis"]["options"][0]["components"][2].update(service="Azure SQL Database"),
            lambda r: r["analysis"]["options"][0]["components"][4].update(service="Azure SQL Database"),
            lambda r: r["analysis"]["options"][0]["components"][1].update(responsibility="Use private endpoints"),
            lambda r: r["analysis"]["options"][0]["connections"][1].update(source="objects", target="web"),
            lambda r: r["analysis"]["options"][0]["connections"].pop(),
            lambda r: r["analysis"]["review"][0].update(dimension="security"),
            lambda r: r["modelReceipts"][0].update(role="assurance"),
            lambda r: r.update(inputHash="missing"),
            lambda r: r.update(code="ignored model shell"),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                result = fixture()
                mutation(result)
                with patch.object(bundle.subprocess, "run") as process:
                    receipt = bundle.build_bundle(result, "web", self.output_root)
                self.assertEqual(receipt["status"], "blocked", receipt["diagnostics"])
                self.assertIsNone(receipt["downloadUrl"])
                self.assertFalse((self.output_root / receipt["buildId"] / "package.zip").exists())
                process.assert_not_called()
        self.assertEqual(self.generate(option="missing")["status"], "blocked")

    def test_functions_identity_hosting_security(self):
        receipt = self.generate(option="events")
        source = files(receipt)["main.bicep"]
        for expected in ["PYTHON|3.12", "FUNCTIONS_EXTENSION_VERSION", "'~4'", "WEBSITE_RUN_FROM_PACKAGE",
                         "AzureWebJobsStorage__accountName", "AzureWebJobsStorage__credential",
                         "AzureWebJobsStorage__clientId", "allowSharedKeyAccess: false",
                         "allowBlobPublicAccess: false", "enablePurgeProtection: true",
                         "enableRbacAuthorization: true", "disableLocalAuth: true",
                         "minimumTlsVersion: 'TLS1_2'", "httpsOnly: true",
                         "requireAuthentication: true", "Return401", "ftpsState: 'Disabled'"]:
            self.assertIn(expected, source)
        for forbidden in ["listKeys(", "listkeys(", "WEBSITE_CONTENTAZUREFILECONNECTIONSTRING",
                          "AccountKey=", "administratorLoginPassword", "privateEndpoints:"]:
            self.assertNotIn(forbidden, source)

    def test_exact_compiler_argv(self):
        with patch.object(bundle.subprocess, "run", side_effect=self.fake_run) as process:
            receipt = bundle.build_bundle(fixture(), "web", self.output_root)
        directory = self.output_root / receipt["buildId"]
        self.assertEqual(process.call_args.args[0], [
            str(bundle.COMPILER_PATHS[0]), "build", str(directory / "main.bicep"),
            "--outfile", str(directory / "main.json"),
        ])
        self.assertFalse(process.call_args.kwargs["shell"])
        self.assertEqual(process.call_args.kwargs["timeout"], bundle.BUILD_TIMEOUT)
        self.assertNotIn("cacheRootDirectory", json.loads(files(receipt)["bicepconfig.json"]))
        self.assertEqual(json.loads(files(receipt)["validation.json"])["compilationConfiguration"]["cacheRootDirectory"],
                         str(directory / ".bicep-cache"))

    def test_missing_failure_and_timeout_never_offer_download(self):
        with patch.object(bundle, "COMPILER_PATHS", (self.output_root / "missing.exe",)):
            missing = bundle.build_bundle(fixture(), "web", self.output_root)
        self.assertEqual(missing["status"], "blocked")
        for mode in ("nonzero", "timeout", "missing-output", "key-output"):
            def run(command, **kwargs):
                if command[-1] == "--version":
                    return self.fake_run(command, **kwargs)
                if mode == "timeout":
                    raise subprocess.TimeoutExpired(command, kwargs["timeout"])
                if mode == "key-output":
                    Path(command[-1]).write_text('{"resources":[{}],"x":"listKeys(x)"}', encoding="utf-8")
                return subprocess.CompletedProcess(command, 7 if mode == "nonzero" else 0, "", "fake compiler failure")
            with self.subTest(mode=mode), patch.object(bundle.subprocess, "run", side_effect=run):
                receipt = bundle.build_bundle(fixture(), "web", self.output_root)
            self.assertIn(receipt["status"], {"failed", "blocked"})
            self.assertIsNone(receipt["downloadUrl"])
            self.assertFalse((self.output_root / receipt["buildId"] / "package.zip").exists())
        self.assertIsNone(missing["compilerVersion"])
        self.assertIsNone(missing["downloadUrl"])

    def test_output_root_is_server_bounded(self):
        receipt = bundle.build_bundle(fixture(), "web", ROOT / "unapproved-build-root")
        self.assertEqual(receipt["status"], "blocked")
        self.assertFalse((ROOT / "unapproved-build-root").exists())

    def test_deterministic_source_and_provenance(self):
        a, b = self.generate(), self.generate()
        self.assertEqual(files(a)["main.bicep"], files(b)["main.bicep"])
        self.assertEqual(files(a)["main.parameters.json"], files(b)["main.parameters.json"])
        manifest = json.loads(files(a)["manifest.json"])
        self.assertEqual(manifest["schemaSha256"], bundle._hash(bundle.SCHEMA_PATH.read_bytes()))
        self.assertEqual(manifest["templateHashes"]["catalog.json"],
                         bundle._hash((bundle.TEMPLATES / "catalog.json").read_bytes()))
        self.assertTrue(all(re.search(r":\d+\.\d+\.\d+$", p) for p in manifest["catalog"]["avm"].values()))

    def test_region_is_target_supplied_not_inferred_or_sandbox_pinned(self):
        result = fixture()
        result["analysis"]["requirements"][0]["text"] = "Keep application data in an approved EU region."
        receipt = self.generate(result)
        self.assertEqual(receipt["status"], "compiled", receipt["diagnostics"])
        source = files(receipt)["main.bicep"]
        self.assertIn("targetScope = 'resourceGroup'", source)
        self.assertIn("param location string = resourceGroup().location", source)
        for region in ("eastus2", "westeurope", "northeurope"):
            self.assertNotIn(region, source.lower())
        self.assertNotIn("location", json.loads(files(receipt)["main.parameters.json"])["parameters"])
        self.assertTrue(any("no validated region field" in item for item in receipt["limitations"]))
        self.assertTrue(receipt["compilerVersion"])
        self.assertEqual(receipt["exitCode"], 0)
        self.assertEqual(receipt["downloadUrl"], f"/api/studio/builds/{receipt['buildId']}/download")

    def test_app_to_app_uses_identity_endpoint_and_rejects_cycles(self):
        result = fixture()
        web = result["analysis"]["options"][0]
        web["components"][4].update(kind="functions", service="Azure Functions")
        receipt = self.generate(result)
        source = files(receipt)["main.bicep"]
        self.assertIn(bundle._symbol("partner") + ".properties.defaultHostName", source)
        self.assertIn(bundle._symbol("web") + "_identity.outputs.clientId", source)
        web["connections"].append({"id": "cycle", "source": "partner", "target": "web", "label": "callback"})
        self.assertEqual(self.generate(result)["status"], "blocked")

    def test_component_ids_cannot_collide_with_supporting_symbols(self):
        result = fixture()
        option = result["analysis"]["options"][0]
        option["components"][2]["id"] = "web-node-plan"
        option["connections"][1]["target"] = "web-node-plan"
        receipt = self.generate(result)
        self.assertEqual(receipt["status"], "compiled", receipt["diagnostics"])
        mapping = json.loads(files(receipt)["manifest.json"])["mapping"]
        symbols = [s for component in mapping["components"] for s in component["symbols"]]
        self.assertEqual(len(symbols), len(set(symbols)))

    def test_disconnected_subgraphs_are_blocked(self):
        result = fixture()
        option = result["analysis"]["options"][0]
        app = dict(option["components"][1], id="other-app")
        storage = dict(option["components"][2], id="other-store")
        option["components"].extend([app, storage])
        option["connections"].append({"id": "other-edge", "source": "other-app",
                                      "target": "other-store", "label": "Stores data"})
        receipt = self.generate(result)
        self.assertEqual(receipt["status"], "blocked")
        self.assertIn("disconnected", receipt["diagnostics"])


class TestRealCompiler(unittest.TestCase):
    """No mocks and no skips: actual installed compiler and official AVM restoration."""

    @classmethod
    def setUpClass(cls):
        cls.output_root = EVIDENCE_ROOT / ("live-local-" + uuid.uuid4().hex)

    def compile_option(self, option, result=None):
        receipt = bundle.build_bundle(result or fixture(), option, self.output_root)
        print(f"LIVE_LOCAL_COMPILER option={option} build={receipt['buildId']} "
              f"status={receipt['status']} exit={receipt['exitCode']} root={self.output_root}", flush=True)
        self.assertEqual(receipt["status"], "compiled", receipt["diagnostics"])
        self.assertEqual(receipt["exitCode"], 0)
        self.assertNotIn("fake", receipt["compilerVersion"].lower())
        content = files(receipt)
        arm = json.loads(content["main.json"])
        self.assertTrue(arm["resources"])
        self.assertNotRegex(content["main.json"].lower(), r"listkeys\s*\(")
        validation = json.loads(content["validation.json"])
        self.assertTrue((self.output_root / receipt["buildId"] / ".bicep-cache").is_dir())
        self.assertTrue(json.loads(content["manifest.json"])["restoredModuleHashes"])
        self.assertEqual(validation["commands"][-1]["exitCode"], 0)
        self.assertEqual(validation["azureOperations"], [])
        self.assertEqual(validation["targetPreflight"], "not-run")
        with zipfile.ZipFile(self.output_root / receipt["buildId"] / "package.zip") as archive:
            self.assertTrue({"main.bicep", "main.parameters.json", "main.json",
                             "manifest.json", "README.md", "validation.json"} <= set(archive.namelist()))
            for entry in receipt["files"]:
                self.assertEqual(hashlib.sha256(archive.read(entry["path"])).hexdigest(), entry["sha256"])
        return content

    def test_real_web_topology(self):
        content = self.compile_option("web")
        self.assertNotIn('"type": "Microsoft.ServiceBus/namespaces"', content["main.json"])
        self.assertIn('"type": "Microsoft.Storage/storageAccounts"', content["main.json"])
        self.assertIn('"type": "Microsoft.KeyVault/vaults"', content["main.json"])

    def test_real_event_topology(self):
        content = self.compile_option("events")
        self.assertIn('"type": "Microsoft.ServiceBus/namespaces"', content["main.json"])
        self.assertIn('"type": "Microsoft.ServiceBus/namespaces/queues"', content["main.json"])
        self.assertIn('"linuxFxVersion": "PYTHON|3.12"', content["main.json"])

    def test_real_queue_topology_with_unselected_duplicates(self):
        result = fixture()
        other = result["analysis"]["options"][0]
        other["connections"].append(dict(other["connections"][1], id="unselected-parallel-operation"))
        result["analysis"]["options"][1]["connections"].append(
            {"id": "worker-produces", "source": "worker", "target": "jobs", "label": "Produce follow-up work"})
        original = bundle._json(result)
        content = self.compile_option("events", result)
        self.assertEqual(bundle._json(result), original)
        self.assertIn("WARNING: Queue", content["manifest.json"])
        self.assertIn(bundle.ROLE_IDS["bus-sender"], content["main.json"])
        self.assertIn(bundle.ROLE_IDS["bus-receiver"], content["main.json"])


if __name__ == "__main__":
    unittest.main()
