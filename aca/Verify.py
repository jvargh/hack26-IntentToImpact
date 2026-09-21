"""Opt-in real browser -> hosted ACA -> managed-identity Foundry -> Linux Bicep."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit
from uuid import uuid4
import zipfile

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--saved-job", help="Verify persisted history without another model call.")
    args = parser.parse_args()
    if not args.execute_live and not args.saved_job:
        parser.error("Use --execute-live for chargeable synthetic inference, or --saved-job for read-only recovery.")
    folder = Path(__file__).resolve().parent
    state = json.loads((folder / ".local" / "deployment-state.json").read_text(encoding="utf-8"))
    if state.get("modelMode") == "simulated":
        raise ValueError("This deployment uses the no-model judge simulator. Run Judge-Check.py instead of the live-model test.")
    url = state["url"]
    if urlsplit(url).hostname is None or not url.endswith(".azurecontainerapps.io"):
        raise ValueError("Expected the deployed ACA origin from the local deployment record.")
    public_demo = state.get("publicDemo", False)
    access_token = None
    if not public_demo:
        token_command = subprocess.run(
            [shutil.which("az") or "az", "account", "get-access-token",
             "--scope", f"api://{state['entraApplicationId']}/access_as_user", "-o", "json"],
            capture_output=True, text=True, check=True, timeout=40,
        )
        access_token = json.loads(token_command.stdout)["accessToken"]
    output = folder / ".local" / ("verification-" + uuid4().hex)
    output.mkdir()
    checks, errors, results, builds = [], [], [], []
    receipt = {"status": "failed", "url": url, "modelMode": "real" if args.execute_live else "saved",
               "checks": checks, "errors": errors, "azureWorkloadDeployment": False}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            recovery = output.parent / "verification-browser-state.json"
            context = browser.new_context(viewport={"width": 1600, "height": 1050}, accept_downloads=True,
                                          storage_state=str(recovery) if args.saved_job and public_demo else None)
            page = context.new_page()
            def authorize(route):
                if urlsplit(route.request.url).hostname != urlsplit(url).hostname:
                    route.abort()
                    return
                route.continue_(headers={**route.request.headers, **({"Authorization": f"Bearer {access_token}"} if access_token else {})})
            page.route("**/*", authorize)
            page.on("pageerror", lambda error: errors.append(str(error)))
            def received(response):
                path = urlsplit(response.url).path
                if response.status == 200 and path.startswith("/api/studio/jobs/"):
                    value = response.json()
                    if value["status"] in ("succeeded", "failed"):
                        results.append(value)
                if response.status == 200 and path == "/api/studio/builds":
                    builds.append(response.json())
            page.on("response", received)
            page.goto(url)
            page.wait_for_load_state("networkidle")
            expect(page.get_by_text("Ready · configuration only", exact=True)).to_be_visible(timeout=30000)
            checks.append("public-demo-no-sign-in-and-secure-browser-session" if public_demo else "real-Entra-operator-token-and-hosted-session")
            if args.saved_job:
                page.get_by_role("button", name="Run history", exact=True).click()
                history = page.get_by_role("dialog", name="Run history", exact=True)
                history.get_by_label("Earlier runs", exact=False).select_option(args.saved_job)
                expect(history.get_by_text(args.saved_job, exact=True)).to_be_visible()
                history.get_by_role("button", name="Open this run", exact=True).click()
                expect(page.get_by_text("SAVED MODEL RESULT", exact=True)).to_be_visible()
                checks.append("Azure-Files-history-recovered-after-restart")
                page.get_by_role("tab", name="Build", exact=True).click()
                expect(page.get_by_role("button", name="Download compiled ZIP", exact=True)).to_be_visible(timeout=20000)
                with page.expect_download() as downloaded:
                    page.get_by_role("button", name="Download compiled ZIP", exact=True).click()
                downloaded.value.save_as(str(output / "recovered-package.zip"))
                checks.append("persisted-compiled-package-download")
                receipt["jobId"] = args.saved_job
            else:
                page.get_by_label("Project name", exact=False).fill("ACA verification - repair status")
                page.get_by_role("textbox", name="What should this system do?").fill(
                    "Design a small repair request and status system using this studio's supported Azure services. "
                    "A customer submits a repair request; staff update its status and the customer can check progress. "
                    "Use authenticated access, durable Blob status storage, and Service Bus for background work where useful. "
                    "We have no existing external systems. Queue consumers must have edges from the declared queue node ID "
                    "to the declared worker node ID. Keep uncertainties explicit and do not claim application code is generated."
                )
                page.get_by_role("checkbox", name="I consent to send", exact=False).check()
                page.get_by_role("button", name="Generate architecture", exact=True).click()
                page.get_by_text("LIVE MODEL RESULT", exact=True).or_(page.get_by_role("alert")).first.wait_for(timeout=330000)
                if not results or results[-1]["status"] != "succeeded":
                    raise AssertionError(results[-1]["error"] if results else page.get_by_role("alert").all_text_contents())
                job = results[-1]
                result = job["result"]
                assert len(result["modelReceipts"]) == 2
                assert {row["role"] for row in result["modelReceipts"]} == {"synthesis", "assurance"}
                assert len(result["analysis"]["review"]) == 9
                checks.append("managed-identity-real-synthesis-and-independent-assurance")
                receipt.update(jobId=job["jobId"], resultId=result["resultId"], modelReceipts=result["modelReceipts"])
                context.storage_state(path=str(recovery))
                page.get_by_role("button", name="Expand", exact=True).click()
                page.get_by_role("button", name="Re-layout", exact=True).click()
                page.screenshot(path=str(output / "hosted-architecture.png"))
                page.get_by_role("button", name="Restore panels", exact=True).click()
                page.get_by_role("tab", name="Build", exact=True).click()
                page.get_by_role("checkbox", name="I confirm package generation only", exact=False).check()
                page.get_by_role("button", name="Generate deployment package", exact=True).click()
                page.get_by_role("button", name="Download compiled ZIP", exact=True).or_(page.get_by_role("alert")).first.wait_for(timeout=150000)
                if not builds or builds[-1]["status"] != "compiled":
                    raise AssertionError(builds[-1]["diagnostics"] if builds else page.get_by_role("alert").all_text_contents())
                build = builds[-1]
                with page.expect_download() as downloaded:
                    page.get_by_role("button", name="Download compiled ZIP", exact=True).click()
                archive_path = output / "compiled-package.zip"
                downloaded.value.save_as(str(archive_path))
                with zipfile.ZipFile(archive_path) as archive:
                    assert len(archive.namelist()) == 8
                    for file in build["files"]:
                        assert hashlib.sha256(archive.read(file["path"])).hexdigest() == file["sha256"]
                checks.append("cloud-Linux-Bicep-exit0-and-eight-file-ZIP-hashes")
                receipt.update(buildId=build["buildId"], compilerVersion=build["compilerVersion"], exitCode=build["exitCode"])
                page.screenshot(path=str(output / "hosted-compiled-package.png"))
            assert not errors, errors
            receipt["status"] = "passed"
        finally:
            (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            print(json.dumps({"evidence": str(output), **receipt}), flush=True)
            browser.close()


if __name__ == "__main__":
    main()
