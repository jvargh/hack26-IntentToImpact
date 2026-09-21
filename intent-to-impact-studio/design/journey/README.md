# Five-moment local demo — design v1.0.0

**UX-01-01 · P0-HERO · D-ux · provisional, human review pending.**
`hero-journey.v1.json` is the bounded walkthrough/state map;
`..\information-architecture\inventory.v1.json` is the route/component draft.
They implement design intent, not a second task plan, a runnable prototype, U01
payloads or canonical D/P schemas. All evidence is **ux-mock**. No live behavior,
human approval, resource identity or accepted scenario hash is asserted.

## Reading and building

Read `moments`, then `interactions`, then their `states`. Use route/component IDs
from the inventory. Expected field references deliberately have **binding pending**:
A reconciles these against the frozen projections; C/D later bind shared props.
Do not generate types, authorization rules or actual fixtures from this document.
`illustrativeNextStateId` means “next scene to inspect,” not “execute this transition.”
An async completion, observed breach or operator acknowledgement is a separate
authored response, never an effect of clicking Inspect. Do not promote fixture
state to live; open a new immutable run for a different mode.

The browser paths are navigation proposals, not files or implemented endpoints.
Implementation uses `/cases/:caseId/implementation`, replacing the source's remote
Delivery emphasis with LOCAL-01. Decisions and the evidence drawer are contextual
drill-downs, not extra hero moments.

## Customer-first hierarchy

1. **Promise:** Contoso's seasonal claims deadline and sensitive documents come
   first. RPO is initially unknown; the authored answer is 15 minutes, requiring
   real human confirmation in a live run.
2. **Decision:** Show A's absent approved regional-recovery profile beside its
   synthetic USD 6,000 estimate. B at synthetic USD 7,200 is the lowest-cost
   eligible design under the USD 8,000 limit. Present server verdicts; do not
   manufacture savings or infer recovery proof from design support.
3. **Implementation Prepared → Approved → Materialized:** Show bounded files,
   validation and exact approval separately. Materialized means **local files**.
   **Azure deployed** and **Runtime verified** stay separate evidence-backed facts.
4. **Promise At Risk:** The dominant scene is CP-01's broken private-connectivity
   edge and customer impact. No Scan CTA. Show the observation time, evidence gaps
   and one current decision. The safe seed changes public network access, not
   anonymous access; do not claim documents leaked or were accessed.
5. **Proof:** Show fresh scoped restoration, remaining unknown promises, and the
   three receipt questions. No fixed 7/8 success story. Unknown billing, recovery
   tests and timing stay unavailable, not zero or verified.

Every screen has **at most one dominant action** from its current server-issued
stage. Answer/Confirm, Select/Approve, Review/Materialize, Review Correction and
Inspect Evidence/Finish are alternatives over time, never a toolbar of equal CTAs.
During work, zero is valid. Back, reject, evidence and Mark updates seen remain
accessible secondary actions. Seen does not mean approved.

## Required 18 interactions

The implementation plan groups experiences rather than assigning eighteen source
IDs. These stable design IDs preserve every listed interaction and system variant.

| ID | Builder walkthrough | Required examples |
| --- | --- | --- |
| UX-I-01 | Define/confirm customer promise and impact | FX-01 |
| UX-I-02 | Answer consequential RPO question | FX-02 |
| UX-I-03 | Compare rejection/eligibility | FX-03 |
| UX-I-04 | Explicit design approval; generation progress | FX-04/05 |
| UX-I-05 | Prepared files, diff and validation | FX-06 |
| UX-I-06 | Local delivery approved, not applied | FX-07 |
| UX-I-07 | Applying → Materialized; separate baseline | FX-07 applying; FX-08 and baseline variant |
| UX-I-08 | Proactive risk and exact graph/list edge | FX-09 |
| UX-I-09 | Away: completed, failed, pending; mark seen separately | FX-18 |
| UX-I-10 | Product attention versus operator effort, window/gaps | FX-13/18 |
| UX-I-11 | Bounded correction with separate approvals/application | FX-10 and four named variants |
| UX-I-12 | Local correction → operator consent → pending fresh verification | FX-11 and two named variants |
| UX-I-13 | Fresh scoped restoration, unknown promises retained | FX-12 |
| UX-I-14 | Receipt and mock export: promise, delivery, value | FX-13 |
| UX-I-15 | Evidence provenance/limitations, expand and return | FX-19 |
| UX-I-16 | Empty start and meaningful loading | FX-00 + loading |
| UX-I-17 | Stale/blocked/failed, diagnostics and permitted recovery | FX-14/15/16 + disabled/retry |
| UX-I-18 | Reconnect/resume; accessible narrow/keyboard/zoom journey | FX-17 + shared variants |

Correction ordering is deliberately visible: `material-approval-pending` →
`material-approved-delivery-pending` → `delivery-approved-not-applied` →
`applying-locally` → FX-11. Never merge material approval, delivery approval and
Materialize. Runtime restoration consent is an operator step, separately disclosed.
Runtime-only drift can reuse unchanged approved Bicep; show the bounded declarative
reconciliation descriptor and desired-state reference, not a gratuitous code edit.

## Fidelity is visual effort, not functional scope

- **Tier 1 — hero polish:** promise/question, options, prepared change set,
  risk/remediation, verified restoration, receipt and away. Calm editorial workspace;
  customer impact and the focused broken edge dominate. Confirm aesthetics at UX01.
- **Tier 2 — functional clarity:** approvals, materialization, stale/blocked/failed
  states and evidence drawer. Unmistakable labels, exact scope, accessible recovery.
- **Tier 3 — test-focused:** loading, applying progress, reconnect/retry/recovery,
  and viewport/focus permutations. Fully functional, less visual polish.

All routes require empty/loading/blocked/stale/failed/recovered states and persistent
origin/identity labels. The inventory and shared variants are a coverage requirement
for later full-response fixtures, not claims of completed browser tests.
Desktop plus one narrow layout, keyboard-only operation, 200% zoom and reduced motion
are P0. Graph and ordered list use identical server edges and gaps. Diff reading is
per-file; the drawer traps/restores focus and supports Escape. Status uses text/icon,
not color alone. No shared tokens, fonts or UI components are implemented here.

## Handoff and open review

- **UXD-001** is explicitly illustrative pending aesthetic feedback, not a meeting.
- **UXD-002** records the real unresolved contract-binding question for A/C/D.
- **UX-Checkpoint-01 / GATE-UX01 remains pending.** Human business-wording,
  primary-promise and hierarchy review plus an actual navigable mock are outstanding.
- UX-02 tokens, U01 fixtures, component binding and downstream UI work are not accepted
  by this handoff and are not started here.

Run from the workspace root:
`python -B design\tests\validate.py --task UX-01-01`.
The receipt under `.intent-to-impact\spikes\UX-01-01\` reports real local validation
only, with artifact hashes and unresolved decisions. Tests deliberately remove the
RPO/correction states and duplicate route/component IDs to prove coverage rejection.
