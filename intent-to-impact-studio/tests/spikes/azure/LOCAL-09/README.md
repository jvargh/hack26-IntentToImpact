# LOCAL-09 NSP candidate — preparation only

The user selected one NSP, one empty profile and one **Enforced** storage
association, with no external inbound/outbound access rules. The old Enabled
approval is not reused. Final risk-acknowledged deployment confirmation is
**pending**; this runner has **no create/update/delete/IAM/seed capability**.

## Exact proposed scope

Subscription `463a82d4-1896-4332-aeeb-618ee5a5aa93`, tenant
`5bb5fa45-2dcc-4310-bbc5-883021e9d84b`, region `eastus2`:

1. New `rg-intent-to-impact-demo`.
2. New `nsp-iticlaims-local09` (proposed name).
3. Child `profile-closed` (proposed name), no access-rule resources.
4. Empty `iticlaimsv2a4f726`: StorageV2, Standard_LRS, Hot, non-HNS,
   `publicNetworkAccess=SecuredByPerimeter`, HTTPS required, anonymous/shared-key
   access false, minimum TLS 1.2, fallback `Deny` / `None`, empty IP/VNet rules.
5. Child `assoc-iticlaimsv2a4f726` (proposed name), **Enforced**, binding only that
   storage account to that profile.

No Key Vault/sample rules, VM, VNet, PE, DNS, VPN, public IP, identity, role,
container, data or log sink. Existing target resources cause a stop, not adoption.
Resource-group/subdeployment metadata is not additional workload infrastructure.

## Order and no exposure window

Microsoft's [new-resource guidance](https://learn.microsoft.com/en-us/azure/private-link/network-security-perimeter-transition#moving-new-resources-into-network-security-perimeter)
explicitly supports creation with `SecuredByPerimeter`: an unassociated resource
starts in lockdown, not Enabled. The candidate creates NSP -> profile -> storage
in lockdown -> Enforced association. No Disabled staging or second account update
is currently proposed; any provider rejection blocks rather than improvises a
different sequence. Resource-provider configuration synchronization must be
observed later before a baseline is complete.

## Reproduce without deploying

```powershell
python -B .\tests\spikes\azure\LOCAL-09\prepare.py --local-only
python -B .\tests\spikes\azure\LOCAL-09\prepare.py
```

The second command adds **read-only** context, registration/API/region/SKU,
permissions, exact absence, inherited policy, Provider validation and full
create-only what-if checks. It never deploys, even if they all pass.
Unknown policy write/deploy effects block; exclusions are proven only from exact
resource types/declared values. Potential policies that would deny/rewrite a
hypothetical later HTTPS=false change are reported without executing that change.

The command-capture mechanics are reused read-only from the historical bootstrap;
none of its constructor, auth-copy, V2 approval, deployment or baseline logic is
used. The native MSI `python.exe -IBm azure.cli` entrypoint is identical to
`az.cmd`; both argument vectors and real exits/times are recorded. Existing CLI
authentication is consumed in place with explicit subscription pins. No login,
default changes or credential copies are performed. Logging/temp/build paths
are owned; the global CLI defaults file hash is checked unchanged.

`evidence.py` retrieves bounded public Microsoft references and scoped metadata.
MCP discovery reported no connected client, so official documentation and CLI
fallback are explicit. The original compiler emitted genuine missing-type warnings; `toolchain.json`
therefore pins the discovered current release v0.47.16. Restore it only into
LOCAL-09's owned tool cache with `python -B
.\tests\spikes\azure\LOCAL-09\restore_compiler.py`; no global compiler/auth
configuration or historical binaries are changed. Checkov is attempted: a genuinely missing tool is labelled
unavailable, with the enterprise guidance's exact-scope self-review exception,
**not a passed scan**.

## Immutable evidence and tests

Each run writes only
`.intent-to-impact\spikes\SPK-03-01\LOCAL-09\<run>\`: exact source/plan/decision
snapshots, two actual compiled outputs, SHA-256 manifest, redacted command
streams, real policy/registration/permission responses, validation/what-if and
pricing results. Files are made read-only and hashes rechecked. This guards
accidental changes, not a hostile administrator. Before any future deployment,
fresh approval must bind the exact compiled/parameter/decision hashes and five
planned IDs; stale or old approvals are rejected.

```powershell
python -B .\tests\spikes\azure\LOCAL-09\test_local09.py
```

The preparation runner sets `SPK_LOCAL09_ARTIFACTS` to test real compiler output.
Standalone runs explicitly skip compiled tests unless that variable points to a
retained artifact directory. Positive observation objects in unit tests are
**fixtures**, never Azure proof. `required-observation-shape.json` documents the
future contract-owner seam, including provider-side synchronization. The profile
GET API exposes versions, not provisioningState; no such field is fabricated.

## Costs, risks and final confirmation

NSP-specific pricing is **unconfirmed**, not zero: the attempted dedicated
Microsoft price URL returned 404 and current retail Perimeter searches returned
no meter. The storage price call initially returned 429; bounded retries and
their actual outcomes are recorded. The absence of a meter is not a promise of
free service. An all-in total or spending cap is not asserted. Resolve current
NSP charges or obtain explicit informed acceptance of the price uncertainty
before deployment; empty storage usage does not guarantee a zero bill.

Enforced/no external rules intentionally restricts external data access, while
management-API observations remain the proposed verification mechanism. No
successful data-plane blocking test has occurred. Partial future creation may
leave billable resources; there is no automatic deletion permission or
rollback-to-Enabled path. Failed association/sync leaves storage locked down and
baseline incomplete. Drift and cleanup each need separate approval.

**Final request, once technical and pricing blockers are resolved:** confirm the
five proposed names/IDs, exact candidate hashes, known costs/uncertainties,
lockdown/no-data-access behavior and partial-creation risks, then explicitly
authorize only their creation. LOCAL-09 confirms topology, not that final
deployment gate. `.azure/infrastructure-plan.json` remains `draft` for that reason.

V3 publication is pending A-contracts; no canonical V3 hash, D12/product approval,
baseline success, M0.5 or UX gate approval is created here. V1/V2 artifacts and the
previous proposal/bootstrap remain immutable historical evidence.
