"""Exercise the business-first frontend without AI, uploads or a backend."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
URL = "http://127.0.0.1:5173/"
KEY = "intent-to-impact.business-draft.v1"
OUT = ROOT / ".intent-to-impact" / "spikes" / "UI-BUSINESS-FIRST" / (
    "browser-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
)
DIMENSIONS = [
    "Business fit", "Security & privacy", "Reliability & recovery",
    "Performance & scale", "Cost & efficiency", "Integration & data",
    "Compliance & governance", "Operations & observability", "Delivery & evolution",
]
STEPS = ["Your business", "Understanding", "Architecture", "360 review", "Design brief"]


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    checks, screenshots, errors, requests = [], [], [], []
    passed = False
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 1050}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.on("request", lambda request: requests.append({"url": request.url, "method": request.method}))
            page.on("dialog", lambda dialog: dialog.accept())
            assert page.goto(URL).status == 200
            page.wait_for_load_state("networkidle")
            expect(page.get_by_role("heading", level=1)).to_contain_text("Turn your business process")
            expect(page.get_by_role("textbox", name="What are you trying to achieve?")).to_have_value("")
            expect(page.get_by_text("Frontend preview · AI analysis not connected")).to_be_visible()

            def nav(name):
                return page.get_by_role("navigation", name="Architecture design steps").get_by_role("button", name=name, exact=False)

            def take(name, full=False):
                page.evaluate("window.scrollTo(0,0)")
                path = OUT / f"{name}.png"
                page.screenshot(path=str(path), full_page=full)
                screenshots.append(path)

            def check_reflow(label):
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), label
                checks.append({"check": label, "passed": True})

            take("intake-desktop", True)
            page.get_by_role("button", name="Build my brief", exact=False).click()
            expect(page.get_by_role("alert")).to_contain_text("Describe the business")
            check_reflow("empty-intake-and-validation")
            title = "A better repair workshop"
            prompt = "Help us design a repair booking process with customer updates and clear operator ownership."
            doc_text = "# Repair process\nA customer requests a repair. An operator confirms a slot.\nRAW-ATTACHMENT-MARKER\n<script>window.documentWasExecuted=true</script>"
            page.get_by_role("textbox", name="Project name", exact=False).fill(title)
            page.get_by_role("textbox", name="What are you trying to achieve?").fill(prompt)
            upload = page.get_by_label("Attach business-process documents")
            upload.set_input_files({"name": "repair-process.md", "mimeType": "text/markdown", "buffer": doc_text.encode()})
            expect(page.get_by_role("status")).to_contain_text("1 document attached locally")
            assert page.evaluate(f"localStorage.getItem('{KEY}')") is None
            upload.set_input_files({"name": "unsupported.pdf", "mimeType": "application/pdf", "buffer": b"not-a-pdf"})
            expect(page.get_by_role("alert")).to_contain_text("TXT and Markdown")
            expect(page.get_by_role("textbox", name="What are you trying to achieve?")).to_have_value(prompt)
            source = page.get_by_role("button", name="repair-process.md", exact=True)
            source.click()
            modal = page.get_by_role("dialog", name="repair-process.md")
            expect(modal).to_contain_text("RAW-ATTACHMENT-MARKER")
            expect(page.get_by_role("button", name="Close dialog")).to_be_focused()
            page.keyboard.press("Shift+Tab")
            expect(page.get_by_role("button", name="Edit local copy")).to_be_focused()
            for _ in range(8):
                page.keyboard.press("Tab")
                assert page.evaluate("Boolean(document.activeElement.closest('[role=dialog]'))")
            page.keyboard.press("Escape")
            expect(modal).to_have_count(0)
            expect(source).to_be_focused()
            assert page.evaluate("window.documentWasExecuted") is None
            checks.append({"check": "actual-local-document-read-safe-render-focus-no-autosave", "passed": True})
            page.get_by_role("button", name="Build my brief", exact=False).click()
            expect(page.get_by_role("textbox", name="Business outcome")).to_have_value(prompt)
            expect(page.get_by_role("textbox", name="People & responsibilities")).to_have_value("")
            page.get_by_role("textbox", name="People & responsibilities").fill("Customers, workshop operators and a service manager.")
            page.get_by_role("textbox", name="The process, step by step").fill("Request -> schedule -> repair -> customer update")
            page.get_by_role("textbox", name="What normal and peak volumes", exact=False).fill("100 bookings per day")
            take("understanding-custom-desktop", True)
            page.get_by_role("button", name="Explore architecture", exact=False).click()
            page.get_by_role("button", name="Use Modular application").click()
            expect(page.get_by_role("button", name="Use Modular application")).to_have_attribute("aria-pressed", "true")
            page.get_by_role("textbox", name="Your design rationale").fill("Keep initial delivery simple for our small team.")
            expect(page.locator("#wb-main button.wb-primary")).to_have_count(1)
            take("architecture-desktop", True)
            page.get_by_role("button", name="Open the 360 review", exact=False).click()
            expect(page.get_by_text("Your project has not been assessed.")).to_be_visible()
            for dimension in DIMENSIONS:
                expect(page.get_by_role("heading", name=dimension, exact=True)).to_be_visible()
            expect(page.get_by_text("What the example surfaces", exact=True)).to_have_count(0)
            page.get_by_label("Review status for Security & privacy").select_option("needs-work")
            page.get_by_label("Notes for Security & privacy").fill("Confirm workshop role permissions.")
            checks.append({"check": "custom-understanding-pattern-and-nine-unassessed-review-dimensions", "passed": True})
            page.get_by_role("button", name="Bring it into a design brief", exact=False).click()
            expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
            with page.expect_download() as download_event:
                page.get_by_role("button", name="Download design brief", exact=False).click()
            download = download_event.value
            path = OUT / "custom-design-brief.md"
            download.save_as(path)
            exported = path.read_text(encoding="utf-8")
            for expected in (prompt, "100 bookings per day", "Modular application", "Confirm workshop role permissions.", "```mermaid"):
                assert expected in exported
            assert "RAW-ATTACHMENT-MARKER" not in exported
            assert "Illustrative finding" not in exported
            assert "AI analysis is not connected" in exported
            take("handoff-desktop", True)
            checks.append({"check": "real-markdown-download-preserves-custom-content-and-limits", "passed": True})
            page.get_by_role("button", name="Save in browser").click()
            expect(page.get_by_role("dialog")).to_contain_text("full document contents")
            assert page.evaluate(f"localStorage.getItem('{KEY}')") is None
            page.get_by_role("button", name="Save draft locally").click()
            expect(page.get_by_role("status")).to_contain_text("Draft saved in this browser")
            saved = json.loads(page.evaluate(f"localStorage.getItem('{KEY}')"))
            assert saved["prompt"] == prompt and saved["documents"][0]["text"] == doc_text
            page.reload()
            page.wait_for_load_state("networkidle")
            page.get_by_role("button", name="Resume saved draft").click()
            page.get_by_role("button", name="Open saved draft").click()
            expect(page.get_by_role("textbox", name="What are you trying to achieve?")).to_have_value(prompt)
            checks.append({"check": "explicit-save-and-resume-with-documents", "passed": True})
            page.get_by_role("button", name="Try worked example", exact=False).click()
            expect(page.get_by_role("dialog")).to_contain_text("Replacing it discards")
            page.get_by_role("button", name="Cancel", exact=True).click()
            expect(page.get_by_role("textbox", name="What are you trying to achieve?")).to_have_value(prompt)
            page.get_by_role("button", name="Try worked example", exact=False).click()
            page.get_by_role("button", name="Replace with example").click()
            expect(page.get_by_text("Worked example · illustrative", exact=True)).to_be_visible()
            page.get_by_role("button", name="Build my brief", exact=False).click()
            expect(page.get_by_text("Sample answers are filled in", exact=False)).to_be_visible()
            for question, answer_fragment in (
                ("What normal and peak volumes", "2,000 orders per day"),
                ("How much downtime and data loss", "60 minutes"),
                ("What is the monthly budget", "USD 1,500"),
                ("Who owns integrations", "Fulfilment operations"),
            ):
                answer = page.get_by_role("textbox", name=question, exact=False).input_value()
                assert answer_fragment in answer, (question, answer)
            take("example-understanding-with-answers", True)
            checks.append({"check": "worked-example-clarifications-prefilled-with-labelled-sample-answers", "passed": True})
            page.get_by_role("button", name="Explore architecture", exact=False).click()
            page.get_by_role("button", name="Use Event-driven services").click()
            page.get_by_role("button", name="Open the 360 review", exact=False).click()
            expect(page.get_by_text("What the example surfaces", exact=True)).to_have_count(9)
            page.get_by_role("button", name="Operating requirements.md", exact=False).first.click()
            expect(page.get_by_role("dialog")).to_contain_text("EU customer contact data")
            page.keyboard.press("Escape")
            take("assessment-example-desktop", True)
            checks.append({"check": "explicit-worked-example-and-traceable-source-dialog", "passed": True})
            for width in (1440, 768, 390, 320):
                page.set_viewport_size({"width": width, "height": 950})
                for step in STEPS:
                    nav(step).click()
                    expect(page.locator("#wb-page-title")).to_be_visible()
                    check_reflow(f"reflow-{width}-{step}")
                    if width in (1440, 390):
                        take(f"example-{step.replace(' ', '-')}-{width}")
            nav("Your business").click()
            page.get_by_role("textbox", name="What are you trying to achieve?").fill("A new unrelated process")
            nav("360 review").click()
            expect(page.get_by_text("Your project has not been assessed.")).to_be_visible()
            expect(page.get_by_text("What the example surfaces", exact=True)).to_have_count(0)
            checks.append({"check": "editing-example-input-invalidates-illustrative-findings", "passed": True})
            external = [request for request in requests if urlsplit(request["url"]).netloc != urlsplit(URL).netloc]
            assert not external, external
            assert all(request["method"] == "GET" for request in requests)
            assert not errors, errors
            checks.append({"check": "no-external-requests-or-browser-errors", "passed": True})
            passed = True
        finally:
            browser.close()
            receipt = {
                "status": "passed" if passed else "failed", "taskId": "UI-BUSINESS-FIRST-001",
                "checks": checks, "errors": errors, "requests": requests,
                "browser": "isolated headless Edge", "url": URL, "backendConnected": False,
                "humanUxApproval": "pending", "evidenceOrigin": "live-local-browser",
                "completedAt": datetime.now(timezone.utc).isoformat(),
                "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "screenshots": [{"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in screenshots],
            }
            (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": receipt["status"], "checks": len(checks), "evidence": str(OUT.relative_to(ROOT))}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
