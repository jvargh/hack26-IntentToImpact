# INT-01-01 — minimum loopback API 1.0.0

**The bounded create/read/context-ack/error seam is implemented using the real
integration-owned policy entries:**

| Capability | Required existing-policy profile | Activity |
| --- | --- | --- |
| `create-case` | `human` | `product-workflow` |
| `acknowledge-run-context` | `human` | `product-workflow` |

The API does **not** edit the registry or repurpose `read-case` /
`confirm-requirements` as write permissions. Positive create/ack tests run
unconditionally against the real registry and fail if these entries disappear.
Negative tests explicitly inject missing, malformed and unavailable registry reads
for each capability, require schema-valid E07 **503** errors and unchanged stored
bytes. No tests are intentionally skipped. See the evidence receipt for actual results.

**V2 is historical under LOCAL-09.** This seam uses the unchanged V2 synthetic
scenario to prove local API behavior only. It does not represent the current
`SecuredByPerimeter`/Enforced NSP design, NSP association evidence, V3 contracts,
or any live-external proof. No UI or human UX gate is approved.

## Endpoints

| Route | Input / output |
| --- | --- |
| `POST /session` | Exact Origin plus operator bootstrap token header; creates a one-hour in-memory demo session and CSRF token |
| `POST /cases` | `CreateRequest` in `transport.schema.json`; persists through CaseStore and returns canonical **E04 `case-created`**, 201 new / 200 idempotent replay |
| `GET /cases/{id}/experience` | Computes and validates joined **P01/P05/P06** from actual stored D01/D22 and the accepted scenario |
| `POST /cases/{id}/actions/{actionId}` | `ContextAcknowledgement`; records canonical **E04 `run-context-acknowledged`** only |
| `GET /cases/{id}/artifacts/{artifactId}?checksum=sha256:...` | Only exact ID/checksum references reachable directly from that case; JSON attachment, never a file path |

All errors, including invalid routes/IDs, transport failures, storage corruption and
schema failures, use existing **E07**. Unknown pre-context IDs are not fabricated.
No full OpenAPI/documentation UI, HTTP/SSE worker orchestration, provider endpoints
or production UI is added.

The local transport schemas reuse canonical JSON Schema references rather than
redeclaring domain models or generated types. Responses are runtime-validated with
`tools.contracts.validate`; P01 is additionally checked with
`validate_reference_integrity`. The projection does not replay fixture overview
snapshots. Unsupported later producer sections fail explicitly rather than being
silently discarded into an empty/unknown response.

## Unknown-risk truth

The unchanged historical V2 scenario supplies **input intent and declared relationships**.
Actual local case revision/checksum/work come from CaseStore.

- Runtime binding/snapshot are null; evidence, findings and evaluations are absent.
- A `historical-scenario` blocker explicitly labels the response as V2, not LOCAL-09
  NSP/V3 or current Azure proof.
- Coverage remains unassessed, with **null counts**, all eight promises unconfirmed
  and runtime status unknown. RPO is not automatically filled from its scripted input.
- P06 is produced by the shared `reporting.continuity.graph.build_graph`, focused
  on CP-01 with no documents, selected evaluation or external references. The API
  does not maintain its own topology rules. The shared graph has explicit missing
  D14 binding and D17 evaluation gaps, graph/list parity, and no actions/evidence.
  Its scenario links describe intended mappings, not implementation/runtime proof.
  P01 coverage still includes all eight unconfirmed promises; P05 has no D15 snapshot.
- Context acknowledgement leaves lifecycle `Draft`, confirms no promises, creates
  no D07 approval and cannot claim verified architecture or runtime.
- The response exposes fixed demo-human / local-demo disclosure in headers and a
  projection blocker. `scenarioOrigin=fixture` remains visible even when the server
  uses `runMode=live` for genuine **local** API execution. No live-external proof is implied.

## Run and test

Dependencies are isolated; no root manifest or shared contracts environment changes:

```powershell
$root = Join-Path (Get-Location) '.intent-to-impact\spikes\INT-01-01'
New-Item -ItemType Directory -Force "$root\package-work" | Out-Null
$env:TEMP = "$root\package-work"; $env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = "$root\pip-cache"
python -m venv "$root\.venv"
$python = "$root\.venv\Scripts\python.exe"
& $python -m pip install -r .\apps\control-plane\api\requirements.txt
& $python -B -m unittest discover -s .\tests\api -p test_api.py -v
& $python -B .\tests\api\record_evidence.py
```

Pins: FastAPI 0.141.1, Starlette 1.6.0, Uvicorn 0.52.4, HTTPX 0.28.1,
Pydantic 2.13.5, jsonschema **with format extras** 4.26.0.
The installed full version set is retained under the task evidence root.
Starlette currently emits a deprecation warning for its supported HTTPX TestClient;
this run did not silently replace the client or ignore failing tests.

Foreground start, using a fresh process-local token without printing it:

```powershell
$env:INTENT_API_ACCESS_TOKEN = [Convert]::ToHexString(
    [Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
& $python -B .\apps\control-plane\api\serve.py --port 8765
```

The trusted local client needs the **same token**, supplied securely in
`X-Local-Access-Token`, to `POST /session` with
`Origin: http://127.0.0.1:8765`. Retain its HttpOnly `iti_session` cookie and send the
returned `csrfToken` as `X-CSRF-Token` on subsequent POSTs. Never put either token
in URLs, logs, evidence, committed config, or a model prompt.

No persistent server was left running by this task. A test-owned Uvicorn process
is checked over actual loopback HTTP, terminated by its exact Popen PID and waited
for. Other route tests use actual FastAPI TestClient/CaseStore operations.

## Safe configuration / identity limits

- Listener is fixed to IPv4 `127.0.0.1`; there is no `--host` option. Middleware also
  rejects non-loopback peers, nonexact Host, wrong Origin and forwarded/proxy headers.
- Uvicorn proxy-header trust is disabled. No CORS permission is enabled.
- POSTs require the exact Origin and session-bound CSRF header. GETs may omit Origin
  but reject a supplied mismatching one. Duplicate security headers/session cookies
  are rejected.
- Session bootstrap requires a 32–256 character ASCII operator token; no default
  password or automatic login is provided. Session capacity is 32; sessions expire
  after one hour and do not survive restart.
- Cookies are HttpOnly/SameSite=Strict. `Secure` is false because this explicitly
  local HTTP seam has no TLS. This is not production authentication or protection
  against the same OS/Python owner.
- Storage must be beneath `.intent-to-impact\spikes\INT-01-01\`. Case IDs map to
  server-generated run IDs, never client-selected roots or filenames.
- Run mode/purpose, null Azure scope, rootId/configId, actor and channel come from
  server config. Replay creation is unavailable; fixture state is never silently
  promoted to live. Historical V2 retains its public endpoint assumptions, not the
  current LOCAL-09 NSP design; no private resources or Azure access are required.
- Request bodies are limited to 16 KiB. Duplicate JSON keys, nonfinite values and
  extra actor/channel/mode/scope/path fields fail closed.

## Creation and acknowledgement contracts

Create body:

```json
{
  "schemaVersion": "1.0.0",
  "scenario": {
    "scenarioId": "DEMO-CASE-CLAIMS-V2",
    "scenarioVersion": "2.0.0",
    "scenarioHash": "sha256:a140b136272f077c82dcd1d38e8e2c13b0aa7aea192be2a80112ccc744213e9a"
  },
  "idempotencyKey": "operator-selected-request-key"
}
```

Create is an explicit context bootstrap: the engine validates the known scenario
and server D22, obtains a human policy decision against those checksum bindings,
then calls `CaseStore.create_run/create_case/put_artifact/commit`.
Run/case IDs are deterministic hashes of the scoped creation key. The key is not a
filesystem path and is not retained raw. A partially created run returns recovery
required rather than silently fabricating a receipt.

The acknowledgement action ID is issued in current P01 only when its real registry
capability exists and the context is not already acknowledged. POST binds that exact
action, current revision, known scenario and run-manifest checksum:

```json
{
  "schemaVersion": "1.0.0",
  "scenario": {"scenarioId": "DEMO-CASE-CLAIMS-V2", "scenarioVersion": "2.0.0", "scenarioHash": "sha256:<actual scenario hash>"},
  "runManifestChecksum": "sha256:<actual immutable run checksum>",
  "expectedRevision": 1,
  "idempotencyKey": "context-ack-request",
  "acknowledgement": "known-scenario-context-only"
}
```

The checksum comes from `P01.derivedFrom.runManifest` (the trusted stored D22), not a guessed literal.
This seam intentionally has no business requirement/approval model. The local
engine gate means only “validated known run context”, not a canonical D08 business
gate. Case revision/idempotency bindings are enforced before commit. Duplicate
accepted requests return the same E04 receipt; changed input conflicts. No worker
or model capability is executed.

## Evidence and unavailable features

`.intent-to-impact\spikes\INT-01-01\receipt.json` records actual commands, test/skip
counts, real-registry mutation results, response/source/dependency hashes and
completion status. Old partial receipts and samples are retained under `history\`.
Current sample case/read/acknowledgement responses come from actual HTTP routes,
with creation and acknowledgement replays checked against their persisted E04
receipts. Session/cookie/bootstrap/CSRF values are excluded.

Unavailable: business promises/requirements confirmation, D07 approvals, provider
work, Azure observation, NSP/V3 migration or proof, full projections after domain
producers run, UI, SSE, multiuser identity, production auth, and UX approval.
This bounded completion is ready for independent acceptance only; it grants no
subsequent task or cloud-operation authority.
