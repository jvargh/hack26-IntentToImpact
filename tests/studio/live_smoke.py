"""Explicit opt-in synthetic live inference and local compilation through the studio API."""

import argparse
import hashlib
import http.cookiejar
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener
from uuid import uuid4
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-live", action="store_true", help="Consent to synthetic model inference charges; no Azure deployment.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--refine", action="store_true", help="Make one additional synthesis/assurance pair for a revised requirement.")
    args = parser.parse_args()
    if not args.execute_live:
        parser.error("--execute-live is required; no model request was sent.")
    parsed = urlsplit(args.base_url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port or parsed.path or parsed.query or parsed.fragment:
        parser.error("Only a bare IPv4 loopback HTTP origin with a port is allowed.")
    output = ROOT / ".intent-to-impact" / "spikes" / "STUDIO-INTEGRATION" / uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    receipt = {"status": "running", "origin": "live-external-model-and-live-local-compiler", "azureDeploymentAttempted": False, "checks": []}

    def call(path, body=None, csrf=None):
        headers = {"X-Studio-Client": "1", "Origin": args.base_url}
        data = None
        if body is not None:
            headers.update({"Content-Type": "application/json", "X-CSRF-Token": csrf})
            data = json.dumps(body).encode()
        try:
            with opener.open(Request(args.base_url + path, data=data, headers=headers), timeout=180) as response:
                return json.load(response)
        except HTTPError as error:
            payload = error.read(4096).decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {error.code} from {path}: {payload}") from error

    def analyze(payload, csrf):
        job = call("/api/studio/analyses", payload, csrf)
        deadline = time.monotonic() + 330
        last = None
        while job["status"] in {"queued", "running"}:
            if time.monotonic() >= deadline:
                raise TimeoutError("Analysis deadline reached; do not automatically resubmit an uncertain request.")
            for event in job["events"]:
                marker = (event["sequence"], event["message"])
                if marker != last and event == job["events"][-1]:
                    print(f"{event['stage']}: {event['message']}", flush=True)
                    last = marker
            time.sleep(1.5)
            job = call(f"/api/studio/jobs/{job['jobId']}")
        if job["status"] != "succeeded":
            (output / f"{job['jobId']}.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
            raise RuntimeError(f"Live analysis failed: {job['error']}")
        result = job["result"]
        assert result["origin"] == "live-model"
        assert {item["role"] for item in result["modelReceipts"]} == {"synthesis", "assurance"}
        assert all(item["responseId"] for item in result["modelReceipts"])
        assert len(result["analysis"]["review"]) == 9
        (output / f"{result['resultId']}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    try:
        csrf = call("/api/studio/session")["csrfToken"]
        health = call("/api/studio/health")
        if not health["ready"]:
            raise RuntimeError(health["message"])
        payload = {
            "title": "Synthetic repair-booking live proof",
            "prompt": "Design a small repair-booking portal for customers and workshop operators. Customers request a booking and receive status updates. Preserve repair records and recover scheduled notification work after a temporary outage. Prefer a simple managed Azure design for a small team.",
            "documents": [{
                "id": "process-source", "name": "synthetic-repair-process.md",
                "text": "A customer submits a repair request. An operator allocates a workshop slot. The customer is notified of confirmation and completion. Workshop staff must see pending work. Do not store payment card data. Budget, peak demand and recovery targets need confirmation."
            }],
            "refinement": "", "previousResultId": None,
            "idempotencyKey": uuid4().hex, "consentToModel": True,
        }
        result = analyze(payload, csrf)
        receipt["checks"].append({"name": "actual-source-grounded-synthesis-and-separate-assurance", "resultId": result["resultId"], "modelReceipts": result["modelReceipts"]})
        if args.refine:
            revised = analyze({
                **payload, "previousResultId": result["resultId"], "idempotencyKey": uuid4().hex,
                "refinement": "Notifications must continue to be accepted if the notification worker is offline. Use durable buffering and explicitly identify replay and duplicate-delivery risks.",
            }, csrf)
            assert revised["resultId"] != result["resultId"] and revised["inputHash"] != result["inputHash"]
            assert revised["analysis"]["changeSummary"]
            receipt["checks"].append({"name": "actual-model-refinement", "resultId": revised["resultId"], "modelReceipts": revised["modelReceipts"], "changeSummary": revised["analysis"]["changeSummary"]})
            result = revised
        option_id = result["analysis"]["recommendedOptionId"]
        build = call("/api/studio/builds", {
            "resultId": result["resultId"], "optionId": option_id,
            "confirmGeneration": True, "idempotencyKey": uuid4().hex,
        }, csrf)
        (output / "build.json").write_text(json.dumps(build, indent=2), encoding="utf-8")
        assert build["resultId"] == result["resultId"] and build["optionId"] == option_id
        assert build["status"] == "compiled", build["diagnostics"]
        assert build["exitCode"] == 0 and build["compilerVersion"]
        assert build["deploymentStatus"] == "not-deployed"
        expected = f"/api/studio/builds/{build['buildId']}/download"
        assert build["downloadUrl"] == expected
        with opener.open(Request(args.base_url + expected, headers={"X-Studio-Client": "1", "Origin": args.base_url}), timeout=30) as response:
            assert "application/zip" in response.headers["Content-Type"]
            archive = response.read(8_000_000)
        package = output / "package.zip"
        package.write_bytes(archive)
        with zipfile.ZipFile(package) as zipped:
            assert "main.bicep" in zipped.namelist() and "main.parameters.json" in zipped.namelist()
            assert not any(Path(name).is_absolute() or ".." in Path(name).parts for name in zipped.namelist())
            for file in build["files"]:
                if file["path"] in zipped.namelist():
                    actual = zipped.read(file["path"])
                    assert actual.decode("utf-8") == file["content"]
                    assert hashlib.sha256(actual).hexdigest() == file["sha256"].removeprefix("sha256:")
        receipt["checks"].append({"name": "actual-compiled-zip", "buildId": build["buildId"], "compilerVersion": build["compilerVersion"], "sha256": hashlib.sha256(archive).hexdigest()})
        receipt["status"] = "passed"
    except Exception as error:
        receipt["status"] = "failed"
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": receipt["status"], "evidence": str(output.relative_to(ROOT))}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
