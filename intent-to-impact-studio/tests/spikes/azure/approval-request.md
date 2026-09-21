# Revised approval request: empty public-endpoint storage sandbox

**Approval required. No deployment or seed authorized or performed.**

The user directed “use public IP where needed. no private needed.” This replaces
the private-network proposal. **One StorageV2 account's built-in public endpoint
needs no standalone public IP or verifier VM.**

## Minimal proposed resources and settings

- Subscription: `463a82d4-1896-4332-aeeb-618ee5a5aa93`.
- New RG: `rg-intent-to-impact-demo`; its absence is reported by the orchestrator's
  actual `az group show` result, not independently rechecked here.
- **East US 2 remains proposed**, not confirmed. Account name/ID are unassigned.
- Only **one empty Standard_LRS, Hot, non-HNS StorageV2 account** in that RG.
  No application, containers, blobs, real data or data-plane operations.

| Desired property | Value |
|---|---|
| `publicNetworkAccess` | `Enabled` |
| `supportsHttpsTrafficOnly` | `true` |
| `allowBlobPublicAccess` | `false` — never enable it |
| `minimumTlsVersion` | `TLS1_2` |
| `allowSharedKeyAccess` | `false` as additional proposed hardening |
| Network ACL | `defaultAction=Allow`, `bypass=None`; public reachability is intentional, anonymous authorization is not |

**No VNet, Private Endpoint, private DNS, VPN, verifier VM, public-IP resource,
NAT, disk, managed identity or role assignment.** Compute quota/image/private-path
gaps from the old proposal are no longer prerequisites.

## Explicit promise/verifier change

The proposed runtime promise is now **HTTPS-only and anonymous-blob-access
configuration**, observed through scoped management-plane account reads.
It is **not private connectivity**, proof of every HTTP/anonymous-access behavior,
or coverage of all attacks. The original private-network **CP-01 is not passed**.
The orchestrator will record the canonical scenario/promise change; no new
canonical promise ID is invented here.

After a separately approved real deployment, record actual deployment/account
IDs, artifact hash, empty owned inventory, timestamps and fresh observed
`supportsHttpsTrafficOnly=true`, `allowBlobPublicAccess=false`,
`publicNetworkAccess=Enabled`, and `minimumTlsVersion=TLS1_2`. Missing/null/stale
properties or failed reads mean **unknown**. Use only an explicitly scoped
`az storage account show`; do not retrieve keys or execute data-plane requests.

## Separate safe seed and rollback

After complete baseline proof, obtain **separate explicit operator consent**
to set only `supportsHttpsTrafficOnly: true -> false -> true` on that actual
empty account, requesting **at most 120 seconds**. The present operator must
have the rollback ready before seeding.

**Anonymous blob access stays false throughout.** Keep public endpoint enabled,
TLS minimum, shared-key prohibition and other settings unchanged. Do not send
HTTP requests, credentials or real data. Observe the actual false property as a
configuration mismatch, then restore true in a guarded operator finally path
and collect fresh actual properties. Re-read scope/protected fields; stop on
unexpected concurrent edits. Restore immediately on errors or lost automation.
No unattended rollback guarantee is claimed.

## Current cost and scope

Public Microsoft Retail Prices API evidence retrieved **2026-09-12
22:49:32–22:49:47 UTC**, East US 2, USD primary Consumption meters:

| Meter | Current retail rate |
|---|---:|
| Hot LRS data | $0.0184/GB-month |
| Hot reads | $0.004/10,000 |
| List/create-container operations | $0.05/10,000 |

With **zero stored data and zero planned data-plane reads/lists**, these listed
usage assumptions total **$0.00**. This is **not a guaranteed free bill**:
actual usage/metadata/transactions, mandated paid policies, tax, support and
residual charges are unmeasured/excluded. ARM property reads are not Blob
data-plane reads. There are no VM/PE/DNS/public-IP infrastructure charges.
Exact meter IDs, retrieval URLs/times and raw-response hashes are pinned in
`proposed-sandbox.json` and its evidence manifest.

Propose a **$1 operator monitoring/stop threshold** and **two-hour lifetime**,
neither an enforced spending cap nor automated cleanup.

## Approval and permissions requested

**Now:** confirm East US 2 and authorize preparation/review of exact public-only
IaC, not deployment. Before creation, separately approve the available account
name, artifact hash, these settings, creation of only the named new RG/account,
$1 monitoring threshold, two-hour lifetime and scoped cleanup.

The operator needs only scoped RG/account/deployment create/read/update/delete
permissions, including account write for the later separately approved seed.
No new role assignments, broad Owner grant, keys or data access are requested.
Check storage provider/region availability and policy read-only; provider
registration is not authorized.

For separately approved cleanup: restore HTTPS-only, export nonsecret proof,
verify the actual account is still owned and empty, delete only it, and delete
the RG only if a fresh inventory contains no unowned resources. Stop if
unexpected data/resources appear; confirm deletion and check residual charges.

## Historical findings and validation

`superseded-private-proposed-sandbox.json` and
`superseded-private-approval-request.md` preserve the discarded private design;
its evidence and metadata gaps are historical, not required components.
**SPK-04-01 is unchanged historical compiler proof**, not the current desired
deployment template: its disabled-public-access fixture must not be deployed
as this new public-only design.

```powershell
python -B .\tests\spikes\azure\test_proposal.py
```

Local tests check the public-only shape, unsafe negative variants, supersession
and evidence provenance. They cannot provision Azure or prove runtime status.

Microsoft references:
[HTTPS-only](https://learn.microsoft.com/en-us/azure/storage/common/storage-require-secure-transfer),
[anonymous access](https://learn.microsoft.com/en-us/azure/storage/blobs/anonymous-read-access-configure),
[minimum TLS](https://learn.microsoft.com/en-us/azure/storage/common/transport-layer-security-configure-minimum-version),
[storage networking](https://learn.microsoft.com/en-us/azure/storage/common/storage-network-security),
[account properties](https://learn.microsoft.com/en-us/rest/api/storagerp/storage-accounts/get-properties),
[Blob pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/).
