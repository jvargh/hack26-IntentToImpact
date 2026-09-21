# Initial V2 experience fixtures — MOCK-01-01 / U01 v1.0.0 / revision 2

**Owner: A-fixtures. Review: implementation-orchestrator (A/C).**
Start with `initial-v2-r2\manifest.json`. This is a materialized, bounded set of
**complete P01 responses with embedded complete P05/P06**, not an application,
the full FX catalog, an approval gate or live-proof evidence.

Revision 2 uses new run/case/artifact identities and the corrected shared ASCII-
escaped checksum convention. The original `initial-v2` JSON bytes are retained,
hash-guarded by the new manifest, and must not be loaded as currently valid fixtures:
their non-ASCII projections used the earlier defective checksum convention.
The scenario itself, its hash and authored visible story remain unchanged.
Both revisions are historical V2 under LOCAL-09, not current NSP/V3 proof.

Schema/design/data inputs remain hash-pinned in the fixture manifest. Mutable
registry and validator/generator source hashes are captured in each validation
receipt instead: compatible tooling changes require fresh validation, not rewriting
an immutable fixture revision. Changed output bytes require a new revision.

Consumes the frozen `contracts\registry\1.0.0.json`, risk/projection schemas and
their actual validation/integrity helpers. FND-01-03 acceptance is supplied by the
dispatch; the contract README's earlier “not accepted” heading is historical.
Current design: `design\components\CURRENT.v2.json`.
Its earlier pending-binding note is now resolved for these exact P01/P05/P06
fields by the accepted schemas; it is not a claim that the other projections froze.

Scenario: **DEMO-CASE-CLAIMS-V2 / 2.0.0**,
`sha256:a140b136272f077c82dcd1d38e8e2c13b0aa7aea192be2a80112ccc744213e9a`.
The scenario file is referenced, never rewritten. All runs are immutable
`fixture` / `ux-mock`; every evidence origin is `fixture` and E01 eligibility is
`ineligible`. `verified` in FX-12 means **an authored example of the verified
presentation**, never an actual verification or live-proof eligibility.

## Files and selected coverage

Each scene directory contains:
- `response.json`: the entire closed-schema P01 response; render it directly.
- `records.json`: the closed referenced record set, including standalone P05/P06
  exactly matching their embedded forms, plus explicit opaque external references.

`run-manifest.json` supplies the trusted fixture D22 for all scenes and their
E01 origins. `manifest.json` supplies file hashes and one primary action ID;
`action-map.json` supplies only explicit authored scene navigation.

| Scene | Meaning | Deliberate limit |
| --- | --- | --- |
| FX-01 | Unknown runtime; all promises and RPO unconfirmed | No full P02 question/answer UI or actual confirmation |
| FX-09 | Known HTTPS-required breach; graph broken edge cites D17 | Public network access Enabled is desired, not the breach |
| FX-10 | `restoration.status=prepared`; last breach remains visible | No delivery approval/applying/local-byte demonstration |
| FX-11 | Verification pending; last breach remains visible | Not a claim that local materialization or restoration occurred |
| FX-12 | Four passing fixture predicates, fixture restoration receipt and D17 | Other promises unknown; no live execution or human approval |
| FX-11:missing-evidence | Restoration unknown with missing evidence/binding | No inferred success |
| FX-09:stale-evidence | Old observation marked stale; graph evaluation edge is a gap | No fresh risk/verification claim |

All eight coverage rows are explicit. CP-05 remains unconfirmed. Counts stay
**null/unassessed**, not zero, 7/8, 8/8 or percentages. Later scenes contain authored
fixture confirmation IDs for seven promises, never real human decisions. FX-01
does not silently advance those confirmations when a snapshot is opened.

## C integration: exact frozen fields, not old prop guesses

| Intended component | Bind now | Deferred/mismatch |
| --- | --- | --- |
| CaseShell | P01 `businessGoal`, `scenarioOrigin`, `asOf`, `currentWork`, `allowedActions`, `blockers`, `artifactRefs` | No invented `safeArtifactRefs`, `evidenceOrigins`, identity or lifecycle fields in P01 |
| PromiseCard | P01 `coverage.rows[]`; CP-01 impact from `operationsRisk.customerImpact` | No P02 `promiseRows`. Other statements may be inspected in the loaded D03, not joined to derive new state |
| RiskPanel | P05 `riskState`, `headline`, `customerImpact`, `binding`, `snapshot`, `findingRefs`, `evaluationRefs`, `restoration` | Not `findings`/`promiseEvaluations`/`evidenceGaps` arrays from the earlier design wish list |
| ContinuityGraph / ordered list | P06 `nodes`, `edges`, **`listEntries`** | No generic traversal, editing, `focusedPromiseId` or client-created gap collection |
| Initial evidence inspection | Resolved typed E01 references, observed time, collector, origin/state/eligibility; D15 property detail | Full P09 drawer projection and raw-artifact endpoint are not published yet |
| ChangeSet/Decision panels | Only the narrow P05 restoration summary for initial previews | P04/full D10-D12 and distinct material/delivery/applying examples wait for FND-01-04 / MOCK-01-02 |

The initial graph is already focused on CP-01. Scenario-supported promise/component
edges do **not** assert runtime success. Its evaluation edge cites the exact D17;
graph and list refer to the same nodes and incident edges, including broken/gap
meaning. Use node labels and supplied evaluation reason `https-not-required` for
human-readable impact. Do not calculate status from D15 properties in the UI.

Every loaded reference is checksum/context checked. **Only D10/D11/D12** may appear
in `externalReferences`, using the accepted integrity-helper exception for
not-yet-published delivery records. They are opaque synthetic fixture facts, not
canonical record implementations or valid supported graph-node proof. No such
opaque node is present in these graphs.

## Canned interaction boundary

Use the exact lowercase core `actionId`, unchanged, with capability `read-case`.
P01 and P05 expose the same actions for joined/standalone rendering. In a joined
screen render the action once; `manifest.scenes[].primaryActionId` identifies the
single dominant action, with stale/missing navigation secondary.

The map is **navigation between independent authored snapshots**, not execution
of the product workflow. For example, viewing the risk scene from FX-01 does not
confirm RPO, approve a design or deploy a baseline. Reading prepared → pending →
verified examples does not skip or perform approvals/materialization/restoration.
Those full functional steps are explicitly outside this initial slice.

`inspect-fixture-evidence` keeps FX-12 selected and opens only its already-loaded
fixture record detail; it does not invoke a provider or pretend to be P09.
Future fixture transport performs a table lookup and loads the complete selected
response, not an evaluator/coverage calculator. It must never invoke HTTP/cloud
endpoints, shell commands, real capability mutations, or a mock-to-live toggle.
The authored scope has the all-zero subscription sentinel and synthetic resource
IDs. No Azure client, credentials or network request is involved.

The full FX-00..19 catalog, approvals, questions, per-file diff/materialization,
away/attention and receipt/export experiences remain for subsequent accepted
contracts and MOCK-01-02. **No GATE-UX01 acceptance is implied.**

## Build and validate

From the workspace root, use the existing pinned contract environment:

```powershell
& contracts\.venv\Scripts\python.exe -B fixtures\experience\build_initial.py
& contracts\.venv\Scripts\python.exe -B fixtures\experience\build_initial.py --check
& contracts\.venv\Scripts\python.exe -B tests\fixtures\validate_initial.py
```

Authoring reuses published risk examples and `seal`; only metadata/references and
explicit canned content change. Reference resealing is a finite fixture-DAG walk,
not a state/policy engine. No schema or generated type is copied or edited.
Validation invokes actual `validate_contract` and `validate_reference_integrity`
against all full projections and loaded fixture records. Negative tests include
live-origin/operation claims, missing references, tampered hashes, old scenario,
graph/list divergence, unsafe restoration and live transport declarations.

Evidence is written to a unique attempt directory under
`.intent-to-impact\spikes\MOCK-01-01\R2\`, including failed runs.
The earlier runner overwrote its latest receipt during revalidation; the retained
root receipt now records that failure, not the earlier 23-test acceptance.
New attempts never overwrite earlier receipts or reconstruct lost evidence.
Its command execution is **live-local validation**; its inputs remain fixture/
ux-mock, never live-external proof. No historical V1/design receipt is modified.
