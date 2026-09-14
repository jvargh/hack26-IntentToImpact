"""Read-only browser layout checks on a real saved topology; no new inference."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True)
    args = parser.parse_args()
    output = ROOT / ".intent-to-impact" / "spikes" / "CANVAS-LAYOUT" / uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    checks, errors, writes, scenes = [], [], [], []
    status = "failed"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1600, "height": 1050}, reduced_motion="reduce")
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.on("request", lambda request: writes.append(request.url) if request.method not in ("GET", "HEAD") else None)
            page.goto("http://127.0.0.1:5173/")
            page.wait_for_load_state("networkidle")
            page.get_by_role("button", name="Run history", exact=True).click()
            history = page.get_by_role("dialog", name="Run history", exact=True)
            history.get_by_label("Earlier runs", exact=False).select_option(args.job)
            expect(history.get_by_text(args.job, exact=True)).to_be_visible()
            response = page.request.get(f"http://127.0.0.1:5173/api/studio/history/{args.job}", headers={"X-Studio-Client": "1"})
            assert response.status == 200
            saved = response.json()
            options = saved["job"]["result"]["analysis"]["options"]
            history.get_by_role("button", name="Open this run", exact=True).click()
            expect(page.get_by_text("SAVED MODEL RESULT", exact=True)).to_be_visible()

            def geometry():
                return page.locator(".st-graph-plane .st-node").evaluate_all(
                    "(nodes) => nodes.map(node => ({id: node.getAttribute('aria-label'), x:parseFloat(node.style.left),"
                    "y:parseFloat(node.style.top), w:node.offsetWidth, h:node.offsetHeight}))")

            for index, option in enumerate(options):
                page.get_by_role("group", name="Architecture alternatives", exact=True).get_by_role("button").nth(index).click()
                page.get_by_role("button", name="Re-layout", exact=True).click()
                nodes = geometry()
                assert len(nodes) == len(option["components"])
                assert page.locator("[data-edge-id]").count() == len(option["connections"])
                for i, node in enumerate(nodes):
                    for other in nodes[i + 1:]:
                        assert (node["x"] + node["w"] <= other["x"] or other["x"] + other["w"] <= node["x"]
                                or node["y"] + node["h"] <= other["y"] or other["y"] + other["h"] <= node["y"]), (node, other)
                assert max(sum(other["x"] == node["x"] for other in nodes) for node in nodes) <= 4
                paths = page.locator("[data-edge-id] > path").evaluate_all("(paths) => paths.map(path => path.getAttribute('d'))")
                assert all("C" not in path and "NaN" not in path for path in paths), "Routes must not use the old backward swooping curve."
                scenes.append({"option": option["id"], "nodes": nodes, "edgeCount": len(paths)})
                page.screenshot(path=str(output / f"{index + 1}-layered.png"))
                checks.append(f"{option['id']}-all-nodes-and-edges-no-block-overlap-or-saturated-column")

            page.get_by_role("button", name="Expand", exact=True).click()
            expect(page.get_by_role("button", name="Restore panels", exact=True)).to_be_visible()
            page.get_by_role("button", name="Fit", exact=True).click()
            page.screenshot(path=str(output / "expanded-layout.png"))
            assert int(page.get_by_label("Canvas zoom").inner_text().replace("%", "")) >= 70, "Expanded view must make this saved topology readable, not just add empty width."
            bounds = page.locator(".st-graph-viewport").bounding_box()
            for box in page.locator(".st-graph-plane .st-node").all():
                rect = box.bounding_box()
                assert rect["x"] >= bounds["x"] - 1 and rect["y"] >= bounds["y"] - 1
                assert rect["x"] + rect["width"] <= bounds["x"] + bounds["width"] + 1
                assert rect["y"] + rect["height"] <= bounds["y"] + bounds["height"] + 1
            checks.append("expanded-fit-keeps-all-nodes-inside-visible-canvas")

            node = page.locator(".st-graph-plane .st-node").first
            original = node.evaluate("(node) => node.style.left")
            node.focus()
            page.keyboard.press("Shift+ArrowRight")
            moved = node.evaluate("(node) => node.style.left")
            assert moved != original
            page.get_by_role("button", name="Fit", exact=True).click()
            assert node.evaluate("(node) => node.style.left") == moved
            page.get_by_role("button", name="Re-layout", exact=True).click()
            assert node.evaluate("(node) => node.style.left") == original
            checks.append("fit-preserves-manual-position-and-relayout-restores-it")

            before = geometry()
            page.get_by_role("combobox", name="Flow direction", exact=True).select_option("TB")
            assert geometry() != before
            page.get_by_role("button", name="Labels", exact=True).click()
            expect(page.get_by_role("button", name="Labels", exact=True)).to_have_attribute("aria-pressed", "true")
            page.screenshot(path=str(output / "top-down-layout.png"))
            page.get_by_role("button", name="List view", exact=True).click()
            expect(page.get_by_role("button", name="Re-layout", exact=True)).to_be_disabled()
            assert page.locator(".st-list-connections li").count() == len(options[-1]["connections"])
            checks.append("direction-labels-and-complete-list-controls")
            assert not writes, writes
            assert not errors, errors
            status = "passed"
        finally:
            receipt = {"status": status, "at": datetime.now(timezone.utc).isoformat(), "jobId": args.job,
                       "checks": checks, "browserErrors": errors, "writeRequests": writes, "modelCalls": 0, "scenes": scenes}
            (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            print(json.dumps({"output": str(output), "status": status, "checks": checks, "browserErrors": errors, "modelCalls": 0}), flush=True)
            browser.close()


if __name__ == "__main__":
    main()
