# U02 tokens + U03 component/state draft — v1.0.0

**UX-02-01 · P0-SUPPORT · D-ux · review: implementation-orchestrator/C.**
Technical dependency UX-01-01 is accepted. **UX-Checkpoint-01 human visual approval
and UXD-002 projection binding remain pending.** These are reusable design assets,
not an implemented mock, UI, approved aesthetic baseline or live app.

## LOCAL-08 scope update — V2 binding blocked

Current direction is **DEMO-CASE-CLAIMS-V2 (2.0.0)**: bounded configuration assurance
on an approved public endpoint, with HTTPS required, anonymous blob access disabled,
and minimum TLS 1.2. No private endpoint, private DNS, VNet or verifier VM is required.
Use neutral **Protected Claims / HTTPS** topic headings and the supplied projection's
actual promise text/status. A topic heading is not a claim of verified protection.
This is not private-connectivity or complete access-control proof.

The `scenarioId` in this draft remains **V1** because its state/prop references still
come from the accepted historical V1 journey/IA. `scenarioAlignment` explicitly
records the V2 target and blocks live fixture binding. **A separate V2 journey/IA
wording revision is required**; this task does not perform it or claim V1 meets V2.
Do not carry the historical private-connectivity wording into a V2 prototype.
Normal in-product promise confirmation remains required. The direction change
does **not** authorize deployment, drift seeding or any cloud operation.

## Builder entry points

- `tokens.v1.json`: single U02 source for both future mock and production.
- `tokens.v1.css`: deterministic `--iti-*` custom-property projection.
- `..\components\component-state-contract.v1.json`: all 18 accepted component IDs,
  concrete grouped prop drafts, events, hierarchy, fixture/interaction references,
  and all 28 accepted scene/variant references across FX-00..19.
- `..\tests\validate_tokens.py`: standalone standard-library checks and CSS emitter.
  It never edits accepted journey/IA/review artifacts or their validators.

Future C-owned shared components import **the same CSS once**, regardless of
transport. Do not create mock-only color, status, spacing or action variants.
Non-CSS consumers read the same JSON/version. Prop groups are design names pointing
only to the existing inventory's expected P/D22 fields, **not canonical schemas or
TypeScript definitions**. A/C must reconcile them after projection freeze.

## Calm, customer-first editorial treatment

Use warm paper, white reading surfaces and dark ink. Locally available Palatino/
Georgia headings add editorial character; Segoe UI body text keeps controls clear;
Cascadia Mono/Consolas is restricted to technical drill-downs. The system stacks
require **no font downloads, CDN, external icon library or design service**.

- Lead with customer impact, then the promise/status, observation limits and one
  server-issued action. Evidence origin/as-of are visible; technical IDs expand.
- Risk is the single dominant red scene, not an alarm dashboard. The graph uses
  a thicker broken/gapped edge plus text and an equivalent ordered list.
- Local Prepared/Approved/Materialized are blue; Azure deployment is a separate
  violet fact; scoped Runtime verified is green. Labels and distinct icon intentions
  always accompany color. Fresh evidence alone is **not** verified.
- The `Demo Identity` label is compact but readable at 0.875rem, with full
  local-demo assurance limits in detail. Do not minimize fixture/replay labels.
- Disabled actions keep readable text and a reason; do not lower opacity over the
  whole control. Reduced opacity could invalidate the measured contrast.

`statusPresentations.icon` is a local glyph/shape intent, not an external package
dependency. A future component must supply a recognizable local icon with adjacent
status text; hide redundant decorative icons from assistive technology.
Badge labels supplement, never replace, full accepted scene wording. In particular,
FX-10 material-approved/delivery-pending stays distinct from material-approval-pending
even though both use the pending palette.

## Fidelity and behavior

| Tier | Effort | Token emphasis |
| --- | --- | --- |
| 1 | Promise/options, change/remediation, risk/graph, restoration, receipt/away | Editorial heading, hero padding, deliberate whitespace and focused lineage |
| 2 | Approval/materialization, evidence, stale/blocked/failed | Functional padding, exact stage labels, accessible controls; no decorative animation |
| 3 | Loading/applying/reconnect/recovery and layout permutations | Same readable/focus foundation; short progress treatment, no equal-polish requirement |

The scene tier and action count match the accepted journey, overriding a component's
general visual tier. At most **one** dominant action appears; working scenes may have
none. Secondary reject/back/inspect/mark-seen stay accessible. These counts and
fixture references are design coverage, not frontend workflow predicates.

CSS emits a desktop root plus a **<=48rem** narrow token override. It substitutes
the literal breakpoint into `@media`; CSS variables cannot be used as media-query
conditions. Narrow layouts stack cards, retain ordered lineage, allow per-file code
scrolling and use a full-width evidence drawer. Avoid fixed-height text so 200% zoom
can reflow. Tokens alone do not prove responsive or keyboard behavior.

Use `:focus-visible` with `--iti-focus-ring-width` (3px), solid
`--iti-color-focus`, and `--iti-focus-ring-offset` (3px). Keep a surface-colored
separation around filled controls and do not clip the outline. Retain a system
outline in forced-colors mode. Minimum target basis is 2.75rem (44px at a 16px root);
the quiet identity/evidence label may remain smaller inside its target.
Do not hide focus during loading or disabled-action explanation.

Reduced-motion CSS replaces both transition durations with **0ms**. Future
components must also disable smooth scrolling, pulsing and motion-only meaning.

## Validation and evidence

From the workspace root:

```powershell
python -B design\tests\validate_tokens.py --emit-css
python -B design\tests\validate_tokens.py
```

The first command writes only owned token CSS. The second checks CSS drift, runs
only UX-02-01 tests, and writes new evidence receipt/test output under
`.intent-to-impact\spikes\UX-02-01\LOCAL-08\`. The earlier V1 receipts/logs are not
overwritten. Their matching token/component/test source snapshots are retained under
`.intent-to-impact\spikes\UX-02-01\history\DEMO-CASE-CLAIMS-V1\`, preserving original
workspace-relative paths. Accepted V1 journey/IA and UX-01/UX-03 evidence stay untouched.
Drift tests use uniquely named files in the new LOCAL-08 evidence directory and
remove them in `finally`; they never alter the source CSS or use system temp paths.

All documented **normal text pairs meet >=4.5:1**, including large headings and
compact labels; focus/essential non-text pairs meet **>=3:1**. The receipt contains
the actual 28 WCAG sRGB contrast measurements, artifact/input hashes and test results.
Ratios are compared before rounding. CSS generation is byte-deterministic UTF-8/LF;
input order does not change output. Missing status/focus tokens, low contrast,
malformed types, duplicate IDs/refs, CSS drift and inconsistent scene semantics fail.

This verifies token values and design consistency, **not browser accessibility,
human approval, live proof or source-evidence authenticity**. Later accepted C/D
work must check actual focus/zoom/narrow rendering and agree the visual direction
with the stakeholder. Do not start MOCK-01/02 or production UI from this task.
