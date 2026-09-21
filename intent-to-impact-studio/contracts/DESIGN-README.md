# Requirements, decisions and generation plans — FND-01-02

**Status: accepted as the bounded V2 contract seam.** The orchestrator ran the
90-test suite, checked all ten generated outputs, and corrected the standalone
human-event scenario-link comparison with 29 passing related design tests.
The accepted core and V2 risk/scenario/projection contracts remain frozen. V2
semantics are historical under LOCAL-09; NSP/V3 publication is separate.
No product/UX gate passes, human approval occurs, or model/provider call runs as
a result of this packet.

## Published mapping

`schemas\1.0.0\design.schema.json` is a separate Draft 2020-12 bundle.
`registry\1.0.0.json` adds seven IDs, bringing the registry to 26 IDs/five bundles.
All seven new roots inherit the existing `risk.RiskEnvelope`, hence the unchanged
core run/case/scope/version/revision/time/checksum metadata plus immutable run
mode, purpose and scenario tuple. There is no competing D03 definition.

| ID | Root / artifactType | Contents and source ownership |
| --- | --- | --- |
| D02 | Requirements / `requirements` | Goal, requirement/promise IDs, bounded V2 constraints, explicit RPO question/answer/confirmation |
| D04 | ArchitectureProposal / `architecture-proposal` | Agent-only, proposal-only authority; source requirements/D03/catalog, two option attribute sets and untrusted recommendation |
| D05 | ArchitectureModel / `architecture-model` | Engine-validated option attributes, proposal/review/D03 refs, recommendation and nullable selection/decision linkage |
| D06 | ArchitectureDecisionRecord / `architecture-decision-record` | ADR ID/title/context/considered options and a nested **DecisionReceipt** for human selection/rejection |
| D07 | Approval / `approval` | Separate explicit approval status, exact subject/action/revision/gate/input binding, actor/event and validity window |
| D08 | ReviewGateEvaluation / `review-gate-evaluation` | Nested **ReviewResult** (checks/findings/option assessments) and **GateEvaluation** (effective result and separate approval snapshot) |
| D09 | GenerationContract / `generation-contract` | Bounded generation plan: source references, selected option, pinned module/template tokens, root ID, file allowlist and V2 desired state |

D06 is **one canonical root**, not two independently editable ADR/decision stores.
Its `decisionReceipt` is null while `status=proposed`; recorded/superseded ADRs retain
the receipt. Choosing an option does not constitute D07 approval.

D08 is likewise **one canonical root** containing review and gate data. D05/D06
reference that root checksum. Agent findings belong to the review; they cannot
be used as a human decision or approval.

## References and current inputs

New field-specific references reuse the frozen core `ArtifactReference` shape:
`{artifactId, checksum}`. The field declares its target:

| Consumer field | Target |
| --- | --- |
| D04 `requirements` | D02 |
| D05 `sourceProposal`, `review`, `decision` | D04, D08, nullable D06 |
| D06 `architecture`, `review`, `requirements` | D05, D08, D02 |
| D07 `gateEvaluation` | D08 |
| D08 `requirements` | D02 |
| D09 `requirements`, `architecture`, `decision`, `gateEvaluation`, `approval` | D02, D05, D06, D08, nullable D07 |

Polymorphic `D08.subject` and `D07.binding.subject` have explicit accompanying
`subjectContractId`. D07 can describe future D11/D13 subjects, but this task does
not implement D11 or make an unloaded subject usable.

References to the already-frozen D03 and E05 retain the accepted risk layout:
`{contractId, artifact: {artifactId, checksum}, scenario: {scenarioId,
scenarioVersion, scenarioHash}}`. This avoids changing the frozen
`risk.LinkedContractId` enum or reauthoring its canonical reference source.
`D03.requirementChecksum` binds to the loaded D02 body; D03's shape stays unchanged.

`derivedFrom` records the checksum under each direct input field name, plus
`scenario`. Nested decision/gate `boundChecksums` retain the same input hashes.
Use the shared `semantic_checksum` and the
[foundation convention](README.md#canonical-checksums), including ASCII escaping.
Use `assert_current_inputs(document, expected_inputs)` with **trusted current**
references from the owning engine. An internally consistent historical document
does not become current merely by copying its old hashes into a new request.

## Unknown RPO and the catalog oracle

- D02 `rpoQuestion.valueMinutes` is null and `confirmation` is null while unanswered.
  A `confirmed` D02 must have the explicit answered branch.
- This bounded V2 question accepts the scripted 15-minute answer, not a model
  default. `confirmation` contains the human decision/action/time and an E05
  reference. The source event must match the question, decision, actor and action.
- Cross-reference checks reject a D03 claiming CP-05 confirmed when its referenced
  D02 still has an unanswered RPO. The canonical V2 scenario itself remains
  immutable with initial RPO null.
- `OptionDefinition.catalogFacts` references the existing scenario
  `CandidateProfile`: A is 6000 with no reviewed regional-recovery profile;
  B is 7200 with that profile; the requirement budget is 8000.
- Option attributes have **no eligibility/approval property**. D08's separate
  system-produced `optionAssessments` reports design eligibility and named rule
  results. The fixture explicitly reports A's mandatory failure and B's eligible
  assessment. No code in this packet calculates that oracle or a runtime verdict.
- The fixture's agent proposes cheaper A; the validated model recommends B from
  the referenced eligibility assessment. Human selection and approval stay separate.
  Catalog prices are synthetic estimates, not bills or realized savings.

The component vocabulary is intentionally limited to this packet's claims-storage
component, public endpoint, managed-identity intent and approved V2 storage controls.
Relationships name declared component IDs; no guessed graph edge or live resource
binding is created. P02/P03 and other full mock projections remain FND-01-04 work.

## Review and approval states

The six `GateId` values remain requirements-ready, design-ready, generation-ready,
delivery-ready, operation-ready and remediation-ready. Check statuses are
`pass`, `pass-with-warnings`, `stale`, `blocked`, in increasing severity.
JSON Schema rejects a reported effective result weaker than a reported check.
The engine still owns check execution and final status derivation.

`gate.approvalStatus` is separately `not-required | pending | approved | rejected |
stale`; it is a snapshot, not authority. A blocked gate with an approved receipt is
a valid record of **blocked checks**, never permission to proceed. Passing checks
with approval pending are equally representable.

D07 statuses are `pending | approved | rejected | stale | expired`. Pending records
have no invented human actor, decision time/ID or attention event. Actual approved
and rejected responses require the frozen `HumanExecutionActor` (`demo-human`,
`local-demo`) and their E05 source event. Historical stale/expired receipts remain
representable but cannot satisfy a current approval comparison.

`assert_current_approval_binding(approval, expected_binding, as_of,
attention_event=trusted_event)` checks:

- body checksum and approved status;
- exact subject type/reference, capability, lowercase-kebab action ID, revision,
  gate ID and all input checksums;
- `issuedAt <= decidedAt <= as_of < expiresAt`;
- actual source event checksum, human actor, approved response, action/decision
  identity, the reference's scenario tuple, run/case/scope/scenario/mode/purpose
  and decision time.

The caller supplies both current binding and clock; neither is inferred from the
claimed approval. The helper returns no permission or workflow decision. It is
not the policy module's noncanonical `ApprovalBinding` dataclass, and this packet
does not modify policy, store, work or API sources.

## Generation plan boundary

D09 references the exact D02/D03/D05/D06/D07/D08 versions. Its selected option must
match the referenced decision; a ready fixture plan requires acceptable referenced
generation checks and a current matching design approval comparison. This validates
reported relationships; it does not render files or run a gate/approval engine.

Outputs declare normalized relative paths, non-executable file kinds, pinned
module/template IDs/versions/checksums and component/promise mappings. The plan
permits Bicep, Bicep parameters, JSON and Markdown, not arbitrary shell/code fields.
It holds only an opaque `outputRootId`; the later renderer must resolve its approved
root, enforce filesystem/reparse/reserved-name safety, and load actual approved
templates. Module descriptors in these fixtures do not prove installed modules.
D10 file manifests, D11 change sets and D12 materialization receipts are not added.

## Validation and generated consumers

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& contracts\.venv\Scripts\python.exe tools\contracts\generate.py --bundle design
& contracts\.venv\Scripts\python.exe tools\contracts\generate.py --bundle all --check
& contracts\.venv\Scripts\python.exe tools\contracts\write_design_examples.py --check
& contracts\.venv\Scripts\python.exe -m unittest discover -s tests\contracts -p 'test*.py' -v
node contracts\node_modules\typescript\bin\tsc --project contracts\tsconfig.design.json
```

The existing pins and default core-only generator command are unchanged. New
outputs are `generated\1.0.0\python\design.py` and
`generated\1.0.0\typescript\design.d.ts`; never edit them manually. Mechanical
declaration expansion from the same accepted canonical schemas remains permitted.
New generation disallows remote refs and requires fully resolved local references.

JSON Schema remains authoritative for conditional states, formats, path patterns
and nonempty maps. Python/TypeScript consumers test required inherited metadata,
actor separation, shared action IDs and actual dictionary checksum typing.
The nonempty-map constraint is expressed as a standard negated empty value on the
containing object, avoiding a generator external-ref merge limitation without
copying or weakening the canonical `ChecksumMap`.

`validate_design_references` checks a closed trusted record set and run/scenario
context. For ready-plan comparisons it requires explicit `current_bindings` and
`as_of`. Source-reference validation does not authenticate a producer or prove an
LLM call; live D04 invocation references require actual adapter-owned E06 proof.

## Fixtures, compatibility and handoff

`examples\1.0.0\design-examples.json` contains explicitly fixture-labelled unknown
and confirmed RPO, untrusted proposal, engine-reported A/B assessments, ADR,
pending/approved/rejected/stale/expired approval and draft/ready plan examples.
Every human decision/approval is an authored **fixture**, never a claimed real action.
Negative vectors live in `design-negative-cases.json`.

Frozen core/risk schemas, all eight existing generated artifacts, canonical V2
scenario and accepted risk examples are hash-guarded. All prior 59 regression
cases remain; only their registry-count assertion is scoped to the original four
bundles so additive registration is allowed without losing its 19-contract check.

Evidence: `.intent-to-impact\spikes\FND-01-02\evidence.json` plus the independent
`acceptance-review.json` in that directory. UXD-002 field binding
and human mock review remain pending. No FND-01-04, UI, provider operation, actual
approval, or product gate is performed by this packet.
