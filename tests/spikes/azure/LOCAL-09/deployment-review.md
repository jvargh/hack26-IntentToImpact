# LOCAL-09 deployment review — final confirmation pending

**No Azure resource was created or updated.** Technical checks passed; NSP
pricing requires clarification or explicit informed acceptance. Final
risk-acknowledged consent is absent. The old Enabled approval cannot authorize
this candidate; plan status remains **draft**.

## Exact future scope

Subscription `463a82d4-1896-4332-aeeb-618ee5a5aa93`, tenant
`5bb5fa45-2dcc-4310-bbc5-883021e9d84b`, `eastus2`:

| Planned resource | Name |
|---|---|
| New RG | `rg-intent-to-impact-demo` |
| Empty StorageV2 / Standard_LRS / Hot, non-HNS | `iticlaimsv2a4f726` |
| NSP | `nsp-iticlaims-local09` |
| Empty profile | `profile-closed` |
| Enforced storage association | `assoc-iticlaimsv2a4f726` |

Storage starts **SecuredByPerimeter**, HTTPS=true, anonymous/shared-key=false,
TLS1_2, fallback Deny/None. Order: RG → NSP → profile → locked-down storage →
Enforced association. Official lockdown-on-create guidance and Provider
validation support direct creation; no Disabled/Enabled staging or subsequent
account update is proposed. No rules or additional resources.

## Actual checks

- **PASS:** Bicep **0.47.16**, two builds, exit **0**, equal hashes, no warnings.
  Scoped manifest-based upgrade followed real 0.34.44 missing-type warnings.
- **PASS:** exact resource/property/order and approval/observation guard tests.
- **PASS:** actual Network/Storage registration, API/region support and action
  permissions; RG absent and account name available at preflight.
- **PASS:** Provider validation exit **0**; full what-if exit **0**, five exact
  Creates and no changes to existing resources.
- **PASS, bounded review:** 12 inherited assignments / 197 definitions.
  The original guard warning was a VM-only unconditional Deny override, resolved
  by local re-review of hashed real responses—not a policy change. No unresolved
  modifying effects or policy-created extras remained for this candidate.
- **EXCEPTION, not passed:** Checkov is absent. Exact-scope secure-configuration
  self-review is recorded under the enterprise guidance's unavailable-tool exception.
- **PASS:** files under `infra`; prior approvals/proposals/spikes are untouched.
  No actual deployment, baseline, product/UX approval or V3 binding is claimed.

Target evidence: `LOCAL-09\candidate-20260913T012617540781Z`.
Policy re-review: `LOCAL-09\policy-snapshot-review-20260913T014234577036Z`.
Both are under `.intent-to-impact\spikes\SPK-03-01\`.

Compiled SHA-256:
`6d4cbc93c7b71b977219e1a40e5ed78cd4a8a06c6c7536895a2fbe82e119db98`.
Parameters:
`5e3e6af85bb57f8b994042aa80dea5cc168f329d788e477ec250d72e8dcb4803`.
The candidate manifest also binds LOCAL-09's decision hash and planned IDs.

## Cost, permission and partial-creation risks

Current USD storage retail: **$0.0184/GB-month**, **$0.004/10,000 reads**,
**$0.05/10,000 list/create-container operations**. Planned data/operations are
zero, not a free-bill guarantee. **NSP price and total are unknown**: the official
price-page lookup returned 404 and targeted retail queries found no NSP meter.
No spending cap or paid monitoring is configured.

Actual scoped permissions allowed the required writes, Storage join-perimeter
action and NSP operation-status reads; no permission was granted. Recheck
permission, policy and target absence immediately before any future apply.
No enforced HTTPS-drift blocker was identified in this snapshot's bounded
counterfactual review; no drift was tested or authorized.

Enforced/no rules restricts external data access by intent, but no data-plane
blocking test has run. Association/provider-sync failures leave baseline unknown.
Partial creation could leave resources and charges: **no automatic rollback or
cleanup is authorized**. Never restore Enabled or add a rule to troubleshoot.

**Final decision requested:** resolve NSP pricing or explicitly accept its
uncertainty; acknowledge lockdown, partial-creation/cost risks and the scanner
exception; then authorize only the five exact planned resources bound to the
current candidate hashes. Until then, stop. Drift/cleanup need separate consent.
A-contracts must publish V3 before product integration; use
`required-observation-shape.json`, not old V2 proof.
