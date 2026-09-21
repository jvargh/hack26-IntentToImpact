"""Exercise numbered studio surfaces and real package regeneration; no inference or Azure writes."""

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
    parser.add_argument("--job", required=True)
    parser.add_argument("--option", required=True)
    parser.add_argument("--open-portal", action="store_true", help="Open the real sign-in/custom-deployment page, without uploading or creating.")
    args = parser.parse_args()
    output = ROOT / ".intent-to-impact" / "spikes" / "NUMBERED-GUIDE" / uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    source = ROOT / ".intent-to-impact" / "studio" / "runs" / "jobs" / args.job / "result.json"
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    checks, errors, posts, builds = [], [], [], []
    status = "failed"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1600, "height": 1050}, accept_downloads=True)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: posts.append(urlsplit(request.url).path) if request.method == "POST" else None)
            page.goto(URL)
            page.wait_for_load_state("networkidle")
            expect(page.get_by_text("Ready · configuration only", exact=True)).to_be_visible(timeout=20000)
            page.get_by_role("button", name="Load example inputs", exact=False).click()
            expect(page.get_by_label("Project name", exact=False)).to_have_value("Order fulfilment")
            expect(page.get_by_role("textbox", name="What should this system do?")).not_to_have_value("")
            expect(page.get_by_role("button", name="Preview attached Order fulfilment - business process.md")).to_be_visible()
            page.get_by_role("button", name="Preview attached Order fulfilment - business process.md").click()
            expect(page.get_by_role("dialog").locator("pre")).not_to_have_text("")
            page.get_by_role("button", name="Close source").click()
            assert not posts
            checks.extend(["01-project-name", "02-example-business-prompt-no-inference", "03-exact-local-source-preview"])

            page.get_by_role("button", name="Run history", exact=True).click()
            history = page.get_by_role("dialog", name="Run history", exact=True)
            history.get_by_label("Earlier runs", exact=False).select_option(args.job)
            expect(history.get_by_text(args.job, exact=True)).to_be_visible()
            response = page.request.get(URL + f"api/studio/history/{args.job}", headers={"X-Studio-Client": "1"})
            assert response.status == 200
            saved = response.json()
            result = saved["job"]["result"]
            options = result["analysis"]["options"]
            history.get_by_role("button", name="Open this run", exact=True).click()
            history.get_by_role("button", name="Open saved run", exact=True).click()
            expect(page.get_by_text("SAVED MODEL RESULT", exact=True)).to_be_visible()
            activity = page.get_by_role("region", name="Live activity")
            assert "synthesis" in activity.inner_text() and "assurance" in activity.inner_text() and "complete" in activity.inner_text()
            assert "response characters" not in activity.inner_text()
            checks.extend(["04-07-persisted-synthesis-assurance-completion-events", "08-saved-result-origin"])
            choices = page.get_by_role("group", name="Architecture alternatives", exact=True).get_by_role("button")
            for index, option in enumerate(options):
                choices.nth(index).click()
                assert page.locator(".st-graph-plane .st-node").count() == len(option["components"])
            checks.append("09-10-alternative-selection-changes-real-topology")
            selected_index = next(index for index, option in enumerate(options) if option["id"] == args.option)
            choices.nth(selected_index).click()
            option = options[selected_index]
            page.get_by_role("button", name="Re-layout", exact=True).click()
            page.get_by_role("button", name="Fit", exact=True).click()
            page.locator(".st-graph-plane .st-node").first.click()
            expect(page.get_by_role("tab", name="Inspect", exact=True)).to_have_attribute("aria-selected", "true")
            expect(page.get_by_role("tabpanel", name="Inspect", exact=True)).to_contain_text(option["components"][0]["responsibility"])
            checks.extend(["11-canvas-fit-and-relayout", "12-component-responsibility-inspection"])
            page.get_by_role("tab", name="Sources", exact=True).click()
            sources = page.get_by_role("tabpanel", name="Sources", exact=True)
            sources.get_by_role("button", name="Highlight requirement", exact=False).first.click()
            expect(page.locator(".st-highlight-bar").first).to_contain_text("Linked requirement")
            sources.get_by_role("button", name="Open source", exact=False).first.click()
            expect(page.get_by_role("dialog").locator("pre")).not_to_have_text("")
            page.get_by_role("button", name="Close source").click()
            checks.append("13-requirement-highlight-and-source-snapshot")
            page.get_by_role("tab", name="Assurance", exact=False).click()
            expect(page.get_by_role("group", name="Nine assurance dimensions").get_by_role("button")).to_have_count(9)
            finding = next(row for row in result["analysis"]["review"] if row["dimension"] == "business")
            page.get_by_role("button", name=f"Review Business fit: {finding['severity']}", exact=True).click()
            page.get_by_role("button", name="Request recommended change", exact=True).click()
            dialog = page.get_by_role("dialog")
            expect(dialog.get_by_role("textbox")).to_have_value(finding["recommendation"])
            expect(dialog.get_by_role("button", name="Approve & regenerate")).to_be_disabled()
            dialog.get_by_role("button", name="Cancel", exact=True).click()
            page.get_by_role("button", name="Challenge finding", exact=True).click()
            dialog = page.get_by_role("dialog")
            expect(dialog.get_by_role("textbox")).to_have_value("")
            expect(dialog.get_by_role("button", name="Approve & regenerate")).to_be_disabled()
            dialog.get_by_role("button", name="Cancel", exact=True).click()
            assert not posts, "Inspecting/cancelling findings must not submit work."
            checks.extend(["14-nine-assurance-lenses", "15-recommendation-prefill-consent-cancel", "16-challenge-blank-consent-cancel"])
            page.screenshot(path=str(output / "01-assurance-actions.png"))

            page.get_by_role("tab", name="Build", exact=True).click()
            page.get_by_role("checkbox", name="I confirm package generation only", exact=False).check()
            for attempt in range(2):
                with page.expect_response(lambda response: urlsplit(response.url).path == "/api/studio/builds" and response.request.method == "POST", timeout=150000) as response:
                    page.get_by_role("button", name="deployment package", exact=False).click()
                body = response.value.json()
                assert response.value.status == 200 and body["status"] == "compiled", body.get("diagnostics", body)
                assert body["resultId"] == result["resultId"] and body["optionId"] == args.option
                assert body["exitCode"] == 0 and body["deploymentStatus"] == "not-deployed"
                builds.append(body)
                with page.expect_download() as event:
                    page.get_by_role("button", name="Download compiled ZIP", exact=True).click()
                archive_path = output / f"package-{attempt + 1}.zip"
                event.value.save_as(str(archive_path))
                with zipfile.ZipFile(archive_path) as archive:
                    assert len(archive.namelist()) == 8
                    for file in body["files"]:
                        assert hashlib.sha256(archive.read(file["path"])).hexdigest() == file["sha256"]
                expect(page.get_by_role("button", name="Regenerate deployment package", exact=False)).to_be_enabled()
            assert builds[0]["buildId"] != builds[1]["buildId"]
            assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
            checks.append("17-two-real-compiles-distinct-builds-download-hashes-original-unchanged")
            page.screenshot(path=str(output / "02-regenerated-package.png"))

            page.get_by_role("button", name="Deploy to Azure", exact=True).click()
            deploy = page.get_by_role("dialog", name="Deploy to Azure", exact=True)
            expect(deploy.get_by_text("Compiled template and parameter-file SHA-256 checks passed.", exact=False)).to_be_visible()
            expect(deploy.get_by_role("button", name="Open Azure Portal deployment")).to_be_disabled()
            template_file = next(file for file in builds[-1]["files"] if file["path"] == "main.json")
            with page.expect_download() as event:
                deploy.get_by_role("button", name="Download ARM template").click()
            arm_path = output / "portal-main.json"
            event.value.save_as(str(arm_path))
            assert hashlib.sha256(arm_path.read_bytes()).hexdigest() == template_file["sha256"]
            expect(deploy.get_by_text("entraApplicationClientId", exact=True)).to_be_visible()
            deploy.get_by_role("checkbox", name="I understand this is a manual handoff", exact=False).check()
            link = deploy.get_by_role("link", name="Open Azure Portal deployment", exact=True)
            expect(link).to_have_attribute("href", "https://portal.azure.com/#create/Microsoft.Template")
            page.screenshot(path=str(output / "03-azure-portal-handoff.png"))
            if args.open_portal:
                with page.expect_popup() as event:
                    link.click()
                portal = event.value
                portal.wait_for_load_state("domcontentloaded", timeout=60000)
                assert urlsplit(portal.url).hostname in {"portal.azure.com", "login.microsoftonline.com", "login.live.com"}, portal.url
                checks.append("real-azure-portal-navigation-only-no-upload-or-create")
                portal.close()
            checks.append("azure-handoff-verified-json-required-parameters-acknowledgement")
            deploy.get_by_role("button", name="Close Azure deployment").click()
            page.get_by_role("button", name="Run history", exact=True).click()
            history = page.get_by_role("dialog", name="Run history", exact=True)
            history.get_by_label("Earlier runs", exact=False).select_option(args.job)
            expect(history.get_by_text(args.job, exact=True)).to_be_visible()
            response = page.request.get(URL + f"api/studio/history/{args.job}", headers={"X-Studio-Client": "1"})
            stored = response.json()
            assert {item["buildId"] for item in builds} <= {item["buildId"] for item in stored["builds"]}
            checks.append("history-preserves-both-build-attempts")
            assert posts == ["/api/studio/builds", "/api/studio/builds"], posts
            assert not errors, errors
            status = "passed"
        finally:
            receipt = {"status": status, "at": datetime.now(timezone.utc).isoformat(), "jobId": args.job, "optionId": args.option,
                       "checks": checks, "browserErrors": errors, "posts": posts, "modelCalls": 0,
                       "builds": [{key: build[key] for key in ("buildId", "resultId", "optionId", "status", "compilerVersion", "exitCode")} for build in builds],
                       "azureDeploymentAttempted": False, "azureProvisioningVerified": False}
            (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            print(json.dumps({"output": str(output), **receipt}), flush=True)
            browser.close()


if __name__ == "__main__":
    main()
