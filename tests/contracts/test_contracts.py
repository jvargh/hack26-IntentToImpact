"""FND-01-01 contract tests. All payloads here are fixture tests, not provider proof."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "contracts" / "examples" / "1.0.0"
GENERATED = ROOT / "contracts" / "generated" / "1.0.0"
WORK = ROOT / ".intent-to-impact" / "spikes" / "FND-01-01"
EXAMPLE_FILES = {
    "D01": "case.json",
    "D22": "run-manifest.json",
    "E01": "evidence-reference.json",
    "E02": "command-execution-receipt.json",
    "E03": "work-envelope.json",
    "E04": "domain-event.json",
    "E07": "error-envelope.json",
    "E08": "authorization-context.json",
}
EXTRA_EXAMPLE_FILES = {
    "automatic-domain-event.json": "E04",
    "agent-authorization-context.json": "E08",
    "pre-context-error.json": "E07",
}


def load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / "contracts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validation = load_tool("validate")
generation = load_tool("generate")


def example(contract_id: str) -> dict:
    return json.loads((EXAMPLES / EXAMPLE_FILES[contract_id]).read_text(encoding="utf-8"))


def extra_example(filename: str) -> dict:
    return json.loads((EXAMPLES / filename).read_text(encoding="utf-8"))


def error_keywords(errors):
    for error in errors:
        yield error.validator
        yield from error_keywords(error.context)


def command(arguments: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        arguments, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"},
    )


class SchemaTests(unittest.TestCase):
    def test_positive_examples_cover_exactly_the_base_contracts(self):
        self.assertEqual(set(EXAMPLE_FILES), set(validation.CONTRACT_NAMES))
        for contract_id in EXAMPLE_FILES:
            with self.subTest(contract=contract_id):
                value = example(contract_id)
                validation.validate_contract(value, contract_id)
                validation.validate_contract(value)
        for filename, contract_id in EXTRA_EXAMPLE_FILES.items():
            with self.subTest(extra=filename):
                value = extra_example(filename)
                validation.validate_contract(value, contract_id)
                validation.validate_contract(value)

    def test_negative_examples_fail_at_the_declared_schema_keyword(self):
        cases = json.loads((EXAMPLES / "negative-cases.json").read_text(encoding="utf-8"))
        self.assertEqual(cases["origin"], "fixture")
        contracts = {filename: contract_id for contract_id, filename in EXAMPLE_FILES.items()}
        contracts.update(EXTRA_EXAMPLE_FILES)
        for case in cases["cases"]:
            with self.subTest(case=case["name"]):
                contract_id = contracts[case["base"]]
                value = extra_example(case["base"])
                target = value
                for segment in case["path"][:-1]:
                    target = target[segment]
                key = case["path"][-1]
                if case.get("delete"):
                    del target[key]
                else:
                    target[key] = case["value"]
                errors = list(validation.validator(contract_id).iter_errors(value))
                self.assertIn(case["keyword"], list(error_keywords(errors)))
                with self.assertRaises(ValidationError):
                    validation.validate_contract(value)

    def test_every_required_root_field_is_enforced(self):
        common = validation.SCHEMA["definitions"]["CommonEnvelope"]["required"]
        for contract_id, name in validation.CONTRACT_NAMES.items():
            definition = validation.SCHEMA["definitions"][name]
            required = definition["required"]
            if {"$ref": "#/definitions/CommonEnvelope"} in definition.get("allOf", []):
                required = required + common
            for field in required:
                with self.subTest(contract=contract_id, missing=field):
                    value = example(contract_id)
                    del value[field]
                    with self.assertRaises(ValidationError):
                        validation.validate_contract(value, contract_id)

    def test_common_metadata_and_closed_shapes_for_every_contract(self):
        invalid = {
            "schemaVersion": "2.0.0",
            "runId": "CASE-NOT-A-RUN",
            "caseId": "RUN-NOT-A-CASE",
            "artifactId": "unsafe/path",
            "caseRevisionAtWrite": True,
            "createdAt": "yesterday",
            "updatedAt": "2026-13-01T00:00:00Z",
            "stateChecksum": "sha256:bad",
            "derivedFrom": {"input": "bad"},
            "unknownField": "not permitted",
        }
        for contract_id in EXAMPLE_FILES:
            for field, bad_value in invalid.items():
                with self.subTest(contract=contract_id, field=field):
                    value = example(contract_id)
                    value[field] = bad_value
                    with self.assertRaises(ValidationError):
                        validation.validate_contract(value, contract_id)
            if contract_id != "D01":
                value = example(contract_id)
                value["logicalRevision"] = 0
                with self.assertRaises(ValidationError):
                    validation.validate_contract(value, contract_id)

    def test_scope_and_nested_ids_are_validated(self):
        for field, value in (
            ("scopeId", "../escape"),
            ("subscriptionId", "not-a-uuid"),
            ("resourceGroup", ""),
            ("resourceIds", [""]),
        ):
            with self.subTest(field=field):
                context = example("D22")
                context["scope"][field] = value
                with self.assertRaises(ValidationError):
                    validation.validate_contract(context, "D22")

    def test_origin_and_evidence_state_are_independent(self):
        for origin in ["live-external", "live-local", "fixture", "replayed", "ux-mock"]:
            for state in ["fresh", "stale", "missing", "partial", "failed"]:
                with self.subTest(origin=origin, state=state):
                    value = example("E01")
                    value.update(origin=origin, evidenceState=state)
                    validation.validate_contract(value, "E01")

    def test_three_modes_and_five_purposes_with_replay_source_and_mock_constraint(self):
        for mode in ["live", "fixture", "replay"]:
            for purpose in ["magic-moment-proof", "hero", "ux-mock", "test", "rehearsal"]:
                with self.subTest(mode=mode, purpose=purpose):
                    value = example("D22")
                    value.update(runMode=mode, purpose=purpose)
                    if mode == "replay":
                        value["sourceRunId"] = "RUN-SOURCE"
                    if purpose == "ux-mock" and mode != "fixture":
                        with self.assertRaises(ValidationError):
                            validation.validate_contract(value, "D22")
                    else:
                        validation.validate_contract(value, "D22")

    def test_demo_identity_is_fixed_in_all_actor_envelopes(self):
        for contract_id in ("E02", "E04", "E08"):
            for field, invalid in (
                ("actorId", "agent"),
                ("identityAssurance", "entra-verified"),
                ("principalId", "client-supplied-principal"),
            ):
                with self.subTest(contract=contract_id, field=field):
                    value = example(contract_id)
                    human = {
                        "kind": "human", "actorId": "demo-human",
                        "identityAssurance": "local-demo",
                    }
                    if contract_id == "E08":
                        value["caller"]["actor"] = human
                    else:
                        value["actor"] = human
                    validation.validate_contract(value, contract_id)
                    human[field] = invalid
                    with self.assertRaises(ValidationError):
                        validation.validate_contract(value, contract_id)

    def test_nested_work_events_checkpoints_and_references(self):
        value = example("D01")
        work = example("E03")
        event = example("E04")
        reference = {"artifactId": "ART-EXAMPLE", "checksum": value["stateChecksum"]}
        work["checkpoints"] = [{
            "checkpointId": "CHECKPOINT-EXAMPLE",
            "createdAt": value["createdAt"],
            "artifacts": [reference],
        }]
        event["payloadRefs"] = [reference]
        value["sections"] = {"requirements": reference}
        value["work"] = [work]
        value["events"] = [event]
        value["idempotencyRecords"] = [{
            "idempotencyKey": "test-creation",
            "commandId": "create-case",
            "inputChecksum": value["stateChecksum"],
            "result": reference,
        }]
        validation.validate_contract(value, "D01")
        broken = deepcopy(value)
        broken["events"][0]["actor"]["actorId"] = "another-human"
        with self.assertRaises(ValidationError):
            validation.validate_contract(broken, "D01")
        broken = deepcopy(value)
        broken["work"][0]["checkpoints"][0]["artifacts"][0]["checksum"] = "bad"
        with self.assertRaises(ValidationError):
            validation.validate_contract(broken, "D01")


class ExecutionAttributionTests(unittest.TestCase):
    def test_automatic_events_and_commands_preserve_executor_and_optional_initiator(self):
        for contract_id in ("E02", "E04"):
            for kind, actor_id in (("system", "SYSTEM-OBSERVER"), ("agent", "AGENT-EXAMPLE")):
                for initiated_by_human in (False, True):
                    with self.subTest(contract=contract_id, kind=kind, human=initiated_by_human):
                        value = example(contract_id)
                        value["actor"] = {"kind": kind, "actorId": actor_id}
                        value.pop("humanInitiator", None)
                        if initiated_by_human:
                            value["humanInitiator"] = {
                                "actorId": "demo-human", "identityAssurance": "local-demo",
                            }
                        validation.validate_contract(value, contract_id)
                        validation.validate_contract(value)
                        self.assertNotEqual(value["actor"]["kind"], "human")
                        self.assertNotEqual(value["actor"]["actorId"], "demo-human")
        automatic = extra_example("automatic-domain-event.json")
        validation.validate_contract(automatic, "E04")
        self.assertNotIn("humanInitiator", automatic)

    def test_human_initiator_never_changes_model_caller_class(self):
        value = extra_example("agent-authorization-context.json")
        for include_initiator in (True, False):
            with self.subTest(humanInitiator=include_initiator):
                candidate = deepcopy(value)
                if not include_initiator:
                    del candidate["humanInitiator"]
                validation.validate_contract(candidate, "E08")
                self.assertEqual(candidate["caller"]["callerClass"], "agent")
                self.assertEqual(candidate["caller"]["channel"], "model")
        for field, invalid in (("actorId", "another-human"), ("identityAssurance", "entra-verified")):
            candidate = deepcopy(value)
            candidate["humanInitiator"][field] = invalid
            with self.assertRaises(ValidationError):
                validation.validate_contract(candidate, "E08")

    def test_caller_class_channel_and_executor_must_agree(self):
        actors = {
            "human": {"kind": "human", "actorId": "demo-human", "identityAssurance": "local-demo"},
            "agent": {"kind": "agent", "actorId": "AGENT-EXAMPLE"},
            "system": {"kind": "system", "actorId": "SYSTEM-WORKER"},
        }
        channels = {
            "human": {"browser", "cli", "harness"},
            "agent": {"model"},
            "system": {"worker", "harness"},
        }
        for caller_class, actor in actors.items():
            for channel in ("browser", "cli", "harness", "worker", "model"):
                for executor_class, executor in actors.items():
                    with self.subTest(caller=caller_class, channel=channel, executor=executor_class):
                        value = example("E08")
                        value["caller"] = {
                            "callerClass": caller_class, "channel": channel, "actor": executor,
                        }
                        if channel in channels[caller_class] and executor == actor:
                            validation.validate_contract(value, "E08")
                        else:
                            with self.assertRaises(ValidationError):
                                validation.validate_contract(value, "E08")

    def test_automated_actor_cannot_claim_human_identity_or_assurance(self):
        for contract_id in ("E02", "E04", "E08"):
            for kind, actor_id in (("system", "SYSTEM-WORKER"), ("agent", "AGENT-EXAMPLE")):
                for field, invalid in (
                    ("actorId", "demo-human"),
                    ("kind", "human"),
                    ("identityAssurance", "local-demo"),
                    ("identityAssurance", "entra-verified"),
                ):
                    with self.subTest(contract=contract_id, kind=kind, field=field, value=invalid):
                        value = example(contract_id)
                        actor = {"kind": kind, "actorId": actor_id}
                        if contract_id == "E08":
                            value["caller"] = {
                                "callerClass": kind,
                                "channel": "worker" if kind == "system" else "model",
                                "actor": actor,
                            }
                        else:
                            value["actor"] = actor
                        validation.validate_contract(value, contract_id)
                        actor[field] = invalid
                        with self.assertRaises(ValidationError):
                            validation.validate_contract(value, contract_id)


class PreContextErrorTests(unittest.TestCase):
    def test_error_without_existing_run_or_case_has_no_fabricated_metadata(self):
        value = extra_example("pre-context-error.json")
        validation.validate_contract(value, "E07")
        validation.validate_contract(value)
        for field in (
            "artifactId", "runId", "caseId", "scope", "caseRevisionAtWrite",
            "stateChecksum", "derivedFrom", "diagnosticReference",
        ):
            self.assertNotIn(field, value)

    def test_unknown_context_may_be_explicitly_null(self):
        value = extra_example("pre-context-error.json")
        for field in (
            "artifactId", "runId", "caseId", "scope", "caseRevisionAtWrite",
            "stateChecksum", "derivedFrom", "updatedAt", "workId",
            "expectedRevision", "actualRevision", "diagnosticReference",
        ):
            value[field] = None
        validation.validate_contract(value, "E07")

    def test_known_context_and_persisted_diagnostic_reference_are_preserved(self):
        value = example("E07")
        value["diagnosticReference"] = {
            "artifactId": "DIAGNOSTIC-EXAMPLE", "checksum": value["stateChecksum"],
        }
        validation.validate_contract(value, "E07")
        value["diagnosticReference"]["checksum"] = "bad"
        with self.assertRaises(ValidationError):
            validation.validate_contract(value, "E07")
        partial = extra_example("pre-context-error.json")
        partial.update(runId="RUN-KNOWN", caseId=None)
        validation.validate_contract(partial, "E07")

    def test_pre_context_reason_correlation_diagnostic_and_recovery_are_required(self):
        for field in ("code", "correlationId", "diagnosticId", "message", "allowedRecoveryActions"):
            for invalid in ("missing", None, ""):
                with self.subTest(field=field, invalid=invalid):
                    value = extra_example("pre-context-error.json")
                    if invalid == "missing":
                        del value[field]
                    else:
                        value[field] = invalid
                    with self.assertRaises(ValidationError):
                        validation.validate_contract(value, "E07")


class ImmutableContextTests(unittest.TestCase):
    def test_identical_and_nonidentity_metadata_comparisons_pass(self):
        old = example("D22")
        validation.assert_run_context_unchanged(old, deepcopy(old))
        new = deepcopy(old)
        new["updatedAt"] = "2026-09-12T18:00:00Z"
        new["stateChecksum"] = "sha256:" + "1" * 64
        validation.assert_run_context_unchanged(old, new)
        self.assertNotEqual(old, new)

    def test_each_immutable_field_mutation_is_rejected_after_both_shapes_validate(self):
        mutations = {
            "runId": "RUN-DIFFERENT",
            "caseId": "CASE-DIFFERENT",
            "runMode": "live",
            "purpose": "hero",
            "scenarioId": "SCENARIO-DIFFERENT",
            "scenarioVersion": "2.0.0",
            "scenarioHash": "sha256:" + "1" * 64,
            "rootId": "ROOT-DIFFERENT",
            "configId": "CONFIG-DIFFERENT",
            "scope": {
                "scopeId": "SCOPE-DIFFERENT",
                "subscriptionId": None, "resourceGroup": None, "resourceIds": [],
            },
            "sourceRunId": "RUN-DIFFERENT-SOURCE",
        }
        fields = {
            field
            for name in ("CommonEnvelope", "LocalRunManifest")
            for field, definition in validation.SCHEMA["definitions"][name]["properties"].items()
            if definition.get("x-immutable")
        }
        self.assertEqual(set(mutations), fields)
        for field, replacement in mutations.items():
            with self.subTest(field=field):
                old = example("D22")
                if field == "sourceRunId":
                    old.update(runMode="replay", sourceRunId="RUN-ORIGINAL-SOURCE")
                new = deepcopy(old)
                new[field] = replacement
                validation.validate_contract(old, "D22")
                validation.validate_contract(new, "D22")
                with self.assertRaisesRegex(ValueError, field):
                    validation.assert_run_context_unchanged(old, new)

    def test_every_mode_transition_requires_a_new_context(self):
        for before in ("live", "fixture", "replay"):
            for after in ("live", "fixture", "replay"):
                if before == after:
                    continue
                with self.subTest(before=before, after=after):
                    old = example("D22")
                    old["runMode"] = before
                    if before == "replay":
                        old["sourceRunId"] = "RUN-SOURCE"
                    new = example("D22")
                    new["runMode"] = after
                    if after == "replay":
                        new["sourceRunId"] = "RUN-SOURCE"
                    with self.assertRaisesRegex(ValueError, "runMode"):
                        validation.assert_run_context_unchanged(old, new)

    def test_invalid_old_or_new_shape_is_not_accepted_by_comparison(self):
        valid = example("D22")
        invalid = deepcopy(valid)
        invalid["runMode"] = "demo"
        for old, new in ((invalid, valid), (valid, invalid), (invalid, invalid)):
            with self.assertRaises(ValidationError):
                validation.assert_run_context_unchanged(old, new)


class GeneratedTypesTests(unittest.TestCase):
    def test_generated_python_import_and_annotations_need_only_standard_library(self):
        script = (
            "import json, runpy, sys, typing; "
            "ns = runpy.run_path(sys.argv[1]); "
            "names = json.loads(sys.argv[2]); "
            "assert all(typing.is_typeddict(ns[n]) for n in names); "
            "assert all(typing.get_type_hints(ns[n], globalns=ns) for n in names); "
            "print('Eight generated TypedDict roots import and resolve without site packages.')"
        )
        result = command([
            sys.executable, "-I", "-S", "-c", script,
            str(GENERATED / "python" / "core.py"),
            json.dumps(list(validation.CONTRACT_NAMES.values())),
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generated_typescript_and_consumer_type_assertions_compile(self):
        result = command([
            "node", str(ROOT / "contracts" / "node_modules" / "typescript" / "bin" / "tsc"),
            "--project", str(ROOT / "contracts" / "tsconfig.json"),
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_toolchain_version_mismatch_is_rejected(self):
        with patch.object(generation.importlib.metadata, "version", return_value="0.0.0"):
            with self.assertRaisesRegex(RuntimeError, "locked"):
                generation.verify_toolchain()


class RegenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = WORK / f"test-generation-{uuid.uuid4().hex}"
        cls.output = cls.workspace / "generated"
        cls.workspace.mkdir(parents=True)
        result = cls.generate()
        if result.returncode:
            shutil.rmtree(cls.workspace)
            raise AssertionError(result.stdout + result.stderr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.workspace)

    @classmethod
    def generate(cls, *extra: str):
        return command([
            sys.executable, str(ROOT / "tools" / "contracts" / "generate.py"),
            "--output-dir", str(cls.output), *extra,
        ])

    def test_regeneration_is_byte_stable_and_matches_checked_in_outputs(self):
        result = self.generate("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in generation.ARTIFACTS:
            with self.subTest(artifact=name):
                self.assertEqual((self.output / name).read_bytes(), (GENERATED / name).read_bytes())

    def test_check_rejects_intentionally_different_bytes_without_modifying_them(self):
        for name in generation.ARTIFACTS:
            with self.subTest(artifact=name):
                target = self.output / name
                original = target.read_bytes()
                altered = original + b"\n"
                try:
                    target.write_bytes(altered)
                    result = self.generate("--check")
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn("Generated type drift", result.stderr)
                    self.assertIn(name, result.stderr)
                    self.assertEqual(target.read_bytes(), altered)
                finally:
                    target.write_bytes(original)

    def test_check_rejects_missing_and_unexpected_generated_files(self):
        target = self.output / generation.ARTIFACTS[0]
        original = target.read_bytes()
        try:
            target.unlink()
            result = self.generate("--check")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        finally:
            target.write_bytes(original)
        extra = self.output / "unexpected.d.ts"
        try:
            extra.write_text("// Unexpected generated artifact\n", encoding="utf-8")
            result = self.generate("--check")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("unexpected.d.ts", result.stderr)
        finally:
            extra.unlink()


if __name__ == "__main__":
    unittest.main()
