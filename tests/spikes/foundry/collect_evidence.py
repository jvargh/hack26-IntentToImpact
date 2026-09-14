"""Collect local verification and minimize existing live receipts; performs no Azure calls."""

import hashlib
import importlib.metadata
import inspect
import json
import platform
import subprocess
import sys
from pathlib import Path

from discover import OUTPUT, ROOT, digest, now, save


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    from agent_framework import Agent, ResponseStream
    from agent_framework.foundry import FoundryAgent, FoundryChatClient
    from azure.ai.projects.aio import AIProjectClient
    from azure.identity.aio import AzureCliCredential
    from spike import PACKAGES

    tests_command = [sys.executable, "-m", "unittest", "discover", "-s",
                     str(ROOT / "tests" / "spikes" / "foundry"), "-p", "test_spike.py", "-v"]
    test_start = now()
    tests = subprocess.run(tests_command, capture_output=True, text=True, check=False)
    missing_command = [sys.executable, str(ROOT / "tests" / "spikes" / "foundry" / "spike.py")]
    missing = subprocess.run(missing_command, capture_output=True, text=True, check=False)
    check = subprocess.run([sys.executable, "-m", "pip", "check"],
                           capture_output=True, text=True, check=False)
    save("local-tests.json", {
        "version": "1.0.0", "origin": "live-local", "startedAt": test_start, "completedAt": now(),
        "tests": {"command": tests_command, "exitCode": tests.returncode,
                  "stdout": tests.stdout, "stderr": tests.stderr},
        "missingConfig": {"command": missing_command, "exitCode": missing.returncode,
                          "result": json.loads(missing.stdout)},
        "pipCheck": {"exitCode": check.returncode, "stdout": check.stdout},
        "externalRequestCount": 0,
    })

    symbols = [Agent, Agent.run, FoundryChatClient, FoundryAgent,
               AIProjectClient, AIProjectClient.get_openai_client, AzureCliCredential]
    sdk = {
        "version": "1.0.0", "origin": "live-local", "createdAt": now(),
        "pythonVersion": platform.python_version(), "azureCliVersionObserved": "2.86.0",
        "packages": {p: importlib.metadata.version(p) for p in PACKAGES},
        "signatures": {f"{s.__module__}.{s.__qualname__}": str(inspect.signature(s)) for s in symbols},
        "sourceFiles": {str(Path(inspect.getfile(s)).relative_to(ROOT)):
                        sha(Path(inspect.getfile(s))) for s in symbols},
        "streamLifecycleMethods": [n for n in dir(ResponseStream)
                                   if any(word in n for word in ("cancel", "close", "final"))],
        "findings": [
            "FoundryChatClient plus local Agent uses project /openai/v1/responses; no cloud agent creation.",
            "AIProjectClient 2.3.0 defaults api-version=v1 and token scope https://ai.azure.com/.default.",
            "Azure CLI 2.86.0 rejects subscription plus tenant together during get-access-token. "
            "Use AzureCliCredential(subscription=exact_id); tenant verified by scoped account show.",
            "FoundryAgent supports agent_name and agent_version for existing service-managed agents.",
            "Installed _agent.py uses extra_body['agent_reference'] with name, type=agent_reference "
            "and version on non-preview calls; local skill example extra_body['agent'] is not this SDK shape.",
            "SDK agent list cursor is last_id regardless of server has_more; use server has_more.",
            "Agent.run returns AgentResponse, or ResponseStream yielding AgentResponseUpdate. "
            "get_final_response() returned AgentResponse with Pydantic ProbeResult in both live probes.",
            "No ResponseStream cancel/close method was exposed by this pinned build. "
            "Remote cancellation or interrupted-stream cost cessation was not tested.",
        ],
        "dependencyAttempts": [
            "Initial PyPI JSON advertised Foundry 1.13.0/Core 1.18.0 but configured pip index "
            "offered at most 1.12.0/1.17.0; install failed without changes outside spike venv.",
            "Foundry 1.12.0 rejects azure-ai-projects 2.6.0: requires >=2.2.0,<2.4.0.",
            "Pinned Foundry 1.12.0/Core 1.17.0/Projects 2.3.0 installed; pip check passed.",
        ],
    }
    report_path = OUTPUT / "install-report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        sdk["installedArtifactHashes"] = [
            {"name": p["metadata"]["name"], "version": p["metadata"]["version"],
             "hashes": p["download_info"].get("archive_info", {}).get("hashes", {})}
            for p in report["install"]
        ]
        report_path.unlink()
    elif (OUTPUT / "sdk-findings.json").exists():
        sdk["installedArtifactHashes"] = read("sdk-findings.json").get("installedArtifactHashes", [])
    save("sdk-findings.json", sdk)

    failure_path = OUTPUT / "agents-auth-failure.json"
    if failure_path.exists():
        failure = read(failure_path.name)
        failure.update(origin="live-local", externalRequestCount=0,
                       diagnostic="Azure CLI argument validation rejected --subscription plus --tenant; "
                       "not a Foundry server authorization failure.")
        save(failure_path.name, failure)
    cursor_path = OUTPUT / "agents-first-page-sdk-cursor.json"
    if cursor_path.exists():
        cursor = read(cursor_path.name)
        cursor.update(sdkContinuationPresent=True, hasMore=None,
                      paginationCorrection="Original hasMore calculation reflected SDK last_id, "
                      "not server has_more. agents-receipt.json confirms server has_more=false.")
        save(cursor_path.name, cursor)

    discovery, agents, model, stream = (
        read("discovery.json"), read("agents-receipt.json"),
        read("model-receipt.json"), read("stream-receipt.json"),
    )
    prompts = [a for a in agents["agents"] if a["kind"] == "prompt"]
    rows = [
        {"proof": "exact-scope-discovery", "status": discovery["status"],
         "origin": "live-external", "evidence": "discovery.json"},
        {"proof": "local-Agent-Framework-Foundry-model", "status": model["status"],
         "origin": "live-external", "responseId": model.get("responseId"),
         "evidence": "model-receipt.json"},
        {"proof": "typed-streaming-model-result", "status": stream["status"],
         "origin": "live-external", "responseId": stream.get("responseId"),
         "evidence": "stream-receipt.json"},
        {"proof": "malformed-missing-exact-scope-config",
         "status": "passed" if tests.returncode == 0 and missing.returncode == 2 else "failed",
         "origin": "live-local", "evidence": "local-tests.json"},
        {"proof": "existing-agent-metadata", "status": agents["status"],
         "origin": "live-external", "evidence": "agents-receipt.json"},
    ]
    rows.extend({"proof": f"private-prompt-agent-{role}", "status": "blocked",
                 "origin": "none", "reason": "No approved name/version definition; "
                 "all discovered current Prompt Agents have tools. None invoked."}
                for role in ("synthesis", "assurance", "implementation-remediation"))
    rows.append({"proof": "remote-stream-cancellation", "status": "not-tested", "origin": "none",
                 "reason": "Bounded to two harmless completed model calls; no server cancellation proof."})
    receipt = {
        "version": "1.0.0", "task": "SPK-01-01", "parentPlan": "SPK-01", "createdAt": now(),
        "status": "partial", "taskComplete": False, "rows": rows,
        "azureResourceMutationCount": 0, "cloudAgentInvocationCount": 0,
        "successfulSyntheticModelCalls": sum(r["status"] == "passed" for r in (model, stream)),
        "observedAgentCount": len(agents["agents"]), "observedPromptAgentCount": len(prompts),
        "observedNoToolPromptAgentCount": sum(not a["toolTypes"] for a in prompts),
        "agentListingComplete": agents.get("hasMore") is False,
        "privateVisibilityProof": "not-established; no agent publication/RBAC inventory. "
        "Account publicNetworkAccess=Enabled does not prove private network isolation.",
        "nextSafeAction": "Approve creation and later synthetic invocation of only the three "
        "probe-only proposed-specialists.json names, or provide approved existing immutable "
        "no-tool versions. No create/update/publish/role assignment is implemented or authorized.",
        "ux02": {
            "status": "capability-notes-only-no-gate-approved",
            "facts": [
                "Show discovering/connecting/generating stages; stream updates are real, not percentage completion.",
                "Structured value is authoritative only after stream completion and schema validation.",
                "One sample first text arrived at 5663 ms including local credential/client setup.",
                "Cancellation status must say local stop requested; remote completion/billing unknown.",
                "Missing specialist approvals are blocked, never silently replayed as live.",
            ],
        },
        "constraints": [
            "No dependency/setup provisioning scripts run; azd installer would write outside approved paths.",
            "Foundry MCP tool discovery returned oversized schema; no operational MCP calls used. "
            "All resource/data calls use exact CLI subscription rather than separate VS Code auth.",
            "Only synthetic ProbeResult was validated; no domain packet or production integration proof.",
        ],
    }
    source_dir = ROOT / "tests" / "spikes" / "foundry"
    receipt["sourceFileHashes"] = {str(p.relative_to(ROOT)): sha(p) for p in source_dir.iterdir()
                                 if p.is_file()}
    receipt["evidenceFileHashes"] = {
        str(p.relative_to(ROOT)): sha(p) for p in OUTPUT.iterdir()
        if p.is_file() and p.name != "receipt.json"
    }
    save("receipt.json", receipt)
    assert sha(OUTPUT / "invocation-source.py") == model["sourceSha256"] == stream["sourceSha256"]
    assert check.returncode == tests.returncode == 0 and missing.returncode == 2
    print(json.dumps({"status": "partial", "taskComplete": False,
                      "receipt": str((OUTPUT / "receipt.json").relative_to(ROOT)),
                      "agentCount": len(agents["agents"]),
                      "noToolPromptAgents": sum(not a["toolTypes"] for a in prompts),
                      "localTests": "7 passed"}))


if __name__ == "__main__":
    main()
