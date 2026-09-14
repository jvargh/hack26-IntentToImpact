# FND-03-01 — local policy API 1.0.0

This is a small in-process dispatch guard, **not** authentication, persistence,
scheduling, HTTP, provider execution, approval creation, or a workflow engine.
It imports frozen core validation from `tools.contracts.validate` and emits
schema-valid **E08** authorization context and **E07** errors. Canonical schemas and
generated types are not modified by this package.

The INT-01-01 integration adds `create-case` and `acknowledge-run-context` to the
existing registry format as `human` / `product-workflow` capabilities. Both require
explicit server grants, a human entry, current engine-issued action/checksum/revision
bindings and a passed engine gate. Neither grants cloud access nor substitutes for
`confirm-requirements`, design/delivery approval, or runtime verification. Agents
and system workers cannot use them, even with a human initiator.

## Trust boundary

Only the application composition root/operator adapter creates `Policy`, entry
handles, and engine-fact handles. Never deserialize these handles or build them from
client/model fields. A model-provided E08, actor ID, channel, `humanInitiator`,
`permittedCapabilities`, activity class, or transport is not authority.

1. State owner supplies the trusted stored **D22**.
2. Server configuration independently supplies exact scope/rootId/configId and an
   explicit capability subset; default grants are empty.
3. The adapter receives an opaque entry handle at startup using a **fixed** constructor:
   `human_entry("browser")`, `human_entry("cli")`, `human_entry("harness")`,
   `agent_entry("AGENT-...")`, or `system_entry("worker"/"harness", "SYSTEM-...")`.
4. Each dispatch receives the owning engine's fresh facts and current D22.
5. `authorize(entry, request, current_run=..., facts=...)` returns a `GuardResult`.
   Only `allowed=True` permits dispatch to the owning engine. It never executes or
   records approval, writes files, deploys, seeds, resets, or certifies verification.

Human entries always use `demo-human` / `local-demo`. Automated entries retain
their actual agent/system executor. An optional fixed human initiator does not
change caller class. Issued handles belong to one policy instance and cannot be
replaced by a raw E08 or constructed client object.

**This is not resistance to a hostile Python/OS owner.** Trusted code can access
process internals or call factories; the API/harness must keep those factories off
the client command surface. Browser Origin/Host enforcement belongs in the future
adapter; optional `same_origin` is pure exact loopback comparison, not a running
CSRF/authentication service.

## Minimal consumption

Add `apps\control-plane` to the Python import path while keeping repository root
available for `tools.contracts`; there is no root manifest or new dependency.

```python
from policy import Policy

# Values below come from trusted state/config, not request JSON.
policy = Policy(
    stored_run,
    scope=server_scope,
    root_id=server_root_id,
    config_id=server_config_id,
    enabled_capabilities=["read-case", "inspect-local-change", "apply-local-change"],
)
browser = policy.human_entry(
    "browser", capabilities=["read-case", "inspect-local-change", "apply-local-change"]
)
result = policy.authorize(browser, {"capability": "read-case"}, current_run=stored_run)
if not result.allowed:
    return_error(result.error)  # E07
# The API now asks the owning engine for the projection; policy did not read case data.
```

The local request projection accepts only:

| Key | Meaning |
| --- | --- |
| `capability` | Registered lower-case core ActionId |
| `expectedRevision` | Nonnegative integer; booleans rejected |
| `actionId` | Engine-issued core ActionId for this local guard interface |
| `subjectId` | Core Identifier |
| `boundChecksums` | Core ChecksumMap; must exactly match engine facts for non-read operations |

This projection is **not** a new canonical command/HTTP schema. The future adapter
validates its domain command and passes only these fields to policy. Domain payload,
idempotency handling, issued-action lifecycle, locks and commits remain with their
owning components. Unknown fields fail closed. Caller/run/scope/approval fields are
explicitly forbidden even when their values appear correct.

Every non-read action requires current revision, capability/action/subject/checksum
binding from `policy.engine_facts`. Reads can omit facts; if an expected revision is
provided they also require current engine facts.

## Approval and gate seam

Frozen core contains no D07/D08 approval/gate shape. This limitation was reported
to contracts-owner; **no canonical approval shape is invented**. `ApprovalBinding`
and `engine_facts` are narrowly versioned, noncanonical, trusted engine projections
per the task's permission to consume explicit engine facts:

```python
from policy import ApprovalBinding

binding = ApprovalBinding(
    approval_id=stored_approval_id, actor_id="demo-human",
    capability="apply-local-change", action_id=issued_action_id,
    subject_id=change_id, revision=current_revision,
    checksums=current_bound_checksums, gate_id=applicable_gate_id, current=True,
)
facts = policy.engine_facts(
    current_revision=current_revision, capability="apply-local-change",
    action_id=issued_action_id, subject_id=change_id, checksums=current_bound_checksums,
    gate_id=applicable_gate_id, gate_passed=engine_gate_passed, approval=binding,
)
result = policy.authorize(browser, request_projection, current_run=current_run, facts=facts)
```

The **engine**, not policy, establishes that the referenced approval exists, is
current/not revoked, came from an explicit human action, covers the applicable
gate/subject/checksums, and applies at the current logical revision. Policy compares
all these supplied bindings. Missing/false/mismatching facts deny. Passing a prior
policy result as an approval fails. A gate pass alone is insufficient for applying
files. A human approval command itself needs a current passed gate and action
binding, but not a previous approval; the engine subsequently creates the approval.

Fact objects and the stored run are detached from mutable input. A reused stale
snapshot remains the adapter's responsibility: the state owner must recheck revision,
approval and inputs under its own commit lock. Policy is not atomic commit authority.

## Local capability registry

`capabilities.v1.json` is policy-owned version 1.0.0. The server enables/grants only
an explicit subset. Registry activity class is returned even for a recognized denied
action; clients cannot relabel it. E08 `permittedCapabilities` is filtered for the
caller/mode but is **not** proof that current gate/approval/state conditions passed.

| Profile | Allowed caller / conditions |
| --- | --- |
| read | Trusted human/agent/system; explicit grant |
| propose | Trusted human/agent/system; current issued action/revision/checksum binding; only proposes/requests controlled work |
| human | Human browser/CLI/harness; current issued action plus passed applicable gate |
| materialize | Human only; matching current explicit approval plus all human conditions |
| provider | System **worker** only; live mode; explicit engine execution authorization and current action binding |
| operator | Human **harness** only; live mode; current approval/gate/bindings and explicit operator consent |
| proof | Human **harness** only; live mode; current gate/bindings and explicit operator consent |

Agents can request generation/reasoning/observation, but cannot directly invoke
providers through this surface, approve, apply, deploy, seed, reset or verify.
Fixture/replay runs cannot reach live provider/operator/proof capabilities.
Local fixture/replay workflow actions remain confined to their immutable configured
run root; any simulated output remains fixture/replayed, never provider proof.
No network/private-endpoint assumptions are added: V2/LOCAL08 scope is opaque,
server-configured and compared exactly.

## Failures and metadata

`GuardResult` exposes `version`, `allowed`, stable `reason`, `activity_class`,
`authorization_context` and `error`. Reasons distinguish malformed input, forged
authority, unknown/ungranted capability, wrong caller, changed context, non-live mode,
missing engine facts, stale revision, stale action binding, gate/approval absence,
operator consent and execution authorization.

E07 uses existing code enums; the more specific stable local reason remains on the
guard result. Unknown canonical context is not fabricated for configuration errors.
Diagnostic IDs identify local error responses, not persisted diagnostic evidence.
E08 is a newly constructed local envelope with a computed checksum and trusted
run-manifest lineage; it does not claim an approval or external execution.

## Validation and evidence

Use the existing contracts environment with `jsonschema==4.26.0`:

```powershell
& .\contracts\.venv\Scripts\python.exe -B -m unittest discover -s .\tests\policy -p test_policy.py -v
& .\contracts\.venv\Scripts\python.exe -B .\tests\policy\record_evidence.py
```

No packages are installed. Tests use clearly isolated fixture values from core
examples, not a canonical live case. Results/source hashes/consumed core hash are
written only to `.intent-to-impact\spikes\FND-03-01\`.
No Azure/model/auth operations, server, scheduler, state writes, or UX gate approval
are performed.
