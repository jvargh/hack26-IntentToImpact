# CURRENT V2 design handoff — LOCAL-08

Start at **`design\components\CURRENT.v2.json`**. This is the current business-wording
handoff for **DEMO-CASE-CLAIMS-V2, scenario 2.0.0**, with design/schema envelopes
1.0.0 and design revision 2.0.0. Historical V1 files remain unchanged.

The wording-only blocker is removed. A/C can consume this design for current mock
preparation; **canonical projection/complete fixture validation remains pending A**,
not silently replaced by a UX-authored schema. **GATE-UX01 remains pending human
visual/product review.** No prototype, payloads, live proof or UI is implemented.

## Read these current files

| Current artifact | Use |
| --- | --- |
| `hero-journey.v2.json` | Five moments, all 18 interactions, 28 scene/variant references, CP-01 scenario display reference |
| `..\information-architecture\inventory.v2.json` | Same routes and 18 component IDs; current scenario and HTTPS graph property |
| `..\components\component-state-contract.v2.json` | Current prop/state/fixture references and one-action hierarchy |
| `..\tokens\tokens.v2-manifest.json` | Current manifest reusing exact accepted neutral token values and CSS |
| `..\decisions\UXD-003.json` | Actual user-directed technical revision, pending review; no fabricated approval |

Old `README.md`, `.v1.json` files, UXD-001/002 and previous receipts retain their
historical context. The current token manifest consumes only the immutable value/
status/contrast sections from `tokens.v1.json` and its unchanged CSS, **not that
source's old scenario-alignment blocker**. Both future mock and production share
those values; no palette, typography, motion or density redesign occurred.

## Same five moments, current public-endpoint meaning

**Promise → Decision → Implementation Prepared / Approved / Materialized →
Promise At Risk → Proof.**

The customer outcome remains protecting sensitive claims and meeting Contoso's
seasonal deadline. Normal explicit in-product promise confirmation remains required.
RPO begins null/unconfirmed; 15 minutes is still the authored answer, not automatic
live confirmation. The A/B recovery-design rejection oracle and synthetic USD
6,000 / 7,200 estimates under the USD 8,000 limit are unchanged. No savings are
inferred from comparing an ineligible option with an eligible one.

**CP-01 is bounded configuration assurance**, not private connectivity or complete
access-control proof:

| Property | Desired V2 configuration | Proposed seed | Restoration |
| --- | --- | --- | --- |
| `publicNetworkAccess` | `Enabled` | Unchanged | `Enabled` |
| `supportsHttpsTrafficOnly` | `true` | `false` | `true` |
| `allowBlobPublicAccess` | `false` | Unchanged | `false` |
| `minimumTlsVersion` | `TLS1_2` | Unchanged | `TLS1_2` |

The graph focuses the supplied **`supportsHttpsTrafficOnly`** finding and exact
broken edge. **Public network access Enabled is not a V2 breach.** The customer
impact is that HTTPS is no longer required, not a claim that documents were
accessed. Labels use **Protected Claims / HTTPS**, with real status/limitations
from the supplied projection.

Only a public Storage endpoint is required. No private endpoint/DNS, VNet/VPN,
verifier VM or standalone Public IP resource is required. Resource IDs and scope
remain operator-bound; no concrete infrastructure is fabricated.

**All deployment, seed and restoration mutations are still unapproved.** The
seed is only a separately authorized proposal on an empty/synthetic sandbox; no
real data goes over HTTP. A prohibited seed blocks rather than bypassing policy.
Restore through the exact approved V2 desired-state hash and verify all four
configuration predicates afresh. Reuse unchanged Bicep where appropriate.
Local materialization remains local bytes, not Azure deployment or verification.
Other promises without proof remain unknown; there is no mandatory 7/8 or 8/8 count.
A new V2 product run needs its own confirmations/approvals; V1 proof is not rebound.

## Stable interaction and fidelity coverage

| IDs | Interaction coverage |
| --- | --- |
| UX-I-01..04 | Promise confirmation; consequential RPO; rejected/eligible comparison; explicit design approval and progress |
| UX-I-05..07 | Prepared diff/checks; separate delivery approval; applying/materialized and separate Azure baseline |
| UX-I-08..10 | Proactive HTTPS risk with graph/list parity; away summary; split product/operator attention |
| UX-I-11..13 | Material approval → delivery approval → applying; separate unapproved operator restoration; pending/fresh scoped proof |
| UX-I-14..16 | Three-question receipt; evidence provenance/limitations; empty/loading |
| UX-I-17..18 | Stale/blocked/failed/retry and reconnect; keyboard/narrow/200%-zoom/reduced-motion coverage |

All FX-00..19 and named correction variants remain. Tier 1 customer hierarchy and
focused risk are unchanged; Tier 2 approvals/materialization/evidence stay clear;
Tier 3 progress/recovery stays functional. At most one server-issued action is
dominant. No client eligibility, approval, coverage or verification engine exists.

## Validation and separate evidence

```powershell
python -B design\tests\validate_local08.py
```

The new runner reuses the existing JSON readers, token contrast/CSS routines and
U04 record validator without modifying them. Its U04 specialization changes only
the historical schema's scenario/task constant selectors for UXD-003; record shape,
review completeness and authenticity limits are preserved. No domain schema/types
are authored. New tests check V2 semantics directly, not by relabeling a V1 input.

Receipts and logs are written only under:

- `.intent-to-impact\spikes\UX-01-01\LOCAL-08\`
- `.intent-to-impact\spikes\UX-02-01\V2\`

Evidence includes current hashes, contrast, negative tests, all 34 pre-existing
source/evidence preservation checks and explicit pending gates. The preservation
manifest is a fixed pre-edit oracle, not regenerated to excuse a change.
Actual browser accessibility, technical acceptance and human gate acceptance remain
separate. Stop here: do not start UI or cloud work.
