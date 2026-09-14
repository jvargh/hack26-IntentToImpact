"""Bounded local Agent Framework proof; never creates or invokes cloud agents."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import logging
import re
import time
from pathlib import Path
from typing import Literal

from discover import ACCOUNT_ID, OUTPUT, PROJECT_ID, ROOT, SUBSCRIPTION, TENANT, digest, now, save

ENDPOINT = "https://jv-eastus2-proj-resource.services.ai.azure.com/api/projects/jv-eastus2-proj"
EXPECTED = {
    "subscriptionId": SUBSCRIPTION, "tenantId": TENANT,
    "resourceGroup": "az-foundry-rg", "projectEndpoint": ENDPOINT,
    "modelDeployment": "gpt-5.2",
}
PROBE = "Return exactly the JSON object with marker equal to SPK-01-01-OK."
INSTRUCTIONS = "This is a synthetic connectivity check. Return only the requested marker."
PACKAGES = (
    "agent-framework-foundry", "agent-framework-core", "agent-framework-openai",
    "azure-ai-projects", "azure-identity", "openai", "pydantic", "httpx",
)


class ConfigError(ValueError):
    pass


def validate_config(path):
    if not path:
        raise ConfigError("Missing --config. Use tests\\spikes\\foundry\\approved-config.json.")
    try:
        config = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ConfigError("Config must be a readable JSON object; no network request was made.") from None
    if not isinstance(config, dict) or set(config) != set(EXPECTED):
        raise ConfigError("Config requires only subscriptionId, tenantId, resourceGroup, "
                          "projectEndpoint and modelDeployment; credentials are not accepted.")
    if config != EXPECTED:
        raise ConfigError("Config is outside the approved exact scope. Use approved-config.json; "
                          "a different subscription, endpoint or model requires approval.")
    return config


def verify_discovery():
    try:
        discovery = json.loads((OUTPUT / "discovery.json").read_text(encoding="utf-8"))
        rows = discovery["rows"]
        assert discovery["status"] == "passed"
        assert rows["scope"]["data"] == {
            "id": SUBSCRIPTION, "tenantId": TENANT, "state": "Enabled"}
        assert rows["project"]["data"]["id"] == PROJECT_ID
        assert ENDPOINT in rows["project"]["data"]["endpoints"].values()
        assert rows["account"]["data"]["id"] == ACCOUNT_ID
        assert any(d["name"] == EXPECTED["modelDeployment"] and d["state"] == "Succeeded"
                   and d["id"] == ACCOUNT_ID + "/deployments/" + EXPECTED["modelDeployment"]
                   for d in rows["deployments"]["data"])
        assert all(row["dataSha256"] == digest(row["data"]) for row in rows.values())
    except (OSError, ValueError, KeyError, AssertionError, TypeError):
        raise ConfigError("A successful exact-scope discovery.json is required; run discover.py first.") from None
    return discovery


def safe_error(exc):
    status = getattr(exc, "status_code", None)
    return {
        "type": type(exc).__name__, "httpStatus": status,
        "requestId": getattr(exc, "request_id", None),
        "aadErrorCodes": sorted(set(re.findall(r"AADSTS\d+", str(exc)))),
        "action": (
            "Check approved-project data-plane access/network; no role or resource changes were attempted."
            if status in (401, 403) else
            "Inspect the pinned local SDK/configuration; no automatic retry or fallback was attempted."
        ),
    }


async def execute(operation, config, discovery):
    # Imports follow strict config validation so invalid config never starts credentials or clients.
    import httpx
    from agent_framework import Agent
    from agent_framework.foundry import FoundryChatClient
    from azure.ai.projects.aio import AIProjectClient
    from azure.core.pipeline.policies import SansIOHTTPPolicy
    from azure.identity.aio import AzureCliCredential
    from pydantic import BaseModel

    logging.disable(logging.CRITICAL)
    wire = []
    started = now()
    start_clock = time.monotonic()
    versions = {name: importlib.metadata.version(name) for name in PACKAGES}
    common = {
        "version": "1.0.0", "task": "SPK-01-01", "origin": "live-external",
        "operation": operation, "startedAt": started, "configSha256": digest(config),
        "subscriptionId": SUBSCRIPTION, "tenantId": TENANT, "resourceGroup": "az-foundry-rg",
        "projectId": PROJECT_ID, "projectEndpoint": ENDPOINT, "versions": versions,
        "sourceSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "discoverySha256": digest(discovery),
        "azureResourceMutationCount": 0, "cloudAgentInvocationCount": 0,
        "automaticRetries": 0,
    }

    class ReadOnlyPolicy(SansIOHTTPPolicy):
        def on_request(self, request):
            req = request.http_request
            if req.method != "GET" or not req.url.startswith(ENDPOINT + "/agents?"):
                raise ConfigError("Only exact-project agent-list GET is permitted.")
            wire.append({"method": req.method, "url": req.url, "startedAt": now()})

        def on_response(self, request, response):
            body = response.http_response.json()
            wire[-1].update(httpStatus=response.http_response.status_code,
                            requestId=response.http_response.headers.get("x-ms-request-id")
                            or response.http_response.headers.get("apim-request-id"),
                            hasMore=body.get("has_more"),
                            itemCount=len(body.get("data", [])),
                            completedAt=now())

    async def guard_request(request):
        if request.method != "POST" or str(request.url) != ENDPOINT + "/openai/v1/responses":
            raise ConfigError("Only the approved project's direct Responses inference is permitted.")
        body = json.loads(request.content)
        if (body.get("model") != config["modelDeployment"] or body.get("store") is not False
                or body.get("tools") or body.get("agent") or body.get("agent_reference")
                or body.get("conversation")
                or body.get("previous_response_id")):
            raise ConfigError("Only a stateless, no-tool, non-agent synthetic model probe is permitted.")
        wire.append({"method": "POST", "url": str(request.url), "startedAt": now(),
                     "requestBodySha256": digest(body), "store": False,
                     "toolCount": 0, "agentReference": False})

    async def record_response(response):
        wire[-1].update(httpStatus=response.status_code, completedAt=now(),
                        requestId=response.headers.get("x-request-id")
                        or response.headers.get("x-ms-request-id")
                        or response.headers.get("apim-request-id"))

    class BoundedProjectClient(AIProjectClient):
        def get_openai_client(self, **kwargs):
            self.spike_openai_client = super().get_openai_client(
                **kwargs, max_retries=0, timeout=45,
                http_client=httpx.AsyncClient(
                    timeout=45, follow_redirects=False, trust_env=False,
                    event_hooks={"request": [guard_request], "response": [record_response]},
                ),
            )
            return self.spike_openai_client

    class ProbeResult(BaseModel):
        marker: Literal["SPK-01-01-OK"]

    # CLI 2.86 rejects --subscription plus --tenant; tenant was verified by the scoped account read.
    credential = AzureCliCredential(subscription=SUBSCRIPTION, process_timeout=20)
    try:
        async with credential:
            if operation == "agents":
                async with AIProjectClient(
                    endpoint=ENDPOINT, credential=credential,
                    retry_total=0, per_call_policies=[ReadOnlyPolicy()],
                ) as project:
                    # One page only; no conversations, definitions, instructions or customer messages retained.
                    pages = project.agents.list(limit=50).by_page()
                    page = await anext(pages)
                    agents = []
                    async for item in page:
                        data = item.as_dict()
                        latest = data.get("versions", {}).get("latest", {})
                        definition = latest.get("definition", {})
                        agents.append({
                            "id": data.get("id"), "name": data.get("name"),
                            "version": latest.get("version"), "kind": definition.get("kind"),
                            "model": definition.get("model"),
                            "toolTypes": [tool.get("type") for tool in definition.get("tools", [])],
                            "definitionSha256": digest(definition) if definition else None,
                        })
                    common.update(status="passed", agents=agents, agentsSha256=digest(agents),
                                  hasMore=wire[-1].get("hasMore"),
                                  sdkContinuationPresent=bool(pages.continuation_token),
                                  apiVersion=project._config.api_version,
                                  specialistProof="blocked",
                                  specialistBlocker="No approved specialist name/version bindings. "
                                  "Existing agents were listed only; none invoked.")
            else:
                async with BoundedProjectClient(
                    endpoint=ENDPOINT, credential=credential, retry_total=0,
                ) as project:
                    client = FoundryChatClient(project_client=project, model=config["modelDeployment"])
                    agent = Agent(client=client, name="SPK-01-01-local-probe", instructions=INSTRUCTIONS)
                    options = {"store": False, "max_tokens": 128, "response_format": ProbeResult}
                    try:
                        if operation == "stream":
                            stream = agent.run(PROBE, stream=True, options=options)
                            updates = []
                            async for update in stream:
                                updates.append({
                                    "type": type(update).__name__, "responseId": update.response_id,
                                    "elapsedMs": round((time.monotonic() - start_clock) * 1000),
                                    "textCharacters": len(update.text or ""),
                                })
                            result = await stream.get_final_response()
                            common["updates"] = updates
                        else:
                            result = await agent.run(PROBE, options=options)
                        parsed = ProbeResult.model_validate_json(result.text)
                        deployment = next(d for d in discovery["rows"]["deployments"]["data"]
                                          if d["name"] == config["modelDeployment"])
                        common.update(
                            status="passed", modelDeployment=deployment,
                            responseId=result.response_id, responseType=type(result).__name__,
                            responseTextSha256=hashlib.sha256(result.text.encode()).hexdigest(),
                            result=parsed.model_dump(), typedValueType=type(result.value).__name__,
                            finishReason=str(result.finish_reason),
                            usage=dict(result.usage_details or {}),
                            syntheticInputSha256=hashlib.sha256(PROBE.encode()).hexdigest(),
                            apiVersion="v1", azureResourceMutationCount=0,
                        )
                    finally:
                        await project.spike_openai_client.close()
    except Exception as exc:
        common.update(status="blocked", error=safe_error(exc))
    common.update(completedAt=now(), durationMs=round((time.monotonic() - start_clock) * 1000),
                  requests=wire)
    path = save(f"{operation}-receipt.json", common)
    print(json.dumps({"status": common["status"], "path": path,
                      "responseId": common.get("responseId"), "error": common.get("error")}))
    return 0 if common["status"] == "passed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--operation", choices=["agents", "model", "stream"], default="model")
    args = parser.parse_args()
    try:
        config = validate_config(args.config)
        discovery = verify_discovery()
    except ConfigError as exc:
        print(json.dumps({"status": "rejected", "origin": "live-local",
                          "externalRequestCount": 0, "error": str(exc)}))
        return 2
    try:
        return asyncio.run(asyncio.wait_for(execute(args.operation, config, discovery), timeout=90))
    except TimeoutError:
        path = save(f"{args.operation}-receipt.json", {
            "version": "1.0.0", "task": "SPK-01-01", "status": "blocked",
            "origin": "live-local", "completedAt": now(), "operation": args.operation,
            "error": "Local 90-second deadline exceeded. Remote completion is unknown; do not auto-retry.",
            "azureResourceMutationCount": 0,
        })
        print(json.dumps({"status": "blocked", "path": path, "error": "Local deadline exceeded."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
