# Core contracts — 1.0.0 / FND-01-01

**Status: core 1.0.0 accepted by the implementation orchestrator and frozen.**
The V2 risk/scenario/projection additions are also accepted and frozen; see
[`RISK-README.md`](RISK-README.md). The separate requirements/decision bundle is
under review; see [`DESIGN-README.md`](DESIGN-README.md).
JSON Schema is the sole shape authority. The core bundle contains no application,
persistence, policy engine, provider integration, risk scenario, or UX implementation.

## Install and verify (PowerShell, repository root)

Verified with Python 3.13.15, Node 25.0.0, npm 11.6.2 on Windows.
Generated Python types target Python 3.11+ and use only the standard library.
The generator environment is separate from the application.

```powershell
python -m venv contracts\.venv
& contracts\.venv\Scripts\python.exe -m pip install -r contracts\requirements.txt
npm ci --prefix contracts --ignore-scripts --no-audit --no-fund
$env:PYTHONDONTWRITEBYTECODE = '1'
& contracts\.venv\Scripts\python.exe tools\contracts\generate.py
& contracts\.venv\Scripts\python.exe tools\contracts\generate.py --check
& contracts\.venv\Scripts\python.exe -m unittest discover -s tests\contracts -p test_contracts.py -v
```

`requirements.txt` automatically applies the exact transitive constraints in
`requirements.lock.txt`; npm uses `package-lock.json`. Generator execution checks
installed versions against these locks. Pins: datamodel-code-generator **0.76.2**,
json-schema-to-typescript **16.0.0**, jsonschema **4.26.0**, TypeScript **5.9.3**.
Generation invokes those maintained generators directly, with fixed headers, no
timestamps, and LF bytes. It does not translate or patch model definitions itself.

`--check` regenerates in this task's project-local spike directory and compares both
artifacts without modifying the destination. Missing, extra, or changed files fail
with exit 1; tool failures use exit 2. `--output-dir` permits isolated tests only
under `.intent-to-impact\spikes\FND-01-01`. Each test deletes only its own scratch
directory. Never manually edit generated files.

## Published seam

All eight versioned schemas are definitions within
`schemas\1.0.0\core.schema.json` (Draft 2020-12). The bundle root accepts exactly one
contract. Address a specific contract with `#/definitions/<Name>`:

| ID | Definition / generated root name | Base consumer state |
| --- | --- | --- |
| D01 | CaseState | Minimal `examples\1.0.0\case.json`; Draft; empty section refs, work, events, idempotency records |
| D22 | LocalRunManifest | Creation-time run/scenario/scope context; rootId/configId are opaque server-configured references |
| E01 | EvidenceReference | Origin, freshness, completeness and eligibility are separate fields |
| E02 | CommandExecutionReceipt | Redacted argv, allowlist/root IDs, exit/times/log hashes, actual executor and optional human initiator |
| E03 | WorkEnvelope | queued/running/succeeded/failed/stale/blocked/recovery-required/awaiting-human/cancelled |
| E04 | DomainEvent | Ordered event with actual executor and optional human initiator, embedded in D01; no outbox service |
| E07 | ErrorEnvelope | Pre-context or known-context error, required reason/correlation/diagnostic ID/recovery; no fabricated canonical metadata |
| E08 | AuthorizationContext | Discriminated trusted caller class/channel/executor; optional human initiator; not an authorization decision |

Every canonical root (not the E07 error response) has runId, caseId, configured scope, schemaVersion, artifactId,
caseRevisionAtWrite, createdAt/updatedAt, stateChecksum and derivedFrom input hashes.
Only D01 owns logicalRevision. Sections and payloads contain opaque artifact/hash
references; later tasks own their domain contents. The initial small-demo caps are
1,000 work/idempotency records and 10,000 embedded events, not retention algorithms.

## Canonical checksums

The accepted foundation convention is sorted-key, compact JSON with
`ensure_ascii=True` and `allow_nan=False`, followed by one newline and encoded as
UTF-8. Non-ASCII characters use JSON escapes (including surrogate pairs where
needed). Exclude only the root `stateChecksum` when calculating its own hash.
`CaseStore.seal`, policy authorization output and
`tools.contracts.integrity.semantic_checksum` use this same convention.
Consumers should use the shared helper rather than introduce local serializers.
Pretty-printed example-file bytes are presentation, not canonical checksum bytes.

Python: `generated\1.0.0\python\core.py` exports TypedDict roots.
TypeScript: `generated\1.0.0\typescript\core.d.ts` exports structural declarations.
The compile-only consumer test covers all roots and rejects invalid mode/actor/origin,
missing metadata/diagnostics, human/model channel confusion, non-case logicalRevision,
and non-JSON timestamps.

## Execution attribution and trusted caller

E02/E04 `actor` is the actual executor, discriminated by `kind`:
`human` (only `demo-human` / `local-demo`), `agent` (`AGENT-*` ID), or `system`
(`SYSTEM-*` ID). Agent/system objects cannot carry human identity assurance.
Optional `humanInitiator` is a separate `DemoIdentity`; omit it when no human
initiated the operation. It does not turn an automated event into human approval.
The shared schema defines the only human identity; no new human identities or IAM exist.

E08 replaces the initial draft's top-level `actor`/`transport` with `caller`:

| callerClass | channel | caller.actor |
| --- | --- | --- |
| human | browser, cli, harness | HumanExecutionActor |
| agent | model | AgentExecutionActor |
| system | worker, harness | SystemExecutionActor |

These are discriminated schema/type unions, not independent strings that can be
mixed. `humanInitiator` remains separate, including for model callers. Only the
trusted dispatcher constructs E08 from the actual entry channel. Model-supplied
data never establishes caller class, human identity, or capabilities; schema
validation alone cannot prove that a blob came from a trusted producer.
Later policy must enforce capability restrictions, including denying model approval.
No permission grants or policy implementation are added here.

Execution identity does not assign Human Attention's `activityClass`: that remains
server-owned capability/decision classification. Operator-initiated automatic work
retains the human initiator rather than being hidden as entirely agent-operated.
Examples: `automatic-domain-event.json` has no human initiator;
`agent-authorization-context.json` retains a human initiator without changing its
agent/model caller.

## Errors before canonical context exists

E07 no longer inherits `CommonEnvelope`. Required fields are schemaVersion,
artifactType, response createdAt, code, human-safe message, correlationId,
diagnosticId, retryable, and allowedRecoveryActions. `diagnosticId` is an opaque
diagnostic identifier, not proof that a diagnostic has already been persisted.
The optional `diagnosticReference` retains the artifact ID/hash if persistence
has actually produced one.

Known runId/caseId/scope, artifactId, revisions, timestamps, stateChecksum,
derivedFrom and workId retain their established shapes but may be omitted or null
when unknown (response createdAt remains required). Never invent a canonical ID or
hash just to return an error. `pre-context-error.json` is the minimal example;
`error-envelope.json` preserves the existing known-context conflict fields.

## Validation and immutable context

Use `tools.contracts.validate.validate_contract(value, "D22")` for authoritative
schema validation, including formats and closed root shapes. Omit the ID to validate
against the bundle union. It raises `jsonschema.ValidationError`; install the pinned
validator dependencies above. No remote schema resolution is needed.

`assert_run_context_unchanged(old, new)` validates both D22 values, then compares
the schema's `x-immutable` fields: runId, caseId, scope, runMode, purpose, scenario
ID/version/hash, rootId, configId and optional sourceRunId. It raises `ValueError`
on a changed context. This comparison is **not** a storage lock or policy engine:
consumers must supply the trusted stored old context and enforce it at entry points.
Schema validation alone cannot detect mutation. A mode change requires a new run.
Replay requires sourceRunId; non-replay forbids it; ux-mock requires fixture mode.

## Evidence boundaries and limitations

All files under `examples\1.0.0` are **fixture contract examples**, not live evidence.
Their zero checksums and fixed times are shape placeholders, not verified hashes or
observations. `negative-cases.json` contains invalid replacement/deletion vectors
against positive examples; tests require the stated schema keyword to reject each.
Real local compiler/test execution is live-local evidence only, not provider proof.

Generated types are not runtime validators. Regexes, numeric/array limits,
date-time formats, conditional replay/mock rules and unknown-field rejection require
JSON Schema validation. Python uses the generator's supported
`--no-use-closed-typed-dict` mode to avoid a typing_extensions runtime dependency.
TypeScript closes structural object shapes via the generator's
`additionalProperties: false` default; common fragments are not standalone roots.
Checksum authenticity, chronology, uniqueness/order across records, run-to-case
consistency, replay freshness, capability enforcement and hero-proof eligibility
remain consuming-engine responsibilities. In particular, a fixture run or an
`eligible` string can never establish provider execution or complete a live hero.

The task's evidence receipt is
`.intent-to-impact\spikes\FND-01-01\evidence.json`: exact commands, test results,
source/generated hashes and tool versions. It supersedes `evidence-initial.json`,
which records the original 19 passing tests but predates the attribution/error
correction and is not evidence for the corrected bytes. Original `tests.log` is
retained; `tests-correction.log` records the corrected suite. That receipt records
the pre-acceptance correction; the orchestrator subsequently accepted core 1.0.0
after independently rerunning all 27 tests and generation checks. The risk bundle
was subsequently accepted after its 59-test review; design-bundle acceptance and
UX gates remain separate. Planning/design documents were not changed.
