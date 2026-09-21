"""Opt-in real saved blocker -> approve design revision -> Foundry assurance -> package."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
import zipfile

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
URL = "http://127.0.0.1:5173/"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-live", action="store_true", help="Authorize chargeable synthetic model calls.")
    parser.add_argument("--parent-job", required=True, help="A saved built-in example result to revise.")
    parser.add_argument("--resume-job", help="Verify an already completed revision and its package without another model call.")
    parser.add_argument("--dimension", default="security", choices=["business", "security", "reliability", "performance", "cost", "integration", "compliance", "operations", "delivery"])
    parser.add_argument("--intent", default="recommendation", choices=["recommendation", "challenge"])
    parser.add_argument("--instruction", help="Explicit challenge/correction instruction; required for challenge.")
    parser.add_argument("--build", action="store_true", help="Compile and download the revised infrastructure; no deployment.")
    args = parser.parse_args()
    if not args.execute_live and not args.resume_job:
        parser.error("Explicit --execute-live is required for two chargeable model calls.")
    if args.intent == "challenge" and not args.instruction and not args.resume_job:
        parser.error("--instruction is required for a challenge; the test must not invent human intent.")
    output = ROOT / ".intent-to-impact" / "spikes" / "DESIGN-CHANGE" / uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    checks, errors, submitted, completed, saved, builds = [], [], [], [], [], []
    status = "failed"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1600, "height": 1050}, accept_downloads=True)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)

            def response_seen(response):
                path = urlsplit(response.url).path
                if response.status not in (200, 202):
                    return
                if path == f"/api/studio/history/{args.parent_job}":
                    saved.append(response.json())
                if path == "/api/studio/analyses":
                    submitted.append({"request": response.request.post_data_json, "job": response.json()})
                if path.startswith("/api/studio/jobs/"):
                    job = response.json()
                    if job["status"] in ("failed", "succeeded"):
                        completed.append(job)
                if path == "/api/studio/builds":
                    builds.append(response.json())

            page.on("response", response_seen)
            response = page.goto(URL)
            assert response.status == 200
            assert "'unsafe-eval'" not in response.headers.get("content-security-policy", "")
            page.wait_for_load_state("networkidle")
            expect(page.get_by_text("Ready · configuration only", exact=True)).to_be_visible(timeout=20_000)
            page.get_by_role("button", name="Run history", exact=True).click()
            select = page.get_by_label("Earlier runs", exact=False)
            expect(select).to_be_visible()
            select.select_option(args.parent_job)
            expect(page.get_by_role("button", name="Open this run", exact=True)).to_be_enabled(timeout=20_000)
            assert saved, "The selected real history record was not captured."
            parent = saved[-1]
            assert parent["job"]["jobId"] == args.parent_job
            assert parent["job"]["status"] == "succeeded"
            assert parent["inputs"]["previousResultId"] is None, "Use an original synthetic example, not a custom refinement."
            assert {doc["id"] for doc in parent["inputs"]["documents"]} == {
                "example-process", "example-requirements", "example-clarifications"
            }, "Live test only accepts the built-in example document set."
            original = parent["job"]["result"]
            finding = next(row for row in original["analysis"]["review"] if row["dimension"] == args.dimension)
            dimension_name = "Business fit" if args.dimension == "business" else args.dimension.capitalize()
            page.get_by_role("button", name="Open this run", exact=True).click()
            expect(page.get_by_text("SAVED MODEL RESULT", exact=True)).to_be_visible(timeout=20_000)
            page.get_by_role("tab", name="Assurance", exact=False).click()
            page.get_by_role("button", name=f"Review {dimension_name}: {finding['severity']}", exact=True).click()
            page.screenshot(path=str(output / "01-original-blocker.png"))

            if args.resume_job:
                page.get_by_role("button", name="Run history", exact=True).click()
                page.get_by_label("Earlier runs", exact=False).select_option(args.resume_job)
                history = page.get_by_role("dialog", name="Run history", exact=True)
                expect(history.get_by_text(args.resume_job, exact=True)).to_be_visible()
                history.get_by_role("button", name="Open this run", exact=True).click()
                history.get_by_role("button", name="Open saved run", exact=True).click()
                expect(page.get_by_text("SAVED MODEL RESULT", exact=True)).to_be_visible()
                response = page.request.get(URL + f"api/studio/jobs/{args.resume_job}", headers={"X-Studio-Client": "1"})
                assert response.status == 200
                job = response.json()
                assert not submitted, "Resuming verification must not submit another model request."
                checks.append("resuming-existing-real-revision-without-additional-inference")
            else:
                page.get_by_role("button", name="Challenge finding", exact=True).click()
                challenge = page.get_by_role("dialog", name="Challenge this finding", exact=True)
                expect(challenge.get_by_role("textbox")).to_have_value("")
                expect(challenge.get_by_role("button", name="Approve & regenerate", exact=True)).to_be_disabled()
                challenge.get_by_role("button", name="Cancel", exact=True).click()
                assert not submitted, "Drafting or cancelling must not call the model."
                checks.append("challenge-cancel-makes-no-model-call")

                action = "Request recommended change" if args.intent == "recommendation" else "Challenge finding"
                page.get_by_role("button", name=action, exact=True).click()
                dialog = page.get_by_role("dialog", name="Approve a design change" if args.intent == "recommendation" else "Challenge this finding", exact=True)
                instruction = dialog.get_by_role("textbox")
                expect(instruction).to_have_value(finding["recommendation"] if args.intent == "recommendation" else "")
                if args.instruction:
                    instruction.fill(args.instruction)
                approve = dialog.get_by_role("button", name="Approve & regenerate", exact=True)
                expect(approve).to_be_disabled()
                dialog.get_by_role("button", name="Close design change", exact=True).focus()
                page.keyboard.press("Shift+Tab")
                expect(dialog.get_by_role("button", name="Cancel", exact=True)).to_be_focused()
                checks.append("native-keyboard-dialog-focus-trap")
                dialog.get_by_role("checkbox", name="I approve this revision request", exact=False).check()
                expect(approve).to_be_enabled()
                page.screenshot(path=str(output / "02-review-before-approval.png"))
                print(f"Approving {args.intent} for the exact saved {dimension_name} finding; starting real synthesis and assurance.", flush=True)
                approve.click()
                page.get_by_text("Revised proposal and independent assurance are ready.", exact=False).or_(
                    dialog.get_by_role("alert")
                ).first.wait_for(timeout=330_000)
                assert submitted and len(submitted) == 1, f"Expected one accepted request. Visible error: {dialog.get_by_role('alert').all_text_contents()}"
                job = completed[-1] if completed else submitted[-1]["job"]
                assert submitted[0]["request"]["designChange"]["confirmRevision"] is True
            (output / "revision-job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
            assert job["status"] == "succeeded", job.get("error")
            approval = job["changeApproval"]
            revised = job["result"]
            assert revised["resultId"] != original["resultId"]
            assert approval["baseResultId"] == original["resultId"]
            assert approval["optionId"] == original["analysis"]["recommendedOptionId"]
            assert approval["finding"] == finding
            assert approval["instruction"] == (args.instruction or finding["recommendation"])
            assert approval["intent"] == args.intent
            assert approval["scope"] == "design-revision-only" and approval["actor"] == "demo-human"
            assert len(revised["modelReceipts"]) == 2
            assert {receipt["role"] for receipt in revised["modelReceipts"]} == {"synthesis", "assurance"}
            assert not {receipt["responseId"] for receipt in revised["modelReceipts"]}.intersection(
                receipt["responseId"] for receipt in original["modelReceipts"]
            ), "The revision needs new real model receipts."
            expect(page.get_by_role("tab", name="Assurance", exact=False)).to_have_attribute("aria-selected", "true")
            current = next(row for row in revised["analysis"]["review"] if row["dimension"] == args.dimension)
            expect(page.get_by_role("button", name=f"Review {dimension_name}: {current['severity']}", exact=True)).to_be_visible()
            checks.extend(["exact-parent-option-finding-approval", "two-new-real-model-receipts", "fresh-independent-nine-lens-review"])
            page.get_by_text("View change & decision record", exact=True).click()
            page.screenshot(path=str(output / "03-revised-design-and-decision.png"))
            assert "not verified resolution" in page.locator(".st-change-outcome").inner_text()
            assert not builds, "Approving a design change must not automatically build or deploy."
            page.get_by_text("View change & decision record", exact=True).click()

            if args.build:
                page.get_by_role("tab", name="Build", exact=True).click()
                page.get_by_role("checkbox", name="I confirm package generation only", exact=False).check()
                page.get_by_role("button", name="Generate deployment package", exact=True).click()
                page.get_by_role("button", name="Download compiled ZIP", exact=True).or_(
                    page.get_by_role("alert")
                ).first.wait_for(timeout=150_000)
                assert builds and builds[-1]["status"] == "compiled", builds
                bundle = builds[-1]
                assert bundle["resultId"] == revised["resultId"] and bundle["exitCode"] == 0
                assert bundle["deploymentStatus"] == "not-deployed"
                with page.expect_download() as download:
                    page.get_by_role("button", name="Download compiled ZIP", exact=True).click()
                package = output / "revised-package.zip"
                download.value.save_as(str(package))
                with zipfile.ZipFile(package) as archive:
                    assert len(archive.namelist()) == 8
                    for file in bundle["files"]:
                        assert hashlib.sha256(archive.read(file["path"])).hexdigest() == file["sha256"]
                page.screenshot(path=str(output / "04-revised-package-compiled.png"))
                checks.append("new-result-real-bicep-compile-and-eight-file-download")

            page.get_by_role("button", name="Run history", exact=True).click()
            page.get_by_label("Earlier runs", exact=False).select_option(job["jobId"])
            history = page.get_by_role("dialog", name="Run history", exact=True)
            expect(history.get_by_text("View change & decision record", exact=True)).to_be_visible()
            with page.expect_download() as download:
                history.get_by_role("button", name="Download run record ZIP", exact=True).click()
            record = output / "revision-record.zip"
            download.value.save_as(str(record))
            with zipfile.ZipFile(record) as archive:
                stored = json.loads(archive.read("run.json"))
                assert stored["job"]["changeApproval"] == approval
                assert stored["job"]["result"]["resultId"] == revised["resultId"]
                stored_inputs = json.loads(archive.read("inputs.json"))
                assert stored_inputs["refinement"] == approval["refinement"]
            checks.append("history-export-preserves-approval-and-exact-refinement-source")
            assert not errors, errors
            status = "passed"
        finally:
            receipt = {
                "status": status, "at": datetime.now(timezone.utc).isoformat(), "parentJobId": args.parent_job,
                "checks": checks, "browserErrors": errors, "modelRequests": len(submitted),
                "builds": len(builds), "deployment": "none", "evidenceMode": "real-model-and-service",
                "resumedRevisionJobId": args.resume_job,
                "intent": args.intent, "dimension": args.dimension,
            }
            (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            print(json.dumps({"output": str(output), **receipt}), flush=True)
            browser.close()


if __name__ == "__main__":
    main()
