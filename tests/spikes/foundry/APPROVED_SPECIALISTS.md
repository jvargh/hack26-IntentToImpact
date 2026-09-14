# SPK-01-01 approved probe continuation

**Completed within the approved probe scope.** Three initially absent names were
created as version `1`, read back as `kind=prompt`, `model=gpt-5.2`, `tools=[]`,
with no connection fields, then successfully invoked through local Agent Framework.
No existing agents, roles, endpoints, connections or model deployments were modified.
No publication or deletion operation was performed.

This document supersedes the **specialist blocker only** in the original README.
It does not replace its preserved actual model/stream proof or imply production readiness.

## Exact created versions and real responses

Project:
`https://jv-eastus2-proj-resource.services.ai.azure.com/api/projects/jv-eastus2-proj`

Subscription: `463a82d4-1896-4332-aeeb-618ee5a5aa93`;
tenant: `5bb5fa45-2dcc-4310-bbc5-883021e9d84b`; resource group: `az-foundry-rg`.

| Agent ID (name:version) | Successful response ID |
| --- | --- |
| `intent-to-impact-synthesis:1` | `resp_06c347464a6e1892016aa5d39fbac48194a94be593f5036a04` |
| `intent-to-impact-assurance:1` | `resp_09082b3499512570016aa5d3b83e4081979fbba0487a120bab` |
| `intent-to-impact-implementation-remediation:1` | `resp_0a632acd560eab0a016aa5d3b82ab08190bd799af4273ef7f1` |

Each successful result is strict JSON with `marker="SPK-01-01-OK"` and the exact
specialist role. **Typing is strict local Pydantic validation of the live Agent
Framework response**, not server-enforced JSON schema or a production-domain packet.

## Evidence and preservation

Root task receipt: `.intent-to-impact\spikes\SPK-01-01\receipt.json`.

New evidence is confined to:
`.intent-to-impact\spikes\SPK-01-01\approved-specialists-20260912T223042Z\`.

- `prior-task-receipt.json`, `prior-source\`: original aggregate and all eight original
  source files preserved before continuation.
- Original root `model-receipt.json`, `stream-receipt.json`, `invocation-source.py` and
  other original evidence remain unchanged and hash-verified.
- `specialist-receipt.json`: exact approval summary, subscription/tenant check, three
  absence GETs returning 404, three creation POSTs returning 200, exact version
  readbacks, definition hashes, and **three failed first invocations (HTTP 400)**.
- `intent-to-impact-*-native-invocation.json`: three successful HTTP 200 invocations;
  exact agent/version references, request IDs/times/hashes, response IDs, strict typed
  results, and matching definition readback hashes.
- `creation-source.py`, `native-invocation-source.py`: exact executed source snapshots.
- `local-tests.json`: 17 local tests, no-approval/run-reentry rejection, and pip check.
- `continuation-receipt.json`: verified proof matrix, limitations and evidence hashes.

## Supported pinned SDK behavior

Existing environment and dependency pins were retained; no installation was needed:
Foundry Framework **1.12.0**, Core **1.17.0**, Framework OpenAI **1.14.2**,
Azure AI Projects **2.3.0**, Azure Identity **1.25.3**, OpenAI **3.8.0**,
Pydantic **2.13.5**, HTTPX **0.28.1**.

Creation used `AIProjectClient.agents.create_version` after exact-name GET returned
404; service-assigned version `1` was read back and pinned.
Invocation used:

```python
agent = FoundryAgent(
    project_client=project,
    agent_name=exact_approved_name,
    agent_version="1",
    allow_preview=False,
)
result = await agent.run(synthetic_input, options={"store": False})
# Validate result.text locally against strict marker + specialist literals.
```

Successful wire shape: `POST <project>/openai/v1/responses`, with
`agent_reference={"name":exact_name,"type":"agent_reference","version":"1"}`.
The SDK resolves the model from the agent version; no model/tool override is supplied.
Explicit CLI subscription credential is used after tenant verification.

The first invocation shape included `response_format=<Pydantic model>` and
`max_tokens=160`; all three returned HTTP 400. Removing both produced the three
successful native responses. **The specific individually rejected option was not
isolated**—the evidence supports the working shape, not a broader compatibility claim.
The failed receipts remain intact. No additional versions or cloud infrastructure were
created to work around this SDK/service behavior.

## Commands and safety

From workspace root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$python = '.\.intent-to-impact\spikes\SPK-01-01\.venv\Scripts\python.exe'
& $python -m unittest discover -s .\tests\spikes\foundry -p test_*.py -v
& $python .\tests\spikes\foundry\collect_specialist_evidence.py
```

The collector verifies artifacts and runs local guards only: **no Azure calls**.
Do not rerun the historical `collect_evidence.py`, which describes the earlier partial
phase. The creation command was:

```powershell
& $python .\tests\spikes\foundry\approved_specialists.py --execute-approved
```

It now intentionally refuses before Azure access because this approval-specific run
already exists. A valid name that already exists is also rejected before creation;
unapproved names, changed instructions, tools, connections or endpoints are rejected.
The successful invocation-only command, run once per exact approved name, was:

```powershell
& $python .\tests\spikes\foundry\invoke_created_specialists.py --name intent-to-impact-synthesis
```

Each invocation attempt file is one-shot. Do not delete receipts to force replay or
reuse the creation permission. Both runners have no automatic retries. No rollback
deletion is authorized.

## Limits retained

- Initial absence checks are not a distributed lock; the SDK exposes no atomic
  create-only-name precondition. Every observed created version was initial `1`.
- Assets were read through the authenticated project and no publish operation was
  called. Wider visibility/private-network isolation is **not** proven.
- Remote cancellation and billing cessation remain **not tested**; no cancellation
  claim or UX gate approval is made.
- Probe-only instructions and typed marker results are not production specialist
  registration, domain-schema proof, or authorization for subsequent AGT work.
