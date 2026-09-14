"""One native-format invocation per already-created approved version; no create API."""

import argparse
import asyncio
import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Literal

from approved_specialists import (
    ApprovalError, ENDPOINT, NAMES, RUN, SUBSCRIPTION, TENANT, PROJECT_ID,
    validate_invocation_body, validate_manifest, validate_readback, sha, write,
)
from discover import digest, now
from spike import safe_error


def error_fields(body):
    error = body.get("error", {})
    result = {}
    for key in ("code", "type", "param"):
        value = error.get(key)
        if value is None or (isinstance(value, str) and re.fullmatch(r"[\w.\- ]{1,100}", value)):
            result[key] = value
    text = str(error.get("message", "")).lower()
    result["knownMessageFragments"] = [word for word in (
        "unknown parameter", "unsupported parameter", "not allowed", "agent_reference",
        "agent", "text.format", "text", "store", "response_format", "max_output_tokens",
        "cannot", "required", "stream", "model", "not found",
    ) if word in text]
    result["messageSha256"] = hashlib.sha256(text.encode()).hexdigest()
    return result


async def run(name):
    import httpx
    from agent_framework.foundry import FoundryAgent
    from azure.ai.projects.aio import AIProjectClient
    from azure.core.pipeline.policies import SansIOHTTPPolicy
    from azure.identity.aio import AzureCliCredential
    from pydantic import ConfigDict, create_model

    logging.disable(logging.CRITICAL)
    validate_manifest()
    creation_file = RUN / "specialist-receipt.json"
    created = json.loads(creation_file.read_text(encoding="utf-8"))
    source = next(r for r in created["rows"] if r["name"] == name)
    version = source.get("createdVersion")
    if not source.get("definitionVerified") or version != "1":
        raise ApprovalError("No verified initial created version exists for this name.")
    filename = f"{name}-native-invocation.json"
    if (RUN / filename).exists():
        raise ApprovalError("This bounded native-format attempt already exists; do not auto-retry.")
    role = NAMES[name]
    receipt = {
        "version": "1.0.0", "task": "SPK-01-01", "status": "in-progress",
        "origin": "live-external", "startedAt": now(), "name": name, "agentVersion": version,
        "agentId": source["createdId"], "projectId": PROJECT_ID, "projectEndpoint": ENDPOINT,
        "subscriptionId": SUBSCRIPTION, "tenantId": TENANT,
        "creationReceiptSha256": sha(creation_file), "sourceSha256": sha(Path(__file__)),
        "sdkVersions": created["sdkVersions"], "requests": [], "automaticRetries": 0,
        "invocationOptions": {"store": False},
        "typedResultBoundary": "Agent Framework response text validated locally as strict Pydantic "
        "marker+specialist; no server schema override and no fixture response.",
        "creationOrUpdateAttempts": 0,
    }

    def flush():
        write(filename, receipt)

    flush()
    wire = receipt["requests"]

    class ReadOnlyVersionPolicy(SansIOHTTPPolicy):
        def on_request(self, request):
            expected = f"{ENDPOINT}/agents/{name}/versions/{version}?api-version=v1"
            if request.http_request.method != "GET" or request.http_request.url != expected:
                raise ApprovalError("Only the exact created-version GET is permitted.")
            wire.append({"method": "GET", "url": expected, "startedAt": now()})
            flush()

        def on_response(self, request, response):
            wire[-1].update(httpStatus=response.http_response.status_code, completedAt=now(),
                            requestId=response.http_response.headers.get("apim-request-id")
                            or response.http_response.headers.get("x-ms-request-id"))
            flush()

    async def before(request):
        if request.method != "POST" or str(request.url) != ENDPOINT + "/openai/v1/responses":
            raise ApprovalError("Only project Responses inference is permitted.")
        if any(r["method"] == "POST" for r in wire):
            raise ApprovalError("A second inference request is not permitted in this attempt.")
        body = json.loads(request.content)
        validate_invocation_body(name, version, body)
        wire.append({
            "method": "POST", "url": str(request.url), "startedAt": now(),
            "requestBodySha256": digest(body), "requestBodyKeys": sorted(body),
            "agentReference": body["agent_reference"], "store": False,
        })
        flush()

    async def after(response):
        wire[-1].update(httpStatus=response.status_code, completedAt=now(),
                        requestId=response.headers.get("x-request-id")
                        or response.headers.get("apim-request-id"))
        if response.status_code >= 400:
            await response.aread()
            wire[-1]["safeError"] = error_fields(response.json())
        flush()

    class Project(AIProjectClient):
        def get_openai_client(self, **kwargs):
            self.probe_client = super().get_openai_client(
                **kwargs, max_retries=0, timeout=45,
                http_client=httpx.AsyncClient(timeout=45, follow_redirects=False, trust_env=False,
                                               event_hooks={"request": [before], "response": [after]}),
            )
            return self.probe_client

    credential = AzureCliCredential(subscription=SUBSCRIPTION, process_timeout=20)
    try:
        async with asyncio.timeout(90), credential:
            async with Project(endpoint=ENDPOINT, credential=credential, retry_total=0,
                               redirect_max=0, per_call_policies=[ReadOnlyVersionPolicy()]) as project:
                data = (await project.agents.get_version(name, version)).as_dict()
                validate_readback(name, version, data)
                receipt["readbackDefinitionSha256"] = digest(data["definition"])
                if receipt["readbackDefinitionSha256"] != source["definitionSha256"]:
                    raise ApprovalError("Definition hash changed since creation.")
                result_type = create_model(
                    "SpecialistProbeResult", __config__=ConfigDict(extra="forbid"),
                    marker=(Literal["SPK-01-01-OK"], ...), specialist=(Literal[role], ...),
                )
                prompt = f'Return only {{"marker":"SPK-01-01-OK","specialist":"{role}"}} as valid JSON.'
                receipt["syntheticInputSha256"] = hashlib.sha256(prompt.encode()).hexdigest()
                agent = FoundryAgent(project_client=project, agent_name=name,
                                     agent_version=version, allow_preview=False)
                start = time.monotonic()
                try:
                    result = await agent.run(prompt, options={"store": False})
                    parsed = result_type.model_validate_json(result.text)
                    receipt.update(
                        status="passed", responseId=result.response_id,
                        responseType=type(result).__name__, localTypedValueType=type(parsed).__name__,
                        result=parsed.model_dump(), resultSha256=digest(parsed.model_dump()),
                        responseTextSha256=hashlib.sha256(result.text.encode()).hexdigest(),
                        finishReason=str(result.finish_reason), usage=dict(result.usage_details or {}),
                        inferenceDurationMs=round((time.monotonic() - start) * 1000),
                    )
                finally:
                    await project.probe_client.close()
    except Exception as exc:
        receipt.update(status="blocked", error=safe_error(exc))
        if isinstance(exc, ApprovalError):
            receipt["error"]["guardReason"] = str(exc)
    receipt["completedAt"] = now()
    flush()
    print(json.dumps({"name": name, "version": version, "status": receipt["status"],
                      "responseId": receipt.get("responseId"), "error": receipt.get("error"),
                      "httpResults": [{k: r.get(k) for k in ("method", "httpStatus", "safeError")}
                                      for r in wire]}))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", choices=list(NAMES), required=True)
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(run(args.name)))
    except ApprovalError as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        raise SystemExit(2)
