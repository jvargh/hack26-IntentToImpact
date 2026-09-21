"""Exercise the final HTTP API in-process with real, synthetic-only Foundry calls."""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))

from studio.app import ORIGIN, create_app
from studio.model_client import now
from studio.service import write_json
from studio.validation import digest, validate

SYNTHETIC = {
    "title": "Community bicycle repair appointments",
    "prompt": (
        "Design a small bicycle repair workshop appointment and order service. Customers request "
        "a repair slot, staff confirm availability, record the inspection and quote, obtain customer "
        "approval, then mark the repair ready for collection. Keep photos and a durable status history. "
        "During busy weekends queued work must not be lost. Two staff manage about 30 jobs per day. "
        "Prefer a low-operations Azure design. No existing cloud integrations or payment processing."
    ),
    "documents": [{
        "id": "workshop-policy", "name": "Synthetic workshop requirements.txt",
        "text": (
            "Customers see only their own repair history. Staff can update repair status. "
            "Quotes require explicit customer acceptance before work. "
            "Repair photos must not be public. Unanswered data retention and recovery targets "
            "must be documented as assumptions rather than invented guarantees."
        ),
    }],
    "refinement": "", "previousResultId": None,
    "idempotencyKey": "synthetic-live-" + str(time.time_ns()), "consentToModel": True,
}


async def main():
    output = ROOT / ".intent-to-impact" / "spikes" / "STUDIO-LIVE-API" / ("http-" + str(time.time_ns()))
    output.mkdir(parents=True)
    app = create_app(data_root=output / "runs")
    started = time.monotonic()
    proof = {"origin": "live-external", "transport": "final-http-api-in-process",
             "syntheticOnly": True, "startedAt": now(), "requestSha256": digest(SYNTHETIC),
             "automaticRetries": 0, "cloudAgentInvocations": 0, "azureResourceMutations": 0}
    try:
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 45123))
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN, headers={"X-Studio-Client": "1"}) as client:
            session = await client.get("/api/studio/session")
            session.raise_for_status()
            headers = {"Origin": ORIGIN, "X-CSRF-Token": session.json()["csrfToken"]}
            response = await client.post("/api/studio/analyses", json=SYNTHETIC, headers=headers)
            if response.status_code != 202:
                proof.update(status="failed", httpStatus=response.status_code, error=response.json())
            else:
                job_id, seen = response.json()["jobId"], set()
                while time.monotonic() - started <= 305:
                    polled = await client.get(f"/api/studio/jobs/{job_id}")
                    polled.raise_for_status()
                    job = polled.json()
                    validate("StudioJob", job)
                    for event in job["events"]:
                        if event["stage"] not in seen:
                            seen.add(event["stage"])
                            print(json.dumps({"stage": event["stage"]}), flush=True)
                    if job["status"] in ("succeeded", "failed"):
                        write_json(output / "job.json", job, immutable=True)
                        proof.update(status=job["status"], jobId=job_id, error=job["error"])
                        if job["result"]:
                            proof.update(
                                resultId=job["result"]["resultId"], resultSha256=digest(job["result"]),
                                modelReceipts=job["result"]["modelReceipts"],
                            )
                        break
                    await asyncio.sleep(0.5)
                else:
                    proof.update(status="failed", error={"code": "smoke_timeout"})
    except Exception as exc:
        proof.update(status="failed", error={"type": type(exc).__name__})
    finally:
        await app.state.service.shutdown()
        proof.update(completedAt=now(), durationMs=round((time.monotonic() - started) * 1000))
        write_json(output / "receipt.json", proof, immutable=True)
    print(json.dumps({"status": proof["status"], "receipt": str(output / "receipt.json"),
                      "modelReceipts": proof.get("modelReceipts"), "error": proof.get("error")}), flush=True)
    return 0 if proof["status"] == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
