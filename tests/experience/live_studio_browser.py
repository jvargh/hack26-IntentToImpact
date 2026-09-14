"""Opt-in real browser -> local API -> Foundry proof; optional package download."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from urllib.parse import urlsplit
from uuid import uuid4
import zipfile

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
URL = "http://127.0.0.1:5173/"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--refine", action="store_true")
    parser.add_argument("--example", action="store_true", help="Click the product's built-in Load example inputs button; do not replace its inputs.")
    parser.add_argument("--title", help="Optional project title for reproducing a reported run.")
    args = parser.parse_args()
    if not args.execute_live:
        parser.error("Explicit --execute-live is required for chargeable synthetic model calls.")
    output = ROOT / ".intent-to-impact" / "spikes" / "STUDIO-BROWSER" / uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    errors, requests, results, builds, checks, failed_jobs = [], [], [], [], [], []
    status = "failed"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1600, "height": 1000}, accept_downloads=True)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.on("request", lambda request: requests.append(request.url))

            def response_seen(response):
                path = urlsplit(response.url).path
                if response.status == 200 and path.startswith("/api/studio/jobs/"):
                    job = response.json()
                    if job["status"] == "succeeded" and all(item["resultId"] != job["result"]["resultId"] for item in results):
                        results.append(job["result"])
                    if job["status"] == "failed":
                        failed_jobs.append(job)
                if response.status == 200 and path == "/api/studio/builds":
                    builds.append(response.json())
            page.on("response", response_seen)
            response = page.goto(URL)
            assert response.status == 200
            assert "'unsafe-eval'" not in response.headers.get("content-security-policy", "")
            page.wait_for_load_state("networkidle")
            expect(page.get_by_text("Ready · configuration only", exact=True)).to_be_visible(timeout=20_000)
            page.screenshot(path=str(output / "empty-studio.png"))
            if args.example:
                page.get_by_role("button", name="Load example inputs", exact=False).click()
                assert "Help us redesign" in page.get_by_role("textbox", name="What should this system do?").input_value()
                expect(page.get_by_role("button", name="Preview attached Order fulfilment - business process.md")).to_be_visible()
                expect(page.get_by_role("button", name="Preview attached Operating requirements.md")).to_be_visible()
                expect(page.get_by_role("button", name="Preview attached Example clarification workshop.md")).to_be_visible()
                checks.append("exact-built-in-example-inputs")
            else:
                prompt = "Design a small repair-booking system for customers and workshop operators. Use managed Azure services supported by this studio. Customers submit repair requests, operators schedule a slot and customers get status updates. Keep the initial application simple, store status durably, and handle background notification work reliably. We do not have an existing ERP."
                page.get_by_label("Project name", exact=False).fill("Live repair-booking design")
                page.get_by_role("textbox", name="What should this system do?").fill(prompt)
                page.get_by_label("Attach source documents").set_input_files({
                    "name": "repair-process.md", "mimeType": "text/markdown",
                    "buffer": b"A customer requests a repair. An operator schedules a slot. The customer receives confirmation and completion updates. Store repair status and audit events. Do not store card details. Peak load and recovery targets are not confirmed."
                })
                expect(page.get_by_role("button", name="Preview attached repair-process.md")).to_be_visible()
            if args.title:
                page.get_by_label("Project name", exact=False).fill(args.title)
            expect(page.get_by_role("checkbox", name="I consent to send", exact=False)).not_to_be_checked()
            page.get_by_role("checkbox", name="I consent to send", exact=False).check()
            print("Starting actual browser-driven synthesis and assurance.", flush=True)
            page.get_by_role("button", name="Generate architecture", exact=False).click()
            page.get_by_text("LIVE MODEL RESULT", exact=True).or_(page.get_by_role("alert")).first.wait_for(timeout=330_000)
            if failed_jobs:
                (output / "failed-job.json").write_text(json.dumps(failed_jobs[-1], indent=2), encoding="utf-8")
                raise RuntimeError(f"Actual analysis failed: {failed_jobs[-1]['error']}")
            page.get_by_text("LIVE MODEL RESULT", exact=True).wait_for(timeout=330_000)
            assert len(results) == 1, "Browser result was not captured from real job transport"
            result = results[-1]
            assert result["origin"] == "live-model"
            assert {receipt["role"] for receipt in result["modelReceipts"]} == {"synthesis", "assurance"}
            assert len(result["analysis"]["review"]) == 9
            if args.example:
                external = [node for alternative in result["analysis"]["options"] for node in alternative["components"] if node["kind"] == "external"]
                assert external and all(node["service"] == "External HTTPS API" and node.get("externalDependency") for node in external)
                checks.append("named-existing-integrations-carry-explicit-source-citations")
            activity = page.get_by_role("region", name="Live activity")
            assert "response characters" not in activity.inner_text()
            checks.append("concise-stage-progress-without-character-counter-spam")
            checks.append("actual-browser-synthesis-and-assurance")
            (output / "initial-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            option = next(item for item in result["analysis"]["options"] if item["id"] == result["analysis"]["recommendedOptionId"])
            node = option["components"][0]
            page.get_by_role("button", name=f"Inspect {node['label']}", exact=True).click()
            expect(page.get_by_text(node["responsibility"], exact=True)).to_be_visible()
            page.screenshot(path=str(output / "generated-canvas.png"))
            checks.append("generated-component-inspection")
            for width in (1440, 768, 390, 320):
                page.set_viewport_size({"width": width, "height": 1000})
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), width
                page.screenshot(path=str(output / f"studio-{width}.png"))
            checks.append("responsive-reflow-1440-768-390-320")
            page.set_viewport_size({"width": 1600, "height": 1000})
            if args.refine:
                old = result["resultId"]
                page.get_by_role("textbox", name="Refine this architecture").fill("Ensure background notification work is durably queued and can recover after a temporary worker outage. Explain retry and duplicate-processing behavior.")
                page.get_by_role("button", name="Refine architecture", exact=False).click()
                page.get_by_text("LIVE MODEL RESULT", exact=True).wait_for(timeout=330_000)
                assert len(results) == 2 and results[-1]["resultId"] != old
                result = results[-1]
                assert result["analysis"]["changeSummary"]
                (output / "refined-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
                checks.append("actual-refinement-new-model-result")
                page.screenshot(path=str(output / "refined-canvas.png"))
            if args.build:
                page.get_by_role("tab", name="Build", exact=True).click()
                page.get_by_role("checkbox", name="I confirm package generation only", exact=False).check()
                page.get_by_role("button", name="Generate deployment package", exact=False).click()
                download_button = page.get_by_role("button", name="Download compiled ZIP", exact=False)
                download_button.or_(page.get_by_role("alert")).first.wait_for(timeout=150_000)
                if builds and builds[-1]["status"] != "compiled":
                    raise RuntimeError(f"Actual package generation {builds[-1]['status']}: {builds[-1]['diagnostics']}")
                expect(download_button).to_be_visible()
                assert builds and builds[-1]["status"] == "compiled" and builds[-1]["exitCode"] == 0
                page.screenshot(path=str(output / "compiler-and-package.png"))
                with page.expect_download() as downloaded:
                    download_button.click()
                path = output / "deployment-package.zip"
                downloaded.value.save_as(path)
                with zipfile.ZipFile(path) as package:
                    assert "main.bicep" in package.namelist() and "main.parameters.json" in package.namelist()
                checks.append("actual-compiler-and-browser-zip-download")
                (output / "build.json").write_text(json.dumps(builds[-1], indent=2), encoding="utf-8")
            assert not errors, errors
            assert all(urlsplit(url).netloc == urlsplit(URL).netloc for url in requests), "External browser request"
            checks.append("csp-no-eval-no-browser-errors-no-external-browser-requests")
            status = "passed"
        finally:
            failure = repr(sys.exception()) if sys.exception() else None
            browser.close()
            receipt = {
                "status": status, "checks": checks, "error": failure, "browserErrors": errors,
                "evidenceOrigin": "live-browser+live-model", "syntheticInput": True,
                "modelReceipts": [entry["modelReceipts"] for entry in results], "completedAt": datetime.now(timezone.utc).isoformat(),
                "buildTested": args.build, "refinementTested": args.refine, "azureDeploymentAttempted": False,
                "builtInExampleTested": args.example,
                "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "buildResults": builds,
            }
            (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": status, "checks": checks, "evidence": str(output.relative_to(ROOT))}), flush=True)
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
