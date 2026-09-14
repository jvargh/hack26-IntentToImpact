# V2 runtime/risk seam — FND-01-03

**Status: accepted by the implementation orchestrator; v1.0.0 is frozen.** Core
v1.0.0 remains accepted and frozen. No producer, UI, cloud operation, permission
grant, or UX gate is implemented or approved here. The separate
[`DESIGN-README.md`](DESIGN-README.md) packet remains under review.

## Registry, generation, and checks

The accepted core/risk slice of `registry\1.0.0.json` maps 19 contract IDs to four
schema bundles and eight generated artifacts; additive design entries are separate.
The existing pinned dependencies and environments are unchanged:
datamodel-code-generator 0.76.2, json-schema-to-typescript 16.0.0, jsonschema 4.26.0,
TypeScript 5.9.3. Run from the repository root in PowerShell:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& contracts\.venv\Scripts\python.exe tools\contracts\generate.py --bundle all
& contracts\.venv\Scripts\python.exe tools\contracts\generate.py --bundle all --check
& contracts\.venv\Scripts\python.exe tools\contracts\write_risk_examples.py --check
& contracts\.venv\Scripts\python.exe -m unittest discover -s tests\contracts -p 'test*.py' -v
node contracts\node_modules\typescript\bin\tsc --project contracts\tsconfig.risk.json
```

The default generation command remains **core-only** for compatibility.
`--bundle scenario|risk|projections` selects one new bundle; `--bundle all` verifies
all eight outputs. Unregistered output files are still rejected by `--check`.
The original core schema, core generated files, and both original consumer test
files are hash-locked in the registry and tested byte-for-byte.

New schemas live beside the core in `schemas\1.0.0`; references are local files.
Python uses strict reference resolution with remote fetching disabled for the new
bundles. TypeScript disables HTTP reference loading. Runtime validation uses an
explicit local `referencing.Registry`, with no network retriever.

**One canonical definition, mechanically expanded declarations:** the maintained
generators expand referenced core declarations into each generated module. This
is allowed; no second canonical `CommonEnvelope` or handwritten model exists.
There are no hand-edited generated imports, schema-flattening compiler, or new
generator. Required metadata is tested through JSON rejection, actual Python
TypedDict required keys/consumption, and TypeScript requiredness/assignability.

## Canonical scenario

`fixtures\scenarios\DEMO-CASE-CLAIMS-V2.json` is the sole V2 scenario input:

- scenarioId `DEMO-CASE-CLAIMS-V2`; scenarioVersion `2.0.0`; schemaVersion `1.0.0`.
- Content hash: `sha256:a140b136272f077c82dcd1d38e8e2c13b0aa7aea192be2a80112ccc744213e9a`.
- Desired-state hash: `sha256:367283b34f8f311bf1cdb4f7bd3e32d8c1e109c79a85205eef4485c677f3c497`.
- CP-01 targets `CMP-CLAIMS-STORE`, StorageV2, publicNetworkAccess `Enabled`,
  supportsHttpsTrafficOnly `true`, allowBlobPublicAccess `false`, minimumTlsVersion
  `TLS1_2`. It is configuration assurance, not complete access-control assurance.
- The proposed seed changes only supportsHttpsTrafficOnly to `false`; anonymous
  access remains disabled. It is **not authorized**, requires empty/synthetic data,
  sends no real data over HTTP, and blocks if policy prohibits it.
- Restoration requires the exact approved desired-state hash, the same binding,
  fresh evidence, and all four declared configuration predicates.
- Subscription, region, resource ID, and deployment receipt remain null until
  separately authorized operator preflight. No private-network resources or
  verifier VM are required.
- All eight promise IDs appear exactly once with bounded evidence requirements.
  RPO is null/unconfirmed; the scripted answer 15 is not a human confirmation.
- A has synthetic monthly estimate 6000 and no approved recovery profile; B has
  estimate 7200 and the active-passive profile; budget is 8000. These are inputs,
  not stored eligibility/recommendation verdicts, real billing, or savings.

Semantic hashing follows the single [foundation convention](README.md#canonical-checksums),
including ASCII escaping and exclusion of only the root `stateChecksum`.
`validate_scenario` verifies that hash,
the desired-state hashes, and CP-01 property/component/verifier link integrity.
Actual later human answers belong in requirements/confirmation artifacts; do not
rewrite this immutable initial fixture or silently relabel V1 history.

## Published contracts and exact keys

All new domain/evidence roots inherit the unchanged core metadata and add:
`scenario: {scenarioId, scenarioVersion, scenarioHash}`, `runMode`, and `purpose`.
This does not replace the trusted stored D22 context.

| ID | Generated root | Minimum consumer-facing content |
| --- | --- | --- |
| D03 | CustomerPromiseContract | `promises`, `confirmedPromiseIds`, requirement checksum, confirmation decision reference; no full requirements/approval engine |
| D13 | SandboxOperationReceipt | `operation`, `result`, exact `generationManifest`/`applicationReceipt` refs, `desiredStateChecksum`, resource IDs, actual actor/optional initiator, operator-consent reference, provider/evidence metadata |
| D14 | RuntimeBinding | `bindingState`, component/resource, operation/manifest/application refs, desired-state hash, boundAt/gaps |
| D15 | RuntimeSnapshot | `binding`, `completeness`, `evidenceWindow`, `observations`, `evidence`, missing kinds/errors |
| D16 | DriftFinding | Stable finding/promise/rule/component/resource IDs, severity/status, impact, baseline/snapshot/evaluation refs, proposed correction/restoration refs |
| D17 | PromiseEvaluation | Phase/status/reason, promise contract, exact binding/snapshot, verifier version/hash, predicate results, evidence, finding ID |
| E05 | HumanAttentionEvent | Stable event/attention/step/question/decision IDs, `activityClass`, action/kind, actual human, time, source E04 ref |
| P01 | ExperienceOverview | Joined `operationsRisk` P05, `continuityGraph` P06, coverage rows and nullable producer counts |
| P05 | OperationsRisk | `riskState`, impact, binding/snapshot/finding/evaluation refs, separate `restoration` summary |
| P06 | IntentContinuityGraph | Typed-source `nodes`, supported/gap/pending/broken `edges`, equivalent `listEntries` |

D15 normalized storage property names exactly match the four CP-01 names above.
Each observed property may be absent or null; absent data never implies a pass.
A wholly missing snapshot has `observations: []`, no invented binding, explicit
completeness/missing kinds/errors, and remains consumable.

Reference layout:

```json
{
  "contractId": "D14",
  "artifact": {"artifactId": "BINDING-EXAMPLE", "checksum": "sha256:<64 lowercase hex>"},
  "scenario": {"scenarioId": "DEMO-CASE-CLAIMS-V2", "scenarioVersion": "2.0.0", "scenarioHash": "sha256:<64 lowercase hex>"}
}
```

An `EvidenceLink` wraps an E01 reference as
`{reference: <typed reference>, origin: <core evidence origin>}`. The origin must
match the loaded E01. E01 itself stays frozen: its scenario association is established
through the **trusted D22 for the source run**, never by adding fields to E01 or by
changing only a scenario ID. References bind both IDs and actual artifact checksums.

`AllowedAction.actionId` uses the same lowercase-kebab core `ActionId` as
`Policy.authorize` request `actionId` and E05 `actionId`, not the uppercase
artifact `Identifier`. Pass the issued string unchanged; `capability` is the
separate policy capability. P01/P05 fixture actions and their E05 example use
`view-rpo-question` directly, with `read-case` as the capability. Regression tests
call the existing policy guard and validate E05 with that exact string, without
remapping or casts; artifact-style action IDs are rejected by all three seams.

### Status and attention boundaries

- D14: `bound | missing | stale | unknown`. `bound` requires non-null exact
  operation/manifest/application references, desired-state hash, and boundAt.
- D15: `complete | partial | missing | failed`; these are completeness, not verdicts.
- D17 runtime: `verified | breached | unknown | stale | not-applicable`.
  Design/delivery success is `design-supported` / `implementation-validated`, never
  runtime `verified`. Predicate results are `pass | fail | unknown`.
- D16: `open | correction-prepared | restoration-pending | resolved | stale`.
- P05: `known-risk | unknown | restoration-pending | no-known-risk`.
  Prepared/awaiting-operator/verification-pending remain separate from verified.
- P06 broken edges cite an existing breached/contradicted evaluation. Gap/pending
  edges explicitly identify missing context and cannot claim supported proof.
- E05: `product-workflow | demo-operator`. Only actual `demo-human` human attention
  is representable. An automatic E04 executor does not become human attention
  merely because an agent or worker ran. Classification/counting remains the
  capability/decision owner's responsibility, including operator-initiated work.
- Coverage counts may be null; do not turn null into zero or 100%. No fixed 7/8,
  8/8, live verdict, RPO test, recovery test, or billing claim is embedded here.

## Validation and ownership

`tools.contracts.validate.validate_contract(document, "D15")` validates shape.
Existing core-only calls and `CONTRACT_NAMES` retain their original behavior.
`REGISTERED_CONTRACTS`, `identify_contract`, and `fragment_validator` are additive.
New schemas use only references to the frozen core; compiled declarations live in
`generated\1.0.0\python\{scenario,risk,projections}.py` and matching TypeScript modules.

`tools.contracts.integrity.validate_reference_integrity(documents, runs, scenario,
external_references)` checks a closed trusted input set: body/reference checksums,
scenario tuple and stored-run identity, case/scope, exact baseline/manifest/resource
links, verifier/assertion IDs, observation/evaluation provenance, graph endpoints
and actual source references, and graph/list parity. The caller supplies `runs`
keyed by runId. A reference to an unloaded record fails.

The sole exception is an explicit trusted list of opaque **D10/D11/D12** references
validated by their future owning engines. Their canonical definitions are outside
this task. Such an external reference **cannot** become a supported graph node here
without a loaded canonical record. No skeleton D10/D11/D12 model was invented.

The integrity helper does **not** evaluate Azure properties, choose candidates,
derive eligibility/counts, authenticate a producer, grant permissions, persist
state, or collect evidence. Its graph labels are checked against already supplied
evaluation records; it never calculates a predicate verdict. Freshness/mode
eligibility, real source capture, authorization, gates and actual runtime assurance
remain owning-engine responsibilities.

## Examples and evidence

`examples\1.0.0\risk-examples.json` contains 25 labelled fixture records including
unknown/missing, known risk, and restoration-pending states. It is not the UX
response catalog and is not under `fixtures\experience`. Counts stay unassessed;
the last breach remains visible while a separate verification link is pending.
Every example hash is calculated from fixture bytes, not a provider result.
The fixture authoring script uses explicit literals, not evaluator business logic.
`risk-negative-cases.json` contains schema rejection vectors.

The earlier FND-01-03 import-deduplication blocker was resolved by the orchestrator:
mechanically duplicated generated declarations from one canonical schema are
permitted. Default external expansion passes; `--external-ref-mapping` is not used.
The blocked diagnosis and the orchestrator's `probe-included` proof remain historical
under `.intent-to-impact\spikes\FND-01-03`. The current evidence receipt supersedes
that blocked status; it records commands, tests, hashes and frozen-core preservation.
The earlier submitted receipt is retained as `evidence-submitted.json` when the
narrow action-ID correction supersedes it.
No historical core/V1 example or receipt has been reinterpreted or overwritten.
