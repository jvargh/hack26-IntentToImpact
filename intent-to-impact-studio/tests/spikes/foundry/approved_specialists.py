"""Approval-specific SPK-01-01 probe creation and exact-version invocation."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from discover import OUTPUT, PROJECT_ID, ROOT, SUBSCRIPTION, TENANT, cli, digest, now
from spike import ENDPOINT, PACKAGES, safe_error, verify_discovery

RUN = OUTPUT / "approved-specialists-20260912T223042Z"
ROLES = ("synthesis", "assurance", "implementation-remediation")
NAMES = {f"intent-to-impact-{role}": role for role in ROLES}
APPROVAL_TIME = "2026-09-12T18:30:42.636-04:00"
MANIFEST_HASH = "f3938bfef87cd16b31d7512b79e2837d3506812214587050f13f8cb7512d1c63"


class ApprovalError(ValueError):
    pass


def expected_definition(role):
    return {
        "kind": "prompt", "model": "gpt-5.2",
        "instructions": f"Synthetic SPK-01-01 {role} connectivity probe only. "
        f"Return a JSON object with marker SPK-01-01-OK and specialist {role}. "
        "No tools, actions, or customer content.",
        "tools": [],
    }


def validate_definition(name, definition, endpoint=ENDPOINT):
    if endpoint != ENDPOINT:
        raise ApprovalError("Project endpoint is outside the exact approved scope.")
    if name not in NAMES:
        raise ApprovalError("Agent name is not in the three-name approval allowlist.")
    if not isinstance(definition, dict) or definition.get("tools") != []:
        raise ApprovalError("Definition must explicitly contain an empty tools list.")
    if definition != expected_definition(NAMES[name]):
        raise ApprovalError("Definition must exactly match the approved tool-free probe; no connections or overrides.")


def ensure_absent(existing):
    if existing is not None:
        raise ApprovalError("Existing-agent collision: no version creation or update is permitted.")


def validate_readback(name, version, data):
    if str(data.get("version")) != version or data.get("name") != name:
        raise ApprovalError("Created-version readback identity does not match the pinned name/version.")
    actual = data.get("definition", {})
    expected = expected_definition(NAMES[name])
    if any(actual.get(key) != value for key, value in expected.items()):
        raise ApprovalError("Created definition differs from approved probe or has tools.")
    if any(value not in (None, [], {}) for key, value in actual.items() if key not in expected):
        raise ApprovalError("Unexpected nonempty definition properties; possible unapproved connection/tool feature.")


def validate_invocation_body(name, version, body):
    expected_ref = {"name": name, "type": "agent_reference", "version": version}
    if name not in NAMES or not version or body.get("agent_reference") != expected_ref:
        raise ApprovalError("Invocation requires an exact approved, created name/version reference.")
    if body.get("store") is not False:
        raise ApprovalError("Invocation must disable response storage.")
    if any(body.get(key) for key in (
        "agent", "model", "tools", "conversation", "previous_response_id", "agent_session_id",
    )):
        raise ApprovalError("No tool/model override, conversation, session or unrelated agent may be invoked.")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    path = RUN / name
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def validate_manifest():
    path = Path(__file__).with_name("proposed-specialists.json")
    if sha(path) != MANIFEST_HASH:
        raise ApprovalError("Approved proposal file changed; obtain approval before using different definitions.")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["scope"] != ENDPOINT or {d["agent_name"] for d in manifest["definitions"]} != set(NAMES):
        raise ApprovalError("Proposal does not match approved endpoint/names.")
    for item in manifest["definitions"]:
        validate_definition(item["agent_name"], item["definition"])
    return manifest


async def create_initial(project, name, definition, row, flush):
    from azure.core.exceptions import ResourceNotFoundError

    validate_definition(name, definition)
    if row.get("creationAttempted"):
        raise ApprovalError("Creation was already attempted; automatic second version creation is forbidden.")
    try:
        existing = await project.agents.get(name)
    except ResourceNotFoundError as exc:
        if exc.status_code != 404:
            raise
        existing = None
    ensure_absent(existing)
    row.update(absenceVerified=True, absenceVerifiedAt=now())
    flush()
    created = await project.agents.create_version(name, body={"definition": definition})
    data = created.as_dict()
    version = str(data["version"])
    row.update(createdVersion=version, createdId=data.get("id"), createdAt=now(),
               creationResponseSha256=digest(data))
    flush()
    if version != "1":
        raise ApprovalError("Service returned a non-initial version; stop and report possible concurrent collision.")
    readback = await project.agents.get_version(name, version)
    data = readback.as_dict()
    validate_readback(name, version, data)
    row.update(
        definitionReadback={
            "id": data.get("id"), "name": data.get("name"), "version": version,
            "definition": data["definition"], "definitionSha256": digest(data["definition"]),
            "definitionKeys": sorted(data["definition"]),
            "created_at": data.get("created_at"),
        },
        definitionVerified=True, readbackAt=now(),
    )
    flush()
    return version


async def execute():
    import httpx
    from agent_framework.foundry import FoundryAgent
    from azure.ai.projects.aio import AIProjectClient
    from azure.core.pipeline.policies import SansIOHTTPPolicy
    from azure.identity.aio import AzureCliCredential
    from pydantic import ConfigDict, create_model
    from typing import Literal

    logging.disable(logging.CRITICAL)
    manifest = validate_manifest()
    verify_discovery()
    if not (RUN / "prior-task-receipt.json").exists():
        raise ApprovalError("Preserved prior aggregate is required before continuation.")
    if (RUN / "specialist-receipt.json").exists():
        raise ApprovalError("This approval-specific run already started. Do not rerun creation; inspect preserved IDs.")
    old = json.loads((RUN / "prior-task-receipt.json").read_text(encoding="utf-8"))
    for relative, expected in old["evidenceFileHashes"].items():
        if sha(ROOT / relative) != expected:
            raise ApprovalError("Prior evidence changed; stop rather than overwrite or reinterpret it.")
    receipt = {
        "version": "1.0.0", "task": "SPK-01-01", "phase": "approved-specialist-probes",
        "status": "in-progress", "startedAt": now(), "origin": "live-external",
        "approval": {
            "source": "explicit user message", "time": APPROVAL_TIME, "names": list(NAMES),
            "summary": "One initial tool-free probe version per exact name if absent, followed by "
            "synthetic invocation of only those created versions. No existing-agent updates, "
            "roles, publication, connections, model deployments, endpoints or infrastructure changes.",
            "proposalFileSha256": MANIFEST_HASH,
        },
        "projectId": PROJECT_ID, "projectEndpoint": ENDPOINT,
        "subscriptionId": SUBSCRIPTION, "tenantId": TENANT, "apiVersion": "v1",
        "sdkVersions": {p: importlib.metadata.version(p) for p in PACKAGES},
        "sourceFileSha256": sha(Path(__file__)),
        "priorReceiptSha256": sha(RUN / "prior-task-receipt.json"),
        "rows": [], "requests": [], "automaticRetries": 0,
        "limitations": [
            "Probe definitions/results only; not production specialist or domain-schema registration.",
            "No publication operation used; no broad visibility, identity or private-network claim.",
            "Remote stream cancellation and billing cessation remain untested.",
            "Absence is checked immediately before creation; no distributed lock or atomic create-only "
            "name precondition is exposed by this SDK. Service-assigned initial version is checked.",
        ],
    }
    wire = receipt["requests"]

    def flush():
        write("specialist-receipt.json", receipt)

    for item in manifest["definitions"]:
        receipt["rows"].append({
            "name": item["agent_name"], "role": NAMES[item["agent_name"]],
            "definitionSha256": digest(item["definition"]), "status": "pending",
        })
    flush()
    scope = cli(["account", "show", "--query", "{id:id,tenantId:tenantId,state:state}"])
    receipt["scopeCheck"] = scope
    if scope.get("data") != {"id": SUBSCRIPTION, "tenantId": TENANT, "state": "Enabled"}:
        receipt.update(status="blocked", completedAt=now(), error="CLI subscription/tenant scope mismatch.")
        flush()
        return 1
    flush()

    class ApprovedPolicy(SansIOHTTPPolicy):
        def on_request(self, request):
            req = request.http_request
            url = urlsplit(req.url)
            prefix = ENDPOINT + "/agents/"
            if not req.url.startswith(prefix) or url.query != "api-version=v1":
                raise ApprovalError("Request escaped exact agent endpoint/API version.")
            path = (url.scheme + "://" + url.netloc + url.path)[len(prefix):].split("/")
            name = path[0]
            if name not in NAMES:
                raise ApprovalError("Unapproved agent request blocked before network.")
            row = next(r for r in receipt["rows"] if r["name"] == name)
            if req.method == "GET":
                if path != [name] and path != [name, "versions", row.get("createdVersion")]:
                    raise ApprovalError("Only name existence and created-version readback are permitted.")
            elif req.method == "POST" and path == [name, "versions"]:
                body = req.body if isinstance(req.body, dict) else json.loads(req.body)
                if set(body) != {"definition"}:
                    raise ApprovalError("Only the approved definition may be sent in a creation request.")
                validate_definition(name, body["definition"])
                if not row.get("absenceVerified") or row.get("creationAttempted"):
                    raise ApprovalError("Absent-name proof and unused one-shot creation permission required.")
                row["creationAttempted"] = True
                row["creationRequestSha256"] = digest(body)
            else:
                raise ApprovalError("Update/delete/publish/session or other unapproved operation blocked.")
            wire.append({"method": req.method, "url": req.url, "startedAt": now(),
                         "name": name, "origin": "live-external"})
            flush()

        def on_response(self, request, response):
            wire[-1].update(
                httpStatus=response.http_response.status_code, completedAt=now(),
                requestId=response.http_response.headers.get("x-ms-request-id")
                or response.http_response.headers.get("apim-request-id"),
            )
            flush()

    active = {}

    async def guard_inference(request):
        if request.method != "POST" or str(request.url) != ENDPOINT + "/openai/v1/responses":
            raise ApprovalError("Only the project Responses endpoint may receive synthetic inference.")
        name, version = active["name"], active["version"]
        row = next(r for r in receipt["rows"] if r["name"] == name)
        body = json.loads(request.content)
        validate_invocation_body(name, version, body)
        if not row.get("definitionVerified") or row.get("invocationAttempted"):
            raise ApprovalError("Only one invocation of a verified created version is permitted.")
        row["invocationAttempted"] = True
        wire.append({
            "method": "POST", "url": str(request.url), "name": name, "version": version,
            "startedAt": now(), "origin": "live-external", "requestBodySha256": digest(body),
            "agentReference": body["agent_reference"], "store": False, "toolCount": 0,
        })
        flush()

    async def record_inference(response):
        wire[-1].update(
            httpStatus=response.status_code, completedAt=now(),
            requestId=response.headers.get("x-request-id")
            or response.headers.get("x-ms-request-id") or response.headers.get("apim-request-id"),
        )
        flush()

    class BoundedProject(AIProjectClient):
        def get_openai_client(self, **kwargs):
            self.probe_client = super().get_openai_client(
                **kwargs, max_retries=0, timeout=45,
                http_client=httpx.AsyncClient(
                    timeout=45, follow_redirects=False, trust_env=False,
                    event_hooks={"request": [guard_inference], "response": [record_inference]},
                ),
            )
            return self.probe_client

    credential = AzureCliCredential(subscription=SUBSCRIPTION, process_timeout=20)
    async with credential:
        async with BoundedProject(
            endpoint=ENDPOINT, credential=credential, retry_total=0, redirect_max=0,
            per_call_policies=[ApprovedPolicy()],
        ) as project:
            for row in receipt["rows"]:
                name, role = row["name"], row["role"]
                row.update(status="in-progress", startedAt=now())
                flush()
                try:
                    async with asyncio.timeout(90):
                        version = await create_initial(
                            project, name, expected_definition(role), row, flush,
                        )
                        active.update(name=name, version=version)
                        result_type = create_model(
                            "SpecialistProbeResult", __config__=ConfigDict(extra="forbid"),
                            marker=(Literal["SPK-01-01-OK"], ...),
                            specialist=(Literal[role], ...),
                        )
                        prompt = f"Return only JSON: marker SPK-01-01-OK, specialist {role}."
                        row["syntheticInputSha256"] = hashlib.sha256(prompt.encode()).hexdigest()
                        agent = FoundryAgent(
                            project_client=project, agent_name=name, agent_version=version,
                            allow_preview=False, name=f"SPK-01-01-{role}",
                        )
                        start = time.monotonic()
                        try:
                            result = await agent.run(
                                prompt, options={"store": False, "max_tokens": 160,
                                                 "response_format": result_type},
                            )
                            parsed = result_type.model_validate_json(result.text)
                            if not isinstance(result.value, result_type):
                                raise ApprovalError("Agent Framework did not return the expected typed value.")
                            row.update(
                                status="passed", responseId=result.response_id,
                                responseType=type(result).__name__,
                                typedValueType=type(result.value).__name__,
                                result=parsed.model_dump(),
                                responseTextSha256=hashlib.sha256(result.text.encode()).hexdigest(),
                                resultSha256=digest(parsed.model_dump()),
                                finishReason=str(result.finish_reason),
                                usage=dict(result.usage_details or {}),
                                inferenceDurationMs=round((time.monotonic() - start) * 1000),
                            )
                        finally:
                            await project.probe_client.close()
                except Exception as exc:
                    row.update(
                        status="blocked", error=safe_error(exc),
                        action="No retry, role change, update or deletion. Inspect recorded created ID/version.",
                    )
                    if isinstance(exc, ApprovalError):
                        row["error"]["guardReason"] = str(exc)
                row["completedAt"] = now()
                flush()
    receipt.update(
        status="passed" if all(r["status"] == "passed" for r in receipt["rows"]) else "partial",
        completedAt=now(),
        createdVersions=sum("createdVersion" in r for r in receipt["rows"]),
        creationAttempts=sum(bool(r.get("creationAttempted")) for r in receipt["rows"]),
        invocationAttempts=sum(bool(r.get("invocationAttempted")) for r in receipt["rows"]),
        successfulTypedInvocations=sum(r["status"] == "passed" for r in receipt["rows"]),
        existingAgentUpdates=0, unapprovedMutationCount=0,
    )
    flush()
    print(json.dumps({
        "status": receipt["status"], "receipt": str(RUN.relative_to(ROOT) / "specialist-receipt.json"),
        "agents": [{"name": r["name"], "version": r.get("createdVersion"),
                    "status": r["status"], "responseId": r.get("responseId"),
                    "error": r.get("error")} for r in receipt["rows"]],
    }))
    return 0 if receipt["status"] == "passed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-approved", action="store_true")
    args = parser.parse_args()
    if not args.execute_approved:
        print("Refused: explicit --execute-approved is required; no Azure requests made.")
        return 2
    try:
        return asyncio.run(execute())
    except ApprovalError as exc:
        print(json.dumps({"status": "rejected", "error": str(exc), "automaticRetry": False}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
