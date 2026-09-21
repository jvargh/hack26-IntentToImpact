# Superseded: disposable CP-01 private-path sandbox

**HISTORICAL ONLY.** The user subsequently directed a public-endpoint-only
sandbox. This private network/VM design, its approval request, cost estimate and
Compute quota gaps are **not current requirements**. See `approval-request.md`
and `proposed-sandbox.json` for the replacement. The findings below are retained,
not approved or deployed.

**Proposal only — approval required. SPK-03-01 live proof remains blocked.**
No Azure resource, role, script execution, deployment or drift mutation was performed.
This is a spike prerequisite, not a product schema or new planning framework.

## Proposed scope

- Subscription: `463a82d4-1896-4332-aeeb-618ee5a5aa93`.
- New RG: `rg-intent-to-impact-demo`. The orchestrator supplied an actual
  `ResourceGroupNotFound` result; this proposal did not requery it.
- **East US 2 is proposed, not user-confirmed.** All other resource names and IDs
  are unassigned. Nothing below is represented as an existing resource.
- Maximum requested lifetime: **two hours**, with an operator present for cleanup.

| Resource | Proposed minimum and reason |
|---|---|
| Storage + empty private container | StorageV2, Standard_LRS, Hot, non-HNS; no real data or blob writes |
| Private network | One isolated VNet, two /28 private subnets within proposed `10.244.80.0/27`; no peering |
| Blob private endpoint | One `blob` binding and its managed NIC, actual connection must be Approved |
| Private DNS | Dedicated `privatelink.blob.core.windows.net`, VNet link and PE zone group/A record |
| Disposable verifier | One B2ts_v2 Linux VM, 2 burstable vCPUs/1 GiB; private NIC + NSG; one 32-GiB E4 LRS standard SSD |
| Identity and evidence | VM system-assigned identity, one **container-scoped Storage Blob Data Reader** assignment; managed boot diagnostics |

**Zero public-IP resources, no NAT, VPN, Bastion, SSH ingress or general guest
internet.** Explicit `defaultOutboundAccess=false`; do not rely on legacy default
outbound connectivity. Storage public networking, anonymous blobs and shared-key
authorization remain disabled; HTTPS/TLS 1.2 and deny-all network ACLs are required.
LRS is a disposable-test choice, not a production recovery claim.

## How actual private-path proof would work

After separate approval, a pinned standard Ubuntu 24.04 LTS Gen2 image would run
only reviewed cloud-init custom data: no extension or package/script downloads.
A small Python-stdlib probe runs every 30 seconds for at most two hours:

1. Record actual VM/guest identity and timestamp; resolve the **normal** account
   hostname using linked Azure private DNS, not a hosts-file override.
2. Match DNS and the actual TLS peer address to the deployed PE NIC private IP;
   validate hostname/certificate and record the negotiated TLS version.
3. Acquire an IMDS managed-identity token for `https://storage.azure.com/` in memory.
   Perform authenticated **List Blobs** on the exact empty container, expecting
   HTTP 200 and an empty enumeration. Record request IDs, method, time and body
   hash, never credentials or customer data.
4. Emit compact nonsecret JSON to the VM serial device. The operator retrieves
   managed boot diagnostics using `az vm boot-diagnostics get-boot-log`, scoped
   explicitly to the subscription/RG/actual VM. Do not export diagnostic SAS URIs.
5. Correlate fresh guest records with the real deployment/script hash and fresh
   ARM storage properties, Approved PE binding, NIC, zone and VNet link.

Azure platform DNS/WireServer (`168.63.129.16`) and local IMDS
(`169.254.169.254`) must remain reachable; neither is a public IP allocated to
this verifier. The guest needs no internet egress to contact these platform
services or its storage private endpoint.

**Why not Run Command?** Microsoft documents outbound 443 to Azure public
addresses for its results. Assuming it works without explicit outbound
connectivity would hide a prerequisite. Managed boot diagnostics avoids that
guest result-upload path. However, the exact cloud-init/serial collection
combination has **not been run**: image tooling, role propagation, serial-log
freshness and collection permissions remain acceptance gates. Missing evidence
means **unknown**, never verified.

## Current price evidence — USD, public retail, not a quote

Retrieved **2026-09-12 22:33–22:35 UTC** from the Microsoft Retail Prices API
(`2023-01-01-preview`); exact primary meter IDs, filters, timestamps and raw
response hashes are in `proposed-sandbox.json` and the evidence manifests.

| Item | Retrieved price |
|---|---:|
| B2ts_v2 Linux, East US 2 | $0.0104/hour |
| One E4 LRS OS disk | $2.40/month |
| One Private Endpoint, Global commercial meter | $0.01/hour; partial hours charged as full hours |
| One private DNS zone, first 25 tier | $0.50/month |
| Private DNS queries | $0.40/million |
| Hot LRS blob capacity / list operations | $0.0184/GB-month / $0.05 per 10,000 |

Two hours of VM + PE: **$0.0408**. Reserving a **full month** of disk and DNS
instead of assuming proration gives a conservative fixed allowance of
**$2.9408**, before transactions/traffic/tax. At 480 probes, list operations
would add $0.0024 and 480 DNS queries $0.000192; actual counts may differ.
Leaving everything running for 730 hours gives **$17.792 fixed subtotal**,
before variable charges. Deallocation alone does not stop disk/PE/DNS billing.

Propose a **$5 monitored stop/escalation threshold**, **not an enforced budget
cap**. Private Link data processing, SSD transactions, tax, mandatory paid
policies and subscription discounts are excluded; no guaranteed total invoice.
Managed boot diagnostic blobs are currently documented as unbilled.

## Permissions, drift safety and cleanup

The operator needs permission to create the one RG and its listed resources,
approve its blob PE, retrieve scoped deployment/serial evidence, and delete
only this run's resources. A separate authorized RBAC administrator must grant
and remove the one container-scoped reader assignment; resource Contributor
alone is insufficient. No subscription Owner grant, storage keys, broad data
roles or provider registration is requested.

**Drift is a separate, later approval.** Only after complete baseline proof and
an empty-container check, a present operator may change the actual new account's
`publicNetworkAccess: Disabled -> Enabled`, then restore `Disabled`, requesting
no more than 120 seconds. **Deny-all ACLs, no IP/VNet allow rules, anonymous=false,
shared-key=false, TLS and the PE remain unchanged.** This proves a configuration
mismatch, not successful anonymous/public data access. Save/re-read exact scope
and protected fields, detect conflicts, measure actual observation latency and
arm the same-property rollback before seeding. An operator must restore on
errors or lost automation; no unattended rollback guarantee is claimed.
Fresh post-restoration private-path proof is required.

Cleanup needs explicit authorization: export nonsecret evidence, remove the
exact role assignment, delete the VM/disk/NIC, PE and children, dedicated DNS,
empty storage, NSG and VNet. Delete the RG only if its fresh inventory matches
the actual ownership manifest; otherwise stop on unowned resources. Confirm
no orphan disks, NICs, endpoints, DNS or role assignments. A stopped probe
does **not** deallocate or delete anything.

## Required approvals and unresolved inputs

**Requested now:** “Approve the proposed East US 2, zero-public-IP sandbox design
for preparation and review of exact IaC and the fixed verifier only. Do not
deploy yet.”

**Before provisioning:** separately approve final resource names, CIDRs, image
version, script hashes, operator public key, listed resource/RBAC/guest-execution
operations, the $5 monitored threshold, two-hour lifetime and scoped cleanup.
**After a passing live baseline:** separately approve the exact guarded drift
and rollback. All approvals are currently absent.

Current subscription SKU eligibility, two-vCPU regional/family headroom,
provider registration and policy are **unconfirmed**: Compute MCP returned
command discovery, not quota/SKU results. Resolve these read-only before final
IaC approval. Pin the image and confirm Python/CA/cloud-init support and OS-disk
fit. Do not promote retail pricing or generic documentation to capacity proof.

If 1 GiB is inadequate, B2ls_v2 (4 GiB) currently lists at $0.0416/hour, subject
to renewed quota/size/budget approval. A NAT + Run Command alternative would add
a **public egress IP**, violate this zero-public-IP proposal, and require a
separate proposal/approval. An existing private runner is another alternative
only if the operator actually supplies connectivity and authorization.

### Microsoft references

- [Storage Private Endpoints](https://learn.microsoft.com/en-us/azure/storage/common/storage-private-endpoints)
  and [Private Endpoint DNS](https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-dns).
- [Cloud-init support](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/using-cloud-init),
  [managed boot diagnostics](https://learn.microsoft.com/en-us/azure/virtual-machines/boot-diagnostics),
  and [boot-log CLI](https://learn.microsoft.com/en-us/cli/azure/vm/boot-diagnostics).
- [Platform address](https://learn.microsoft.com/en-us/azure/virtual-network/what-is-ip-address-168-63-129-16),
  [IMDS tokens](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/how-to-use-vm-token),
  and [List Blobs](https://learn.microsoft.com/en-us/rest/api/storageservices/list-blobs).
- [Bsv2 sizes](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/bsv2-series),
  [default outbound access](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/default-outbound-access),
  and [Run Command restrictions](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/run-command).
- [Retail Prices API](https://prices.azure.com/api/retail/prices?api-version=2023-01-01-preview),
  [DNS billing](https://azure.microsoft.com/en-us/pricing/details/dns/),
  [Private Link billing](https://azure.microsoft.com/en-us/pricing/details/private-link/).

## Local validation only

```powershell
python -B .\tests\spikes\azure\test_proposal.py
```

This checks the proposal and persisted public evidence, including unsafe
negative variants; it cannot provision or verify Azure. It writes a local
validation receipt only beneath `.intent-to-impact\spikes\SPK-03-01\`.
To refresh only public references, use `python -B
.\tests\spikes\azure\collect_public_evidence.py`; a new timestamped snapshot is
created, and the proposal must be reviewed before changing its pinned references.
