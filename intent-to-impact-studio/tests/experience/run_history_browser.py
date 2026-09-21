"""Read and download existing workspace history in a real browser; no inference."""

import json
from pathlib import Path
import sys
from uuid import uuid4
import zipfile

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".intent-to-impact" / "spikes" / "RUN-HISTORY" / uuid4().hex
REFERENCE = ROOT / ".intent-to-impact" / "spikes" / "STUDIO-BROWSER" / "3f1553cb8934444abddd7abb696c12cc" / "initial-result.json"


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    expected_result = json.loads(REFERENCE.read_text(encoding="utf-8"))
    checks, requests, errors, indexes, runs = [], [], [], [], []
    status = "failed"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1000}, accept_downloads=True)
            page.on("request", lambda request: requests.append({"url": request.url, "method": request.method}))
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)

            def response_seen(response):
                if response.status != 200:
                    return
                if response.url.endswith("/api/studio/history"):
                    indexes.append(response.json())
                elif "/api/studio/history/job_" in response.url and "/builds/" not in response.url and not response.url.endswith("/download"):
                    runs.append(response.json())

            page.on("response", response_seen)
            assert page.goto("http://127.0.0.1:5173/").status == 200
            page.wait_for_load_state("networkidle")
            page.get_by_role("button", name="Run history", exact=True).click()
            dialog = page.get_by_role("dialog", name="Run history", exact=True)
            expect(dialog).to_contain_text("Shared local workspace")
            expect(page.get_by_label("Earlier runs", exact=False)).to_be_visible()
            assert indexes and indexes[-1]["scope"] == "workspace"
            chosen = next(row for row in indexes[-1]["runs"] if row["resultId"] == expected_result["resultId"])
            page.get_by_label("Earlier runs", exact=False).select_option(chosen["jobId"])
            expect(dialog.get_by_text(chosen["jobId"], exact=True)).to_be_visible()
            selected = next(run for run in reversed(runs) if run["summary"]["jobId"] == chosen["jobId"])
            assert selected["job"]["result"]["resultId"] == expected_result["resultId"]
            checks.append("real-shared-history-includes-earlier-browser-session-run")
            page.screenshot(path=str(OUT / "history-desktop.png"))
            with page.expect_download() as record_download:
                page.get_by_role("button", name="Download run record ZIP", exact=True).click()
            archive = OUT / "saved-run.zip"
            record_download.value.save_as(archive)
            with zipfile.ZipFile(archive) as z:
                inputs = json.loads(z.read("inputs.json"))
                state = json.loads(z.read("run.json"))
                assert inputs["prompt"] == selected["inputs"]["prompt"]
                assert state["job"]["result"] == expected_result
                assert "owner" not in state and "idempotencyKey" not in inputs and "consentToModel" not in inputs
                assert "sessions.json" not in z.namelist()
                for index, document in enumerate(inputs["documents"], 1):
                    assert z.read(f"documents/{index:02d}.txt").decode("utf-8") == document["text"]
            checks.append("actual-run-archive-with-original-inputs-and-no-session-secrets")
            with page.expect_download() as package_download:
                page.get_by_role("button", name="Download saved package", exact=True).first.click()
            package = OUT / "saved-package.zip"
            package_download.value.save_as(package)
            with zipfile.ZipFile(package) as z:
                assert "main.bicep" in z.namelist() and "main.json" in z.namelist()
            checks.append("existing-compiled-package-download-without-new-build")
            page.get_by_role("button", name="Open this run", exact=True).click()
            expect(page.get_by_text("SAVED MODEL RESULT", exact=True)).to_be_visible()
            expect(page.get_by_role("textbox", name="What should this system do?")).to_have_value(inputs["prompt"])
            expect(page.get_by_role("checkbox", name="I consent to send", exact=False)).not_to_be_checked()
            page.get_by_role("tab", name="Build", exact=True).click()
            expect(page.get_by_role("button", name="Download compiled ZIP", exact=False)).to_be_visible()
            checks.append("restore-inputs-result-and-package-with-fresh-consent-required")
            page.screenshot(path=str(OUT / "restored-run.png"))
            page.get_by_role("button", name="Run history", exact=True).click()
            expect(page.get_by_role("button", name="Close run history")).to_be_focused()
            page.set_viewport_size({"width": 390, "height": 900})
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            page.screenshot(path=str(OUT / "history-mobile.png"))
            page.keyboard.press("Escape")
            expect(page.get_by_role("dialog")).to_have_count(0)
            expect(page.get_by_role("button", name="Run history", exact=True)).to_be_focused()
            checks.append("history-drawer-focus-escape-and-narrow-reflow")
            page.reload()
            page.wait_for_load_state("networkidle")
            page.get_by_role("button", name="Run history", exact=True).click()
            expect(page.get_by_label("Earlier runs", exact=False)).to_be_visible()
            assert any(row["jobId"] == chosen["jobId"] for row in indexes[-1]["runs"])
            assert all(request["method"] == "GET" for request in requests), requests
            assert not errors, errors
            checks.append("history-persists-after-reload-with-no-model-or-build-POST")
            status = "passed"
        finally:
            failure = repr(sys.exception()) if sys.exception() else None
            browser.close()
            receipt = {"status": status, "checks": checks, "error": failure, "browserErrors": errors,
                       "source": "actual saved local workspace runs, not mocked API data",
                       "historyScope": "workspace, explicitly selected by user",
                       "modelCalls": 0, "newBuilds": 0, "azureMutations": 0}
            (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": status, "checks": checks, "evidence": str(OUT.relative_to(ROOT))}))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
