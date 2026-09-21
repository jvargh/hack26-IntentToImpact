"""Fixture-only tests: none of these tests contacts a model provider."""

import asyncio
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))

from studio.model_client import FoundryModelClient, StreamProgress, SUBSCRIPTION, TENANT, SYSTEM, verify_identity
from studio.validation import (
    DIMENSIONS, StudioFailure, no_secrets, safe_token, strict_json,
    validate, validate_analysis, validate_request, ground_external_dependencies,
)


def request():
    return {
        "title": "Synthetic order fixture",
        "prompt": "Customers request repairs and staff confirm a collection time.",
        "documents": [{"id": "doc-1", "name": "Synthetic policy", "text": "Keep repair photos private."}],
        "refinement": "", "previousResultId": None, "idempotencyKey": "fixture-key-0001", "consentToModel": True,
    }


def analysis():
    options = []
    for prefix, kind, service in (("web", "appservice", "AppService"), ("event", "functions", "Functions")):
        options.append({
            "id": prefix, "name": prefix + " option", "rationale": "Synthetic fixture rationale.",
            "tradeoffs": ["Synthetic fixture tradeoff."], "costNotes": "Not a measured cost.",
            "components": [
                {"id": prefix + "-client", "kind": "client", "service": "Client", "label": "Customer",
                 "responsibility": "Request repair.", "requirementIds": ["r1"]},
                {"id": prefix + "-api", "kind": kind, "service": service, "label": "Repair service",
                 "responsibility": "Process repair request.", "requirementIds": ["r1", "r2"]},
            ],
            "connections": [{"id": prefix + "-edge", "source": prefix + "-client", "target": prefix + "-api",
                             "label": "Submit request over HTTPS"}],
        })
    return {
        "title": "Synthetic fixture proposal", "summary": "A fixture, never a live fallback.",
        "businessProcess": ["Request repair.", "Confirm collection."],
        "requirements": [
            {"id": "r1", "text": "Customers request repairs.", "sourceIds": ["prompt"]},
            {"id": "r2", "text": "Protect repair photos.", "sourceIds": ["doc-1"]},
        ],
        "assumptions": ["Synthetic assumption."], "questions": [],
        "options": options, "recommendedOptionId": "web",
        "review": [{"dimension": dimension, "severity": "warning", "finding": "Fixture finding.",
                    "recommendation": "Fixture recommendation.", "sourceIds": ["prompt"]}
                   for dimension in sorted(DIMENSIONS)],
        "changeSummary": "Synthetic initial fixture.",
    }


class FakeModel:
    """Only explicitly injected by tests; never selected by production configuration."""

    def __init__(self, failure=None, delay=0):
        self.calls = []
        self.failure, self.delay = failure, delay

    def readiness(self):
        return {"ready": True, "model": "fixture-only", "message": "Injected test fake."}

    async def generate(self, role, input_request, analysis=None, previous=None, progress=None):
        self.calls.append({"role": role, "request": copy.deepcopy(input_request), "previous": copy.deepcopy(previous)})
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.failure:
            raise self.failure
        if progress:
            progress("Fixture-only stream event.")
        value = globals()["analysis"]()
        if role == "assurance":
            value = {"review": [{**item, "finding": "Independent fixture assurance."} for item in value["review"]]}
        return value, {"role": role, "model": "fixture-only", "responseId": f"fixture-{len(self.calls)}",
                       "durationMs": 1}


class ValidationTests(unittest.TestCase):
    def test_queue_examples_use_component_ids_and_kind_endpoints_are_not_repaired(self):
        self.assertIn('"source":"opt-a-queue","target":"opt-a-worker"', SYSTEM)
        self.assertIn("NEVER kind or service names", SYSTEM)
        value = analysis()
        value["options"][0]["connections"][0]["source"] = "servicebus"
        with self.assertRaises(StudioFailure) as caught:
            validate_analysis(value, request())
        self.assertEqual(caught.exception.code, "invalid_references")
        self.assertEqual(value["options"][0]["connections"][0]["source"], "servicebus")

    def test_stream_chunks_do_not_flood_customer_progress(self):
        updates = []
        progress = StreamProgress("synthesis", updates.append)
        progress.receive("")
        for _ in range(512):
            progress.receive("x" * 64)
        self.assertEqual(progress.characters, 32768)
        self.assertEqual(updates, ["Receiving the architecture proposal."])
        progress.complete()
        self.assertEqual(len(updates), 2)
        self.assertFalse(any("characters" in message for message in updates))
        with self.assertRaises(StudioFailure) as caught:
            progress.receive("x" * 400000)
        self.assertEqual(caught.exception.code, "model_output_limit")

    def test_canonical_valid_fixture(self):
        validate_request(request())
        validate_analysis(analysis(), request())

    def test_duplicate_and_nonfinite_json_rejected(self):
        for value in ('{"a":1,"a":2}', '{"a":{"x":1,"x":2}}', '{"x":NaN}', '{"x":Infinity}', b"\xff",
                      '{"x":1}'.encode("utf-16")):
            with self.subTest(value=value), self.assertRaises(StudioFailure):
                strict_json(value)

    def test_unknown_schema_properties(self):
        value = request()
        value["endpoint"] = "https://attacker.invalid"
        with self.assertRaises(StudioFailure):
            validate_request(value)

    def test_request_bounds_and_empty_values(self):
        changes = [
            {"prompt": " " * 12}, {"prompt": "a" * 12001}, {"consentToModel": False},
            {"documents": [{"id": "doc", "name": "doc", "text": " "}]},
            {"documents": [{"id": "prompt", "name": "doc", "text": "content"}]},
            {"documents": [{"id": "refinement", "name": "doc", "text": "content"}]},
            {"documents": [{"id": f"d{i}", "name": "doc", "text": "x"} for i in range(6)]},
            {"documents": [{"id": f"d{i}", "name": "doc", "text": "x" * 80000} for i in range(2)]},
            {"documents": [{"id": "same", "name": "doc", "text": "x"} for _ in range(2)]},
            {"previousResultId": "../../outside", "refinement": "Change queue"},
            {"previousResultId": "result_missing", "refinement": " "},
            {"refinement": "Change without parent"},
        ]
        for change in changes:
            with self.subTest(change=list(change)), self.assertRaises(StudioFailure):
                validate_request({**request(), **change})

    def test_invalid_graph_and_source_references(self):
        mutations = [
            lambda value: value["requirements"][1].update(id="r1"),
            lambda value: value["requirements"][0].update(sourceIds=["foreign-doc"]),
            lambda value: value["options"][1].update(id="web"),
            lambda value: value.update(recommendedOptionId="absent"),
            lambda value: value["options"][0]["components"][0].update(requirementIds=["missing"]),
            lambda value: value["options"][0]["connections"][0].update(target="missing"),
            lambda value: value["options"][1]["components"][0].update(id="web-client"),
            lambda value: value["options"][1]["connections"][0].update(id="web-edge"),
            lambda value: value["review"][0].update(dimension=value["review"][1]["dimension"]),
            lambda value: value["review"][0].update(sourceIds=["foreign"]),
            lambda value: value["options"][0]["components"][1].update(service="SQL"),
        ]
        for mutate in mutations:
            value = analysis()
            mutate(value)
            with self.subTest(mutation=mutate), self.assertRaises(StudioFailure):
                validate_analysis(value, request())

    def test_external_requires_explicit_existing_source(self):
        value = analysis()
        value["options"][0]["components"][1].update(
            kind="external", service="External HTTPS API",
            externalDependency={"name": "RepairERP", "sourceId": "prompt", "quote": "Connect to our existing RepairERP."},
        )
        with self.assertRaises(StudioFailure):
            validate_analysis(value, request())
        source = request()
        source["prompt"] += " Connect to our existing RepairERP."
        validate_analysis(value, source)

    def test_refinement_is_a_source_only_when_nonempty(self):
        value = analysis()
        value["requirements"][0]["sourceIds"] = ["refinement"]
        value["review"][0]["sourceIds"] = ["refinement"]
        for text in ("", "  "):
            with self.subTest(refinement=text), self.assertRaises(StudioFailure):
                validate_analysis(value, {**request(), "refinement": text})
        revised = {**request(), "previousResultId": "result_fixture", "refinement": "Require pickup reminders."}
        validate_request(revised)
        validate_analysis(value, revised)

    def test_refinement_can_identify_an_existing_external_dependency(self):
        value = analysis()
        value["options"][0]["components"][1].update(
            kind="external", service="External HTTPS API",
            externalDependency={"name": "RepairERP", "sourceId": "refinement", "quote": "Connect to our existing RepairERP."},
        )
        revised = {**request(), "previousResultId": "result_fixture",
                   "refinement": "Connect to our existing RepairERP."}
        validate_request(revised)
        validate_analysis(value, revised)

    def test_named_existing_integrations_use_source_binding_not_display_or_service_label(self):
        declaration = "The ERP, payment provider and warehouse are existing integrations that must be retained."
        source = request()
        source["documents"][0]["text"] = declaration
        for name in ("ERP", "payment provider", "warehouse"):
            with self.subTest(name=name):
                value = analysis()
                value["options"][0]["components"][1].update(
                    kind="external", service="External HTTPS API", label=f"Existing {name} integration",
                    externalDependency={"name": name, "sourceId": "doc-1", "quote": declaration},
                )
                validate_analysis(value, source)

    def test_external_quote_is_bound_to_real_source_not_model_paraphrase(self):
        source = request()
        source["documents"][0]["text"] = "The ERP is an existing integration that must be retained."
        value = analysis()
        value["options"][0]["components"][1].update(
            kind="external", service="External HTTPS API",
            externalDependency={"name": "ERP", "sourceId": "doc-1", "quote": "Paraphrased or invented model quotation."},
        )
        original = copy.deepcopy(value)
        grounded = ground_external_dependencies(value, source)
        actual = grounded["options"][0]["components"][1]["externalDependency"]["quote"]
        self.assertEqual(actual, "The ERP is an existing integration that must be retained")
        self.assertIn(actual, source["documents"][0]["text"])
        self.assertEqual(value, original)
        validate_analysis(grounded, source)
        for field, replacement in (("sourceId", "prompt"), ("name", "SQL Database")):
            wrong = copy.deepcopy(value)
            wrong["options"][0]["components"][1]["externalDependency"][field] = replacement
            with self.subTest(field=field), self.assertRaises(StudioFailure):
                ground_external_dependencies(wrong, source)

    def test_existing_dependency_citation_rejects_fabrication_negation_and_proposed_services(self):
        cases = [
            ("Consider a new RepairERP.", "RepairERP"),
            ("We do not have an existing RepairERP.", "RepairERP"),
            ("No existing RepairERP is available.", "RepairERP"),
            ("An existing OtherERP is used.", "ERP"),
            ("Keep our existing ERP; consider a new SQL database.", "SQL database"),
        ]
        for declaration, name in cases:
            source = request()
            source["prompt"] += " " + declaration
            value = analysis()
            value["options"][0]["components"][1].update(
                kind="external", service="External HTTPS API",
                externalDependency={"name": name, "sourceId": "prompt", "quote": declaration},
            )
            with self.subTest(declaration=declaration), self.assertRaises(StudioFailure):
                validate_analysis(value, source)
        value = analysis()
        value["options"][0]["components"][1].update(
            kind="external", service="External HTTPS API",
            externalDependency={"name": "RepairERP", "sourceId": "missing", "quote": "Keep our existing RepairERP."},
        )
        with self.assertRaises(StudioFailure):
            validate_analysis(value, request())

    def test_output_credential_patterns_rejected(self):
        for secret in (
            "-----BEGIN PRIVATE KEY-----", "AccountKey=" + "a" * 40,
            "sk-" + "A" * 40, "ghp_" + "A" * 40,
            "eyJ" + "A" * 20 + "." + "B" * 20 + "." + "C" * 20,
        ):
            with self.subTest(secret=secret[:8]), self.assertRaises(StudioFailure):
                no_secrets({"text": secret})

    def test_token_paths_rejected(self):
        for token in ("../abc", "..\\abc", "C:\\secrets", "/file", "%2e%2e", "", "a" * 81):
            with self.subTest(token=token), self.assertRaises(StudioFailure):
                safe_token(token)


class ModelFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_error_never_falls_back(self):
        model = FoundryModelClient()
        with patch.object(model, "_generate", AsyncMock(side_effect=OSError("secret raw provider payload"))) as call:
            with self.assertRaises(StudioFailure) as raised:
                await model.generate("synthesis", request())
            self.assertEqual(raised.exception.code, "model_unavailable")
            self.assertNotIn("secret raw", raised.exception.message)
            self.assertEqual(call.await_count, 1)

    async def test_provider_timeout_is_bounded_and_not_retried(self):
        model = FoundryModelClient()
        with patch.object(model, "_generate", AsyncMock(side_effect=TimeoutError)) as call:
            with self.assertRaises(StudioFailure) as raised:
                await model.generate("synthesis", request())
            self.assertEqual(raised.exception.code, "model_timeout")
            self.assertEqual(call.await_count, 1)

    async def test_cancellation_propagates(self):
        model = FoundryModelClient()
        with patch.object(model, "_generate", AsyncMock(side_effect=asyncio.CancelledError)):
            with self.assertRaises(asyncio.CancelledError):
                await model.generate("synthesis", request())

    async def test_scope_verified_without_changing_defaults(self):
        completed = type("Completed", (), {"stdout": json.dumps({
            "id": SUBSCRIPTION, "tenantId": TENANT, "state": "Enabled",
        })})()
        with patch("studio.model_client.subprocess.run", return_value=completed) as run:
            verify_identity()
            self.assertEqual(run.call_args.kwargs["timeout"], 20)
            self.assertNotIn("set", run.call_args.args[0])
        completed.stdout = json.dumps({"id": "foreign", "tenantId": TENANT, "state": "Enabled"})
        with patch("studio.model_client.subprocess.run", return_value=completed):
            with self.assertRaises(StudioFailure) as raised:
                verify_identity()
            self.assertEqual(raised.exception.code, "credential_scope")


if __name__ == "__main__":
    unittest.main()
