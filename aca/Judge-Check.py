"""Browser verification for explicit ACA simulation; never requests real inference."""

import hashlib
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
import zipfile

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recover-job", help="Verify a previous test session's saved run/package after a container restart.")
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    state = json.loads((folder / ".local" / "deployment-state.json").read_text(encoding="utf-8"))
    url = state["url"]
    output = folder / ".local" / ("judge-check-" + uuid4().hex)
    output.mkdir()
    completed, builds, errors, external = [], [], [], []
    report = {"status": "failed", "url": url, "mode": "simulated", "modelCalls": 0, "checks": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            context = browser.new_context(viewport={"width": 1600, "height": 1100}, accept_downloads=True,
                                          storage_state=str(folder / ".local" / "judge-browser-state.json") if args.recover_job else None)
            page = context.new_page()
            def guard(route):
                if urlsplit(route.request.url).hostname != urlsplit(url).hostname:
                    external.append(route.request.url)
                    route.abort()
                else:
                    route.continue_()
            page.route("**/*", guard)
            page.on("pageerror", lambda error: errors.append(str(error)))
            def receive(response):
                path = urlsplit(response.url).path
                if response.status in (200, 202) and (path.startswith("/api/studio/jobs/") or path == "/api/studio/analyses"):
                    body = response.json()
                    if body["status"] == "succeeded" and all(row["jobId"] != body["jobId"] for row in completed):
                        completed.append(body)
                    if body["status"] == "failed":
                        errors.append(str(body["error"]))
                if response.status == 200 and path == "/api/studio/builds":
                    builds.append(response.json())
            page.on("response", receive)
            page.goto(url)
            expect(page.get_by_text("JUDGE DEMO / SIMULATED AI", exact=True)).to_be_visible(timeout=30000)
            health = context.request.get(url + "/api/studio/health", headers={"X-Studio-Client": "1"})
            assert health.status == 200 and health.json()["mode"] == "simulated", "Refuse to run on a real model endpoint."
            if args.recover_job:
                page.get_by_role("button", name="Run history", exact=True).click()
                history = page.get_by_role("dialog", name="Run history", exact=True)
                history.get_by_label("Earlier runs", exact=False).select_option(args.recover_job)
                expect(history.get_by_text(args.recover_job, exact=True)).to_be_visible()
                history.get_by_role("button", name="Open this run", exact=True).click()
                expect(page.get_by_text("SAVED SIMULATED EXAMPLE", exact=True)).to_be_visible()
                page.get_by_role("tab", name="Build", exact=True).click()
                expect(page.get_by_role("button", name="Download compiled ZIP", exact=True)).to_be_visible(timeout=20000)
                with page.expect_download() as event:
                    page.get_by_role("button", name="Download compiled ZIP", exact=True).click()
                archive = output / "recovered-package.zip"
                event.value.save_as(str(archive))
                with zipfile.ZipFile(archive) as package:
                    assert len(package.namelist()) == 8
                    assert json.loads(package.read("manifest.json"))["origin"] == "simulated"
                report.update(status="passed", jobId=args.recover_job,
                              checks=["NFS-persisted-session-history-recovered", "saved-simulated-design-and-compiled-package-after-restart"])
                page.screenshot(path=str(output / "judge-recovered.png"))
                return
            assert page.get_by_role("checkbox", name="I consent to send", exact=False).count() == 0
            page.get_by_role("button", name="Load example inputs", exact=False).click()
            page.get_by_role("button", name="Generate architecture", exact=True).click()
            expect(page.get_by_text("SIMULATED EXAMPLE", exact=True)).to_be_visible(timeout=30000)
            assert len(completed) == 1 and completed[0]["result"]["origin"] == "simulated"
            assert len(completed[0]["result"]["analysis"]["options"]) == 2
            assert len(completed[0]["result"]["analysis"]["review"]) == 9
            report["checks"].append("Load-Example-Generate-without-login-or-model-consent")
            for row in completed[0]["result"]["modelReceipts"]:
                assert row["origin"] == "simulated" and row["responseId"].startswith("sim_")
            assert page.get_by_text("LIVE MODEL RESULT", exact=True).count() == 0
            page.get_by_role("button", name="Expand", exact=True).click()
            page.get_by_role("button", name="Re-layout", exact=True).click()
            page.screenshot(path=str(output / "judge-architecture.png"))
            page.get_by_role("button", name="Restore panels", exact=True).click()

            for index, intent in enumerate(("recommendation", "challenge"), 2):
                page.get_by_role("tab", name="Assurance", exact=False).click()
                dimension = page.get_by_role("button", name="Review Security:", exact=False)
                if dimension.get_attribute("aria-pressed") != "true":
                    dimension.click()
                page.get_by_role("button", name="Request recommended change" if intent == "recommendation" else "Challenge finding", exact=True).click()
                dialog = page.get_by_role("dialog")
                if intent == "challenge":
                    dialog.get_by_role("textbox").fill("This is a judge walkthrough of a recorded challenge. Show the scripted recovery example.")
                dialog.get_by_role("checkbox", name="I approve this scripted", exact=False).check()
                dialog.get_by_role("button", name="Approve & regenerate", exact=True).click()
                expect(dialog).not_to_be_visible(timeout=30000)
                expect(page.get_by_text("SIMULATED EXAMPLE", exact=True)).to_be_visible()
                assert len(completed) == index
                job = completed[-1]
                assert job["changeApproval"]["intent"] == intent
                assert job["changeApproval"]["baseResultId"] == completed[-2]["result"]["resultId"]
                assert job["result"]["origin"] == "simulated"
                report["checks"].append(f"{intent}-scripted-revision-and-approval-lineage")

            page.get_by_role("tab", name="Build", exact=True).click()
            page.get_by_role("checkbox", name="I confirm package generation only", exact=False).check()
            page.get_by_role("button", name="Generate deployment package", exact=True).click()
            page.get_by_role("button", name="Download compiled ZIP", exact=True).or_(page.get_by_role("alert")).first.wait_for(timeout=150000)
            assert builds and builds[-1]["status"] == "compiled", builds[-1]["diagnostics"] if builds else errors
            build = builds[-1]
            with page.expect_download() as event:
                page.get_by_role("button", name="Download compiled ZIP", exact=True).click()
            archive = output / "judge-package.zip"
            event.value.save_as(str(archive))
            with zipfile.ZipFile(archive) as package:
                assert len(package.namelist()) == 8
                for file in build["files"]:
                    assert hashlib.sha256(package.read(file["path"])).hexdigest() == file["sha256"]
                assert json.loads(package.read("manifest.json"))["origin"] == "simulated"
                assert "simulat" in package.read("README.md").decode().lower()
            report["checks"].append("real-Linux-Bicep-with-simulated-origin-and-matching-ZIP-hashes")
            page.screenshot(path=str(output / "judge-compiled-package.png"))

            page.get_by_role("button", name="Run history", exact=True).click()
            history = page.get_by_role("dialog", name="Run history", exact=True)
            history.get_by_label("Earlier runs", exact=False).select_option(completed[0]["jobId"])
            expect(history.get_by_text("SIMULATED EXAMPLE:", exact=False)).to_be_visible()
            history.get_by_role("button", name="Open this run", exact=True).click()
            history.get_by_role("button", name="Open saved run", exact=True).click()
            expect(page.get_by_text("SAVED SIMULATED EXAMPLE", exact=True)).to_be_visible()
            report["checks"].append("saved-simulation-history-keeps-honest-origin")
            context.storage_state(path=str(folder / ".local" / "judge-browser-state.json"))
            # A different browser must not inherit the public demo's run history.
            other = browser.new_context()
            session = other.request.get(url + "/api/studio/session", headers={"X-Studio-Client": "1"})
            assert session.status == 200
            other_history = other.request.get(url + "/api/studio/history", headers={"X-Studio-Client": "1"})
            assert other_history.json()["runs"] == [] and other_history.json()["scope"] == "session"
            other.close()
            report["checks"].append("anonymous-visitors-have-isolated-history")
            assert not errors and not external, (errors, external)
            report.update(status="passed", jobs=[job["jobId"] for job in completed], buildId=build["buildId"],
                          compiler=build["compilerVersion"], exitCode=build["exitCode"])
        finally:
            report.update(browserErrors=errors, externalBrowserRequests=external)
            (output / "receipt.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps({"output": str(output), **report}), flush=True)
            browser.close()


if __name__ == "__main__":
    main()
