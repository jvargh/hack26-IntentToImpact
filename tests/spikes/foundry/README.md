# SPK-01-01 — bounded Foundry proof

**Outcome: partial, not complete.** Actual local Agent Framework → Foundry model and typed
streaming calls passed. All three private specialist invocations remain blocked. No
Azure resource/agent/deployment/connection/role was created, updated or deleted.

## Scope and evidence

Approved subscription `463a82d4-1896-4332-aeeb-618ee5a5aa93`, tenant
`5bb5fa45-2dcc-4310-bbc5-883021e9d84b`, resource group `az-foundry-rg`.
Project: `jv-eastus2-proj-resource/projects/jv-eastus2-proj`.
Deployment: `gpt-5.2`, model version `2025-12-11`.

All receipts are under `.intent-to-impact\spikes\SPK-01-01\`:

| Evidence | Actual proof |
| --- | --- |
| `receipt.json` | v1.0.0 per-row outcome, source/evidence hashes, limitations and approval request |
| `discovery.json` | Explicit-subscription CLI account, scoped resources, project and deployments; UTC timestamps and minimized metadata hashes |
| `agents-receipt.json` | Project agents GET, 13 agents including 11 Prompt Agents; server `has_more=false`; every current Prompt Agent has tools |
| `model-receipt.json` | Local `Agent` + `FoundryChatClient`; HTTP 200; `AgentResponse` and validated Pydantic `ProbeResult` |
| `stream-receipt.json` | HTTP 200; 20 real `AgentResponseUpdate` events; final `AgentResponse`/`ProbeResult` |
| `local-tests.json` | Seven unittest tests; missing config CLI exit 2; no external requests; pip check |
| `sdk-findings.json`, `installed-versions.txt` | Actual signatures, SDK source and installed package artifact hashes, Python/dependency versions |
| `invocation-source.py` | Exact source snapshot whose hash appears in the two live model receipts |
| `agents-auth-failure.json` | Local CLI argument rejection, **not** a server access denial |

The successful model response IDs are
`resp_0dc0a4fd4c4480f8016aa5c62104f88196b9629db000a8ae99` and
`resp_0ed2b48f252fbc04016aa5c638c71c8197accc36f59c182834`.
Both completed on 2026-09-12, consumed 103 total tokens each, and produced the
synthetic marker only. Receipts contain exact times, request IDs, request/result hashes
and deployment ARM IDs, not credentials or raw customer content.

## Replay

Run from the workspace root in PowerShell. These commands **do not provision** anything.
Use the existing active CLI login; no `az login` or `az account set` is performed.

```powershell
$root = Join-Path (Get-Location) '.intent-to-impact\spikes\SPK-01-01'
New-Item -ItemType Directory -Force "$root\package-work" | Out-Null
$env:TEMP = "$root\package-work"; $env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = "$root\pip-cache"
$env:PYTHONDONTWRITEBYTECODE = '1'
python -m venv "$root\.venv"
$python = "$root\.venv\Scripts\python.exe"
& $python -m pip install -r .\tests\spikes\foundry\requirements.txt
# For the exact transitive version set from this run, use installed-versions.txt instead.
& $python .\tests\spikes\foundry\discover.py
& $python -m unittest discover -s .\tests\spikes\foundry -p test_spike.py -v
& $python .\tests\spikes\foundry\spike.py # Expected exit 2, no outbound request
& $python .\tests\spikes\foundry\spike.py --config .\tests\spikes\foundry\approved-config.json --operation agents
# Each following command incurs ONE fresh synthetic inference; no auto-retry.
& $python .\tests\spikes\foundry\spike.py --config .\tests\spikes\foundry\approved-config.json --operation model
& $python .\tests\spikes\foundry\spike.py --config .\tests\spikes\foundry\approved-config.json --operation stream
```

Replay overwrites the named receipts; preserve the previous run first if its evidence
must remain available. `collect_evidence.py` summarizes the original complete evidence
set without Azure calls; it expects the preserved invocation source snapshot.

## Pinned SDK/API findings

Python 3.13.15; Azure CLI 2.86.0; `agent-framework-foundry==1.12.0`,
`agent-framework-core==1.17.0`, `agent-framework-openai==1.14.2`,
`azure-ai-projects==2.3.0`, `azure-identity==1.25.3`, `openai==3.8.0`,
`pydantic==2.13.5`, `httpx==0.28.1`.

- Direct inference: `Agent(client=FoundryChatClient(project_client=..., model=...))`
  then `await agent.run(..., options={"store": False, "response_format": ProbeResult, ...})`.
  Streaming uses `agent.run(..., stream=True)` and `await stream.get_final_response()`.
- Endpoint: project `/openai/v1/responses`, token audience `https://ai.azure.com/.default`.
  No server agent or conversation is created by the spike; response storage is disabled.
  The server may still retain normal service/security logs; `store=False` is not a
  claim of zero service retention.
- Use `AzureCliCredential(subscription=approved_id)` after tenant verification.
  Passing both `tenant_id` and `subscription` fails in CLI 2.86.0.
- Existing Prompt Agent API: installed `FoundryAgent(agent_name=..., agent_version=...)`
  generates non-preview `extra_body["agent_reference"]={name,type:"agent_reference",version}`.
  This differs from the older local skill's `extra_body["agent"]` example.
  **Source-inspected only; no Prompt Agent invocation is claimed.**
- SDK pagination exposes `last_id` even when service `has_more=false`; the latest
  agent receipt uses the actual server flag, not SDK cursor presence.
- There is no exposed `ResponseStream.cancel/close` method in this pinned build.
  Remote cancellation, billing cessation, domain schemas and production orchestration
  are not proven. A local 90-second timeout reports unknown remote completion.

## Approval blocker and UX02 limits

The current agent list contains unrelated tool-bearing Prompt Agents, one Hosted Agent
and one workflow. None is an approved no-tool synthesis, assurance or
implementation/remediation specialist. Historical versions were not enumerated.
Private visibility/publication state was not established; account public-network access
is enabled, so this is **not** private-network connectivity proof.

`proposed-specialists.json` contains three **unexecuted, probe-only** definitions:
`intent-to-impact-synthesis`, `intent-to-impact-assurance`,
`intent-to-impact-implementation-remediation`. Next safe action: separately approve
one immutable version creation per exact name in this project and later synthetic
invocation of those versions, or supply approved existing no-tool versions.
Required capability is scoped agent-version creation/read and inference, not a blanket
role assignment. This spike does not establish the caller's creation permission and
does not request or perform any role, deployment or publication changes.

Future UX02 can show real connecting/generating stages and text updates, not completion
percentages. Typed output becomes authoritative only after final schema validation.
One sample first text was 5.663 seconds including credential/client setup; it is not an
SLA. Missing approvals stay blocked. A local stop must not claim server cancellation.
No UX gate is approved.

References: local SPK-01/LOCAL-03 plans and microsoft-foundry skill; current Microsoft
[model-provider guidance](https://learn.microsoft.com/en-us/agent-framework/integrations/by-component/model-providers/microsoft-foundry),
verified against the installed SDK sources rather than assuming documentation versions match.
