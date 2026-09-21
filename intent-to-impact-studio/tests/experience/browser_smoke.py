"""Verify the running historical mock in an isolated, headless Edge browser."""

import hashlib
from importlib.metadata import version as package_version
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from urllib.parse import urlsplit
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "experience" / "initial-v2-r2"
URL = "http://127.0.0.1:5173/legacy-risk"
OUTPUT = ROOT / ".intent-to-impact" / "spikes" / "UI-01-01" / "browser" / (
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    OUTPUT.mkdir(parents=True, exist_ok=False)
    manifest = read(FIXTURES / "manifest.json")
    responses = {
        scene["sceneId"]: read(FIXTURES / scene["response"])
        for scene in manifest["scenes"]
    }
    checks, requests, errors, console_errors, screenshots = [], [], [], [], []
    passed = False
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        version = browser.version
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: console_errors.append({
                "message": message.text, "location": message.location,
            })
                    if message.type == "error" else None)
            page.on("request", lambda request: requests.append(request.url))
            response = page.goto(URL)
            assert response.status == 200
            page.wait_for_load_state("networkidle")

            def select(scene_id):
                page.get_by_label("Review scene").select_option(scene_id)
                expected = responses[scene_id]["operationsRisk"]
                expect(page.locator("#scene-title")).to_have_text(expected["headline"])
                page.wait_for_load_state("networkidle")
                expect(page.locator(".risk-panel")).to_have_attribute("data-risk-state", expected["riskState"])
                expect(page.locator("[data-primary=true]")).to_have_count(1)
                expect(page.get_by_label("Historical fixture notice")).to_contain_text("not current NSP proof")
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), scene_id

            for width in (1440, 768, 390, 320):
                page.set_viewport_size({"width": width, "height": 1000})
                for scene in manifest["scenes"]:
                    select(scene["sceneId"])
                    if width <= 768:
                        expect(page.get_by_role("button", name="Ordered list", exact=True)).to_have_attribute(
                            "aria-pressed", "true"
                        )
                    else:
                        page.get_by_role("button", name="Map", exact=True).click()
                        intersections = page.locator(".continuity-card svg").evaluate("""
                            svg => {
                                const nodes = [...svg.querySelectorAll('[data-node-id] rect')]
                                    .map(node => node.getBoundingClientRect());
                                return [...svg.querySelectorAll('.edge-caption')].flatMap(label => {
                                    const box = label.getBoundingClientRect();
                                    return nodes.filter(node =>
                                        Math.min(box.right, node.right) - Math.max(box.left, node.left) > 0.5 &&
                                        Math.min(box.bottom, node.bottom) - Math.max(box.top, node.top) > 0.5
                                    ).map(() => label.textContent);
                                });
                            }
                        """)
                        assert not intersections, (scene["sceneId"], intersections)
                    checks.append({"scene": scene["sceneId"], "viewportWidth": width, "passed": True})

                select("FX-09")
                if width == 1440:
                    page.get_by_role("button", name="Map", exact=True).click()
                page.locator(".wordmark").click()
                screenshot = OUTPUT / f"risk-{width}.png"
                page.screenshot(path=str(screenshot), full_page=True)
                screenshots.append(screenshot)
                if width <= 768:
                    viewport = OUTPUT / f"risk-{width}-viewport.png"
                    page.screenshot(path=str(viewport), full_page=False)
                    screenshots.append(viewport)

            page.set_viewport_size({"width": 1440, "height": 1000})
            select("FX-01")
            for expected_scene in ("FX-09", "FX-10", "FX-11", "FX-12"):
                page.locator("[data-primary=true]").click()
                expect(page.get_by_label("Review scene")).to_have_value(expected_scene)
                expect(page.locator("#scene-title")).to_have_text(
                    responses[expected_scene]["operationsRisk"]["headline"]
                )
            checks.append({"check": "authored-primary-action-path", "passed": True})

            for width in (1440, 390):
                page.set_viewport_size({"width": width, "height": 1000})
                select("FX-09")
                opener = page.get_by_role("button", name="Inspect evidence", exact=False)
                opener.click()
                dialog = page.get_by_role("dialog", name="Inspect the evidence.")
                expect(dialog).to_be_visible()
                expect(page.get_by_role("button", name="Close evidence")).to_be_focused()
                expect(dialog).to_contain_text("ineligible for live proof")
                page.keyboard.press("Shift+Tab")
                expect(page.get_by_role("button", name="Return to snapshot")).to_be_focused()
                for _ in range(16):
                    page.keyboard.press("Tab")
                    assert page.evaluate("Boolean(document.activeElement.closest('[role=dialog]'))")
                dialog.evaluate("element => { element.scrollTop = 0; }")
                screenshot = OUTPUT / f"evidence-{width}.png"
                page.screenshot(path=str(screenshot), full_page=False)
                screenshots.append(screenshot)
                dialog.get_by_text("Technical references & hashes", exact=True).first.click()
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                page.keyboard.press("Escape")
                expect(dialog).to_have_count(0)
                expect(opener).to_be_focused()
                checks.append({"check": "drawer-keyboard-focus-and-reflow", "viewportWidth": width, "passed": True})

            page.goto(URL + "/?scene=UNKNOWN-SCENE")
            page.wait_for_load_state("networkidle")
            expect(page.get_by_role("alert")).to_be_visible()
            expect(page.locator(".risk-panel")).to_have_count(0)
            checks.append({"check": "unknown-scene-fails-visibly", "passed": True})
            external = [url for url in requests if urlsplit(url).netloc != urlsplit(URL).netloc]
            assert not external, external
            assert not errors, errors
            assert not console_errors, console_errors
            checks.append({"check": "no-external-requests-or-browser-errors", "passed": True})
            passed = True
        finally:
            failure = repr(sys.exception()) if sys.exception() else None
            browser.close()
            receipt = {
                "status": "passed" if passed else "failed",
                "evidenceOrigin": "live-local-browser",
                "fixtureOrigin": "fixture/ux-mock",
                "scenario": manifest["scenario"],
                "fixtureRevision": manifest["fixtureRevision"],
                "browser": {"channel": "msedge", "version": version, "headless": True,
                            "playwrightVersion": package_version("playwright")},
                "url": URL,
                "checks": checks,
                "failure": failure,
                "pageErrors": errors,
                "consoleErrors": console_errors,
                "requests": sorted(set(requests)),
                "screenshots": [
                    {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                    for path in screenshots
                ],
                "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "sourceFiles": [
                    {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                    for path in [
                        *sorted((ROOT / "apps" / "experience" / "src").rglob("*.*")),
                        ROOT / "apps" / "experience" / "index.html",
                        ROOT / "apps" / "experience" / "public" / "favicon.svg",
                        ROOT / "apps" / "experience" / "package-lock.json",
                        FIXTURES / "manifest.json",
                    ] if path.is_file()
                ],
                "completedAt": datetime.now(timezone.utc).isoformat(),
                "limitations": [
                    "Historical seven-scene V2 preview only; not current NSP/V3 proof.",
                    "Viewport reflow checks are not a claim of browser zoom testing.",
                    "No human review, GATE-UX01 or full live-task acceptance.",
                ],
            }
            (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": receipt["status"], "checks": len(checks),
                              "evidence": str(OUTPUT.relative_to(ROOT))}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
