"""Source-constrained generation schema tests; no model calls."""

import copy
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))
sys.path.insert(0, str(Path(__file__).parent))

from studio.generation_schema import response_format, responses_text_format
from studio.validation import SCHEMA, StudioFailure
from test_model import analysis, request


class GenerationSchemaTests(unittest.TestCase):
    def test_initial_calls_cannot_emit_a_nonexistent_refinement_source(self):
        for name in ("ArchitectureAnalysis", "AssuranceReview"):
            generated = response_format(name, request())
            schema = generated["json_schema"]["schema"]
            self.assertTrue(generated["json_schema"]["strict"])
            allowed = schema["$defs"]["ReviewFinding"]["properties"]["sourceIds"]["items"]["enum"]
            self.assertEqual(allowed, ["doc-1", "prompt"])
            self.assertNotIn("refinement", allowed)
        review = {"review": analysis()["review"]}
        schema = response_format("AssuranceReview", request())["json_schema"]["schema"]
        Draft202012Validator(schema).validate(review)
        review["review"][0]["sourceIds"] = ["doc-1", "refinement", "prompt"]
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(review)

    def test_real_refinement_is_an_allowed_source_only_for_that_request(self):
        original = request()
        revised = {**original, "previousResultId": "result_fixture", "refinement": "Change resilience targets"}
        generated = response_format("ArchitectureAnalysis", revised)["json_schema"]["schema"]
        for definition in ("Requirement", "ReviewFinding"):
            self.assertEqual(generated["$defs"][definition]["properties"]["sourceIds"]["items"]["enum"],
                             ["doc-1", "prompt", "refinement"])
        self.assertEqual(generated["$defs"]["ExternalDependency"]["properties"]["sourceId"]["enum"],
                         ["doc-1", "prompt", "refinement"])
        self.assertNotIn("refinement", response_format("AssuranceReview", original)["json_schema"]["schema"]
                         ["$defs"]["ReviewFinding"]["properties"]["sourceIds"]["items"]["enum"])

    def test_strict_generation_derives_only_reachable_types_without_mutating_runtime_contract(self):
        before = copy.deepcopy(SCHEMA)
        generated = response_format("ArchitectureAnalysis", request())["json_schema"]["schema"]
        self.assertEqual(SCHEMA, before)
        self.assertNotIn("RunHistory", generated["$defs"])
        self.assertNotIn("AnalysisRequest", generated["$defs"])

        def check(value):
            if isinstance(value, dict):
                if value.get("type") == "object":
                    self.assertEqual(set(value["required"]), set(value["properties"]))
                    self.assertFalse(value["additionalProperties"])
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)

        check(generated)
        self.assertIn("externalDependency", generated["$defs"]["Component"]["required"])
        self.assertIn({"type": "null"}, generated["$defs"]["Component"]["properties"]["externalDependency"]["anyOf"])
        self.assertEqual(SCHEMA["definitions"]["ArchitectureAnalysis"]["properties"]["review"]["minItems"], 9)
        with self.assertRaises(StudioFailure):
            response_format("StudioJob", request())

    def test_installed_sdk_maps_strict_schema_to_the_expected_responses_wire_format(self):
        from agent_framework_openai import OpenAIChatClient
        client = object.__new__(OpenAIChatClient)
        format_value = response_format("AssuranceReview", request())
        parse_target, text = client._prepare_response_and_text_format(response_format=format_value, text_config=None)
        self.assertIsNone(parse_target)
        self.assertEqual(text["format"], responses_text_format(format_value))
        self.assertEqual(text["format"]["type"], "json_schema")
        self.assertTrue(text["format"]["strict"])


if __name__ == "__main__":
    unittest.main()
