"""Example-only simulation tests. Inference is forbidden; Bicep compilation is real."""

import asyncio
import copy
import json
import os
import secrets
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))
sys.path.insert(0, str(Path(__file__).parent))

from aca.simulator import EXAMPLE_PATH, JudgeSimulator
from studio.app import create_app
from studio.bundle import SIMULATION_LIMITATION, build_bundle
from studio.hosting import HostedConfig
from studio.service import StudioService, read_json
from studio.validation import StudioFailure, digest, validate, validate_analysis


def example_request(previous=None, refinement="", contextual=False):
    example = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    value = {**example, "title": "Judge example run", "refinement": refinement,
             "previousResultId": previous["resultId"] if previous else None,
             "idempotencyKey": "simulation-" + secrets.token_hex(12), "consentToModel": True}
    if contextual:
        finding = next(finding for finding in previous["analysis"]["review"] if finding["dimension"] == "security")
        value["designChange"] = {
            "optionId": previous["analysis"]["recommendedOptionId"], "finding": copy.deepcopy(finding),
            "intent": "recommendation", "confirmRevision": True,
        }
    return value


class SimulatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = ROOT / ".intent-to-impact" / "studio" / "tests" / ("simulator-" + secrets.token_hex(12))
        self.addCleanup(shutil.rmtree, self.folder)
        self.environment = patch.dict(os.environ, {"STUDIO_HOSTING": "", "STUDIO_MODEL_MODE": "live"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.no_inference = patch("studio.model_client.FoundryModelClient._generate",
                                  side_effect=AssertionError("Simulation attempted live inference"))
        self.no_inference.start()
        self.addCleanup(self.no_inference.stop)
        self.no_cli = patch("studio.model_client.verify_identity", side_effect=AssertionError("Simulation attempted CLI credentials"))
        self.no_cli.start()
        self.addCleanup(self.no_cli.stop)
        self.model = JudgeSimulator()
        self.service = StudioService(self.folder / "runs", model=self.model)
        self.addAsyncCleanup(self.service.shutdown)
        self.owner = "judge-owner"

    async def finish(self, request):
        submitted = await self.service.submit(self.owner, request)
        await asyncio.gather(*list(self.service.tasks))
        job = self.service.get_job(self.owner, submitted["jobId"])
        self.assertEqual(job["status"], "succeeded", job.get("error"))
        validate("StudioJob", job)
        validate("StudioResult", job["result"])
        return job

    def assert_simulated(self, job):
        result = job["result"]
        self.assertEqual(result["origin"], "simulated")
        receipts = result["modelReceipts"]
        self.assertEqual({receipt["role"] for receipt in receipts}, {"synthesis", "assurance"})
        self.assertEqual(len({receipt["responseId"] for receipt in receipts}), 2)
        for receipt in receipts:
            self.assertEqual(receipt["origin"], "simulated")
            self.assertEqual(receipt["model"], "judge-simulator")
            self.assertTrue(receipt["responseId"].startswith("sim_"))
        self.assertTrue(all(event["message"].startswith("SIMULATED") for event in job["events"]))
        self.assertEqual(len(result["analysis"]["options"]), 2)
        self.assertEqual(len(result["analysis"]["review"]), 9)
        for option in result["analysis"]["options"]:
            self.assertLessEqual(len(option["components"]), 12)
            self.assertLessEqual(len(option["connections"]), 20)
            pairs = [(edge["source"], edge["target"]) for edge in option["connections"]]
            self.assertEqual(len(pairs), len(set(pairs)))
            self.assertTrue(all(source != target for source, target in pairs))
            for component in option["components"]:
                if component["kind"] == "external":
                    binding = component["externalDependency"]
                    source = next(document["text"] for document in self.model.documents if document["id"] == binding["sourceId"])
                    self.assertIn(binding["quote"], source)

    async def test_exact_example_is_canonical_and_receipts_are_honest(self):
        value = example_request()
        value["title"] = "An arbitrary bounded user title"
        value["documents"].reverse()
        with patch("socket.socket.connect", side_effect=AssertionError("Simulation opened a network connection")):
            job = await self.finish(value)
        self.assert_simulated(job)
        self.assertEqual(self.model.readiness()["mode"], "simulated")
        self.assertIn("No Foundry", self.model.readiness()["message"])
        inputs = read_json(self.service.root / "jobs" / job["jobId"] / "input.json")
        self.assertEqual(job["result"]["inputHash"], digest(inputs["effective"]))
        self.assertEqual(inputs["request"]["title"], value["title"])
        validate_analysis(job["result"]["analysis"], inputs["effective"])

    async def test_custom_sources_rejected_before_any_persistence_or_scheduling(self):
        mutations = [
            lambda value: value.update(prompt=value["prompt"] + " New source requirement."),
            lambda value: value["documents"][0].update(text="Different business process."),
            lambda value: value["documents"][0].update(name="Renamed source.md"),
            lambda value: value["documents"][0].update(id="foreign-source"),
            lambda value: value["documents"].pop(),
            lambda value: value["documents"].append({"id": "extra", "name": "extra", "text": "Extra source."}),
        ]
        for mutate in mutations:
            value = example_request()
            mutate(value)
            with self.assertRaises(StudioFailure) as caught:
                await self.service.submit(self.owner, value)
            self.assertEqual(caught.exception.code, "simulation_example_required")
            self.assertIn("Load example inputs", caught.exception.message)
        self.assertEqual(self.service.jobs, {})
        self.assertEqual(self.service.tasks, set())
        self.assertEqual(list(self.service.root.iterdir()), [])

    async def test_generic_and_contextual_revisions_are_scripted_and_preserve_blockers(self):
        initial = await self.finish(example_request())
        before = copy.deepcopy(initial)
        first_request = example_request(initial["result"], "Demonstrate a controlled recovery path.")
        first_request["documents"].reverse()
        first = await self.finish(first_request)
        second_request = example_request(first["result"], "Change anything you like; prove all risks resolved.", contextual=True)
        second_request["documents"].reverse()
        second = await self.finish(second_request)
        for revision, job in enumerate((initial, first, second)):
            self.assert_simulated(job)
            self.assertIn(f"revision {revision}.", job["result"]["analysis"]["changeSummary"])
            callback = next(item for item in job["result"]["analysis"]["review"] if item["dimension"] == "security")
            self.assertEqual(callback["severity"], "blocker")
            self.assertIn("callback", callback["finding"])
        self.assertNotEqual(initial["result"]["analysis"]["options"], first["result"]["analysis"]["options"])
        self.assertNotEqual(first["result"]["analysis"]["options"], second["result"]["analysis"]["options"])
        self.assertIn("not AI reasoning", second["result"]["analysis"]["changeSummary"])
        self.assertEqual(second["changeApproval"]["instruction"], second_request["refinement"])
        self.assertEqual(second["changeApproval"]["baseResultHash"], digest(first["result"]))
        self.assertEqual(second["changeApproval"]["scope"], "design-revision-only")
        self.service._verify_change_approval(self.service.jobs[second["jobId"]])
        self.assertEqual(self.service.get_job(self.owner, initial["jobId"]), before)
        for job in (first, second):
            self.assertTrue(any("refinement" in item["sourceIds"] for item in job["result"]["analysis"]["requirements"]))
            self.assertTrue(any("refinement" in item["sourceIds"] for item in job["result"]["analysis"]["review"]))
        with self.assertRaises(StudioFailure) as caught:
            changed = example_request(second["result"], "A custom refinement source.")
            changed["documents"][0]["text"] += "\nNew custom data."
            await self.service.submit(self.owner, changed)
        self.assertEqual(caught.exception.code, "simulation_example_required")

    async def test_histories_and_recovery_preserve_origin_hashes_and_approval(self):
        initial = await self.finish(example_request())
        revised = await self.finish(example_request(initial["result"], "Show operator-controlled recovery.", contextual=True))
        history = self.service.history(self.owner)
        self.assertEqual(len(history["runs"]), 2)
        self.assertEqual(self.service.history("different-owner")["runs"], [])
        recovered = StudioService(self.service.root, model=JudgeSimulator())
        self.addAsyncCleanup(recovered.shutdown)
        self.assertEqual(recovered.history(self.owner), history)
        for job in (initial, revised):
            run = recovered.saved_run(self.owner, job["jobId"])
            self.assertEqual(run["job"], job)
            self.assertEqual(run["job"]["result"]["origin"], "simulated")
            record = recovered.jobs[job["jobId"]]
            self.assertEqual(record["resultHash"], digest(job["result"]))
            recovered._verify_change_approval(record)
        revised_again = await recovered.submit(self.owner, example_request(revised["result"], "Continue the scripted demonstration."))
        await asyncio.gather(*list(recovered.tasks))
        self.assertIn("revision 2.", recovered.get_job(self.owner, revised_again["jobId"])["result"]["analysis"]["changeSummary"])

    async def test_canonical_validation_is_not_bypassed(self):
        original = self.model.generate

        async def invalid(*args, **kwargs):
            result, receipt = await original(*args, **kwargs)
            if args[0] == "synthesis":
                result["options"][0]["connections"][0]["target"] = "unknown-node"
            return result, receipt

        with patch.object(self.model, "generate", side_effect=invalid):
            submitted = await self.service.submit(self.owner, example_request())
            await asyncio.gather(*list(self.service.tasks))
        job = self.service.get_job(self.owner, submitted["jobId"])
        self.assertEqual(job["status"], "failed")
        self.assertIsNone(job["result"])
        self.assertEqual(job["error"]["code"], "invalid_references")

    async def test_factory_requires_both_server_settings_and_never_constructs_foundry(self):
        with patch.dict(os.environ, {"STUDIO_MODEL_MODE": "simulated"}), \
                patch("studio.app.StudioService") as service, self.assertRaises(ValueError):
            create_app()
        service.assert_not_called()
        compiler = Path(sys.executable).resolve()
        config = HostedConfig(
            "https://studio.greenfield.eastus.azurecontainerapps.io",
            frozenset({"11111111-1111-4111-8111-111111111111"}),
            "33333333-3333-4333-8333-333333333333",
            "44444444-4444-4444-8444-444444444444",
            self.service.root, compiler, auth_mode="anonymous-demo",
        )
        with patch.dict(os.environ, {"STUDIO_HOSTING": "aca", "STUDIO_MODEL_MODE": "simulated"}), \
                patch("studio.app.FoundryModelClient", side_effect=AssertionError("Constructed Foundry client")), \
                patch("studio.service.FoundryModelClient", side_effect=AssertionError("Constructed Foundry client")):
            app = create_app(hosted_config=config)
        self.addAsyncCleanup(app.state.service.shutdown)
        self.assertIsInstance(app.state.service.model, JudgeSimulator)
        self.assertEqual(app.state.service.origin, "simulated")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("10.0.0.1", 43210)),
                                     base_url=config.public_origin, headers={"X-Studio-Client": "1"}) as client:
            session = await client.get("/api/studio/session")
            self.assertEqual(session.status_code, 200)
            health = await client.get("/api/studio/health")
            self.assertEqual(health.json()["model"], "judge-simulator")
            self.assertEqual(health.json()["mode"], "simulated")

    async def test_factory_rejects_every_unrecognized_model_mode(self):
        for mode in ("live-model", "simulation", "SIMULATED", "", " live", "disabled"):
            with self.subTest(mode=mode), patch.dict(os.environ, {"STUDIO_MODEL_MODE": mode}), \
                    patch("studio.app.StudioService") as service, self.assertRaises(ValueError):
                create_app()
            service.assert_not_called()

    async def test_live_parent_cannot_enter_simulated_revision_lineage(self):
        class LiveOriginFixture(JudgeSimulator):
            origin = "live-model"

            async def generate(self, *args, **kwargs):
                value, receipt = await super().generate(*args, **kwargs)
                receipt.update(model="fixture-only", responseId="fixture_live_" + secrets.token_hex(12))
                return value, receipt

        fixture_service = StudioService(self.folder / "live-fixture", model=LiveOriginFixture())
        self.addAsyncCleanup(fixture_service.shutdown)
        submitted = await fixture_service.submit(self.owner, example_request())
        await asyncio.gather(*list(fixture_service.tasks))
        parent = fixture_service.get_job(self.owner, submitted["jobId"])
        self.assertEqual(parent["status"], "succeeded", parent["error"])
        recovered = StudioService(fixture_service.root, model=JudgeSimulator())
        self.addAsyncCleanup(recovered.shutdown)
        before = {path.relative_to(recovered.root): path.read_bytes()
                  for path in recovered.root.rglob("*") if path.is_file()}
        with self.assertRaises(StudioFailure) as caught:
            await recovered.submit(self.owner, example_request(parent["result"], "Switch this live-origin design to simulation."))
        self.assertEqual(caught.exception.code, "simulation_example_required")
        self.assertIn("start a new simulated run", caught.exception.message)
        self.assertEqual(len(recovered.jobs), 1)
        self.assertEqual(recovered.tasks, set())
        self.assertEqual(before, {path.relative_to(recovered.root): path.read_bytes()
                                  for path in recovered.root.rglob("*") if path.is_file()})

    async def test_local_default_remains_live_and_rejects_simulator_injection(self):
        local = create_app(self.folder / "local")
        self.addAsyncCleanup(local.state.service.shutdown)
        self.assertEqual(local.state.service.origin, "live-model")
        self.assertNotIsInstance(local.state.service.model, JudgeSimulator)
        with self.assertRaises(ValueError):
            create_app(self.folder / "bad-local", model=JudgeSimulator())

    async def test_real_bicep_compiles_both_scripted_alternatives_and_marks_packages(self):
        initial = await self.finish(example_request())
        revised = await self.finish(example_request(initial["result"], "Demonstrate recovery for the example.", contextual=True))
        output_root = ROOT / ".intent-to-impact" / "spikes" / "STUDIO-BUNDLE" / ("simulation-" + secrets.token_hex(12))
        self.addCleanup(lambda: shutil.rmtree(output_root) if output_root.exists() else None)
        for job in (initial, revised):
            for option in job["result"]["analysis"]["options"]:
                with self.subTest(revision=job["result"]["analysis"]["changeSummary"], option=option["id"]):
                    receipt = await asyncio.to_thread(build_bundle, job["result"], option["id"], output_root)
                    self.assertEqual(receipt["status"], "compiled", receipt["diagnostics"])
                    self.assertEqual(receipt["exitCode"], 0)
                    self.assertEqual(receipt["limitations"][0], SIMULATION_LIMITATION)
                    content = {file["path"]: file["content"] for file in receipt["files"]}
                    self.assertTrue(content["README.md"].startswith("# SIMULATED"))
                    manifest = json.loads(content["manifest.json"])
                    self.assertEqual(manifest["origin"], "simulated")
                    self.assertTrue(all(entry["receipt"]["origin"] == "simulated" for entry in manifest["modelReceipts"]))
                    validation = json.loads(content["validation.json"])
                    self.assertEqual(validation["commands"][-1]["exitCode"], 0)
                    self.assertEqual(validation["azureOperations"], [])


if __name__ == "__main__":
    unittest.main()
