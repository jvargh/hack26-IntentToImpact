# Lightweight UX records — v1.0.0

**UX-03-01 · P0-SUPPORT · D-ux · reviewer: implementation-orchestrator.**
These local U04 records are provisional design-process artifacts, not domain
approval schemas. No approval or checkpoint meeting is claimed.

- `ux-record.schema.json`: closed JSON Schema (2020-12) for one UXD or checkpoint.
- `checkpoint-agendas.v1.json`: six records, **all pending**; UX01 is a draft.
  Roles and criteria reference implementation §10.5 and task §12.0, not invented
  attendee identities. `participantRoles` are consultation/review responsibilities,
  **not a list of required human identities**.
- `..\decisions\UXD-001.json`: explicitly **illustrative**, pending feedback →
  rationale → component/fixture/task mapping. It must never be promoted as evidence
  that a stakeholder raised or approved the example.
- `..\decisions\UXD-002.json`: real pending question about A/C/D projection binding.
  Referenced future tasks are traceability only; this bundle does not dispatch them.

## Capture and promotion

Copy the matching record shape, allocate a new stable UXD ID, and record the actual
reporter, checkpoint, screen/component, fixture/projection versions, observation,
severity and proposed change. Keep source versions and precise evidence references.

1. Classify **presentation-only**, **projection-contract**, or **domain-policy**.
2. D/C review presentation; A additionally reviews contract/domain changes. Record
   technical reviews by the assigned implementation reviewer/orchestrator, explicitly
   `agent` or `human`, with lane, disposition, timestamp, subject version and evidence.
   One assigned reviewer may cover multiple lanes; no distinct-person requirement
   exists. Never label an agent as human. Actual stakeholder/demo-human product/UX
   confirmation belongs in the checkpoint's separate `humanApproval`, not a lane review.
3. Update the approved mock and, in their owning accepted tasks, tokens/props and
   fixtures. Bind affected plan/task/component IDs to the UXD; do not create a
   second design-management application.
4. Implement bounded accepted changes in shared components/API, not frontend
   evidence, eligibility or authorization rules.
5. Validate schema, keyboard/narrow/zoom behavior, accessibility and live semantic
   consistency. Link actual paired mock/live evidence before `validated`/`closed`.
6. Freeze the reviewed version; retain history, decisions and unresolved blockers.
   If real data improves the design, revise the mock rather than forcing pixel parity.

States are `pending-review`, `approved`, `implemented`, `validated`, `closed`,
or `blocked`. A gate is `pending`, `passed`, or `blocked`; it is not a task.
Required human product/UX acceptance is never implied by successful local tests.
`approved` on a UXD means **technical-design-only** (`approvalScope`); it cannot
approve the linked checkpoint or authorize product/runtime actions. The six checkpoint
gates retain explicit product/UX acceptance from the one `demo-human`. This is the
same local human, including the UX confirmation at checkpoint 03, not a new human
persona for D/C/operator. Engineering consultation roles remain unchanged.

For a structurally complete gate candidate:

- `technicalReviews.requiredRoles` covers the listed technical consultation lanes,
  excluding Stakeholder. Each lane has a nonempty evidence-bearing disposition.
  Reviews may be agent or human; an operator-lane review is not runtime operation consent.
- `humanApproval` contains one genuine `demo-human` product/UX decision, independent
  of technical review completeness. Agent-authored product approval is invalid.
- The checkpoint is reviewed, prerequisites retained, required evidence referenced,
  and no unresolved findings remain. None of these automatically changes gate state.

**Authenticity is not a JSON property.** The structural validator requires populated
review/evidence fields but cannot establish whether a plausible reference, an
`actorType: human` assertion or even the literal `demo-human` came from a real human.
It therefore always returns `acceptanceEstablished: false` and
`evidenceAuthenticity: unverified`, even for a structurally complete test candidate.
The implementation-orchestrator must inspect the actual source evidence and reviewer
assignment, genuine human confirmation, subject/version and prerequisite acceptance.
Missing, fabricated, misattributed or uninspectable evidence blocks acceptance; leave
the real gate pending (or record a blocked finding). No authentication system or
automatic acceptance engine is introduced here.
A material finding stays in a bounded UXD; a hypothetical example is retired/replaced
by actual feedback, not silently treated as a real participant statement.

## Validation

From the workspace root:

```powershell
python -B design\tests\validate.py --task UX-03-01
python -B -m unittest discover -s design\tests -p "test_ux_*.py" -v
```

Tests use standard `unittest` plus the environment's existing `jsonschema` package;
no package installation, manifest or new runner is introduced. The schema is
portable to any Draft 2020-12 validator. Additional semantic checks bind gate IDs,
participants, record states, references and technical-review completeness. Tests
allow explicitly agent/human technical reviews (including one reviewer covering
multiple lanes), reject missing technical evidence and agent product approval, and
show that plausible but fabricated evidence cannot establish acceptance. Illustrative
records stay pending; alignment evidence and explicit gate checks remain required.

`validate.py` runs one task suite and writes its log plus versioned/hash-linked
receipt only beneath that task's permitted `.intent-to-impact\spikes\` directory.
Receipt validation origin is **live-local**; design origin remains **ux-mock**.
Neither receipt closes human gates, proves browser accessibility or constitutes
mock/live production alignment. Both task receipts list the unresolved questions,
separating human product decisions from technical lane reviews.
When refreshing only the accepted UX-01 receipt after a shared validator change,
use `--task UX-01-01 --receipt-only`: current test output is embedded in that receipt,
leaving its accepted journey/IA sources and previous test log unchanged.
