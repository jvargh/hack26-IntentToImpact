"""Real browser interaction checks over a replayed design; no model calls."""

import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / ".intent-to-impact" / "spikes" / "STUDIO-BROWSER" / "3f1553cb8934444abddd7abb696c12cc" / "initial-result.json"
OUTPUT = ROOT / ".intent-to-impact" / "spikes" / "CANVAS-ZOOM" / uuid4().hex


def main():
    OUTPUT.mkdir(parents=True, exist_ok=False)
    result = json.loads(FIXTURE.read_text(encoding="utf-8"))
    checks, errors, api_calls = [], [], []
    status = "failed"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 950})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)

            def api(route):
                path = route.request.url.split("/api/studio/", 1)[1]
                api_calls.append(path)
                if path == "session":
                    body = {"csrfToken": "synthetic-local-zoom-test-csrf-not-a-real-session"}
                elif path == "health":
                    body = {"ready": True, "model": "replayed-design-for-zoom-test", "message": "UI interaction fixture only"}
                elif path == "analyses":
                    body = {
                        "jobId": "job-zoom-fixture", "status": "succeeded", "result": result, "error": None,
                        "events": [{"sequence": 1, "stage": "complete", "message": "Replayed design for UI controls, no inference.",
                                    "at": "2026-09-13T00:00:00Z"}],
                    }
                else:
                    raise AssertionError(f"Unexpected API call: {path}")
                route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

            page.route("**/api/studio/**", api)
            page.goto("http://127.0.0.1:5173/")
            page.wait_for_load_state("networkidle")
            page.get_by_role("textbox", name="What should this system do?").fill("UI interaction fixture only; no model call.")
            page.get_by_role("checkbox", name="I consent to send", exact=False).check()
            page.get_by_role("button", name="Generate architecture", exact=False).click()
            expect(page.get_by_text("LIVE MODEL RESULT", exact=True)).to_be_visible()
            canvas = page.get_by_role("region", name="Interactive architecture canvas")
            zoom = page.get_by_label("Canvas zoom")
            percent = lambda: int(zoom.inner_text().replace("%", ""))
            canvas.focus()
            start = percent()
            page.keyboard.press("Control+=")
            expect(zoom).not_to_have_text(f"{start}%")
            assert percent() > start
            page.keyboard.press("Control+-")
            expect(zoom).to_have_text(f"{start}%")
            page.keyboard.press("Control+Shift+=")
            assert percent() > start
            page.keyboard.press("Control+0")
            fit_zoom = percent()
            checks.append("Ctrl-plus-minus-shift-plus-and-fit")

            viewport = page.locator(".st-graph-viewport")
            bounds = viewport.bounding_box()
            x, y = round(bounds["x"] + bounds["width"] * 0.6), round(bounds["y"] + bounds["height"] * 0.4)
            page.mouse.move(x, y)
            world = lambda: page.locator(".st-graph-plane").evaluate(
                """(plane, point) => {
                    const viewport = plane.parentElement.getBoundingClientRect();
                    const matrix = new DOMMatrix(getComputedStyle(plane).transform);
                    return {x: (point.x - viewport.left - matrix.e) / matrix.a,
                            y: (point.y - viewport.top - matrix.f) / matrix.a};
                }""", {"x": x, "y": y})
            before = world()
            page.keyboard.down("Control")
            page.mouse.wheel(0, -100)
            page.keyboard.up("Control")
            expect(zoom).not_to_have_text(f"{fit_zoom}%")
            assert percent() > fit_zoom
            after = world()
            assert abs(before["x"] - after["x"]) < 0.05 and abs(before["y"] - after["y"]) < 0.05, {"before": before, "after": after, "pointer": [x, y]}
            page.keyboard.down("Control")
            page.mouse.wheel(0, 100)
            page.keyboard.up("Control")
            expect(zoom).to_have_text(f"{fit_zoom}%")
            checks.append("native-Ctrl-mouse-wheel-both-directions-anchored-at-pointer")

            page.evaluate("""document.addEventListener('keydown', event => {
                if (event.ctrlKey && ['=', '+', '-'].includes(event.key))
                    window.zoomShortcutPrevented = event.defaultPrevented;
            })""")
            prompt = page.get_by_role("textbox", name="What should this system do?")
            prompt.focus()
            page.keyboard.press("Control+=")
            assert page.evaluate("window.zoomShortcutPrevented") is False
            page.keyboard.press("Control+0")
            page.get_by_role("link", name="Intent to Impact Studio home").focus()
            page.mouse.move(100, 40)
            page.keyboard.press("Control+-")
            assert page.evaluate("window.zoomShortcutPrevented") is False
            page.keyboard.press("Control+0")
            checks.append("browser-shortcuts-not-intercepted-in-input-or-outside-canvas")

            canvas.focus()
            for _ in range(30):
                page.keyboard.press("Control+=")
            expect(zoom).to_have_text("180%")
            expect(page.get_by_role("button", name="Zoom in", exact=True)).to_be_disabled()
            for _ in range(30):
                page.keyboard.press("Control+-")
            expect(zoom).to_have_text("25%")
            expect(page.get_by_role("button", name="Zoom out", exact=True)).to_be_disabled()
            page.get_by_role("button", name="Zoom in", exact=True).click()
            assert percent() > 25
            page.get_by_role("button", name="Fit", exact=True).click()
            checks.append("limits-and-existing-toolbar-controls")
            page.screenshot(path=str(OUTPUT / "canvas-controls.png"))
            page.get_by_role("button", name="List view", exact=True).click()
            expect(page.get_by_role("button", name="Zoom in", exact=True)).to_be_disabled()
            prior = percent()
            canvas.focus()
            page.keyboard.press("Control+=")
            assert percent() == prior
            checks.append("list-view-does-not-consume-canvas-zoom")
            assert not errors, errors
            assert api_calls == ["session", "health", "analyses"], api_calls
            status = "passed"
        finally:
            failure = repr(sys.exception()) if sys.exception() else None
            browser.close()
            receipt = {
                "status": status, "checks": checks, "error": failure, "browserErrors": errors,
                "evidenceOrigin": "live-local-browser-interactions", "modelCalls": 0,
                "apiResponses": "explicitly replayed UI fixture; no live inference or backend proof",
                "fixture": str(FIXTURE.relative_to(ROOT)),
                "completedAt": datetime.now(timezone.utc).isoformat(),
            }
            (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": status, "checks": checks, "evidence": str(OUTPUT.relative_to(ROOT))}))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
