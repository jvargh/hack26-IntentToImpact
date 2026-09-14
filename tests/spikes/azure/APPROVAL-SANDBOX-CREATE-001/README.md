# Approved public sandbox bootstrap — APPROVAL-SANDBOX-CREATE-001

## Current execution result: blocked before creation

Read-only checks on **2026-09-13 00:14–00:16 UTC** found the inherited enforced
`MCAPSGovDeployPolicies` member `StorageAccount_PublicNetwork_Modify`. Its
`modify` action writes `publicNetworkAccess=Disabled`, contradicting the exact
approved `Enabled` setting. No at-scope policy exemption was returned.
**No RG/account creation command was executed; no actual baseline exists.**
The RG was still absent and the account name still available after diagnostics.

Provider-level validation and create-only what-if both returned exit 0; that
does **not** override the separately observed policy-modify conflict. No exclusion
tag, policy exemption, alternative private architecture or policy change was
applied. Governance/user resolution is required before this exact public design
can proceed. Do not rerun creation merely because validation/what-if passed.

Evidence summary:
`.intent-to-impact\spikes\SPK-03-01\APPROVAL-SANDBOX-CREATE-001-blocker.json`.
The immutable compiled candidate is under
`create-a001-20260913T001027370380Z\artifacts`; read-only target diagnostics are
under `create-a001-20260913T001619683818Z`. Earlier failed local/preflight
attempts are retained honestly, with `azureMutationAttempted=false`.

This isolated operator spike consumes the actual explicit creation approval and
canonical `fixtures\scenarios\DEMO-CASE-CLAIMS-V2.json` semantic hash
`sha256:a140b136272f077c82dcd1d38e8e2c13b0aa7aea192be2a80112ccc744213e9a`.
It does not edit those inputs, previous proposals, or SPK-04-01 compiler evidence.

The only infrastructure is the **new** `rg-intent-to-impact-demo` and its one
empty `iticlaimsv2a4f726` StorageV2 / Standard_LRS / Hot account in `eastus2`,
subscription `463a82d4-1896-4332-aeeb-618ee5a5aa93`, tenant
`5bb5fa45-2dcc-4310-bbc5-883021e9d84b`. An inline local-module deployment record
is ARM deployment metadata, not an additional workload resource.

Public networking is Enabled, required HTTPS true, anonymous access false, shared
key access false, TLS minimum 1.2, HNS false, network default Allow/bypass None.
No VM, PE, DNS, VNet, IP, identity, IAM assignment, container, data-plane operation
or key retrieval. **Drift, restoration and Azure cleanup/deletion are not approved
and are not implemented.** The $1 monitoring threshold is not a spending cap.

## Commands

Local preparation, real `az bicep build` twice and tests only:

```powershell
python -B .\tests\spikes\azure\APPROVAL-SANDBOX-CREATE-001\bootstrap.py
```

Execute the recorded approval **once**, only when the exact target remains absent:

```powershell
python -B .\tests\spikes\azure\APPROVAL-SANDBOX-CREATE-001\bootstrap.py --execute-approved
```

The runner always refuses an existing RG or unavailable/unknown account name.
It cannot adopt or update an existing sandbox. After success, do not rerun
creation: baseline refresh should be a separately scoped read-only operation.
No mutation is retried automatically. Failure/timeout after a creation attempt
triggers exact deployment/RG/account/inventory **reads only**, preserving partial
IDs and diagnostics without deleting anything.

The ordered checks are:

1. Exact approval/parameters/settings and actual canonical V2 semantic checksum.
2. Copy approval-specific source/parameters/scenario/approval into a new owned
   run directory; use the hash-verified existing Bicep compiler, no new modules.
3. Two actual `az bicep build --no-restore` runs, identical output hashes, strict
   compiled resource/property/scope inspection, and all local positive/negative
   tests. Unexpected CLI flags (seed/delete/role/extra resource) are rejected
   before the runner starts.
4. Capture actual Checkov availability. If installed, require a clean ARM scan.
   If genuinely absent, record **unavailable, not passed**, and the enterprise
   guidance's explicit self-review exception. No full security-audit claim.
   Public access/LRS override generic private/HA guidance by exact user consent.
5. Freeze artifact files read-only and SHA-256 hash them; check again immediately
   before creation. This prevents accidental changes, not hostile administrator
   tampering or all concurrent Azure races.
6. Isolate Azure CLI configuration in the owned run directory. Read only the
   selected existing profile/tenant and copy existing auth caches into that
   directory temporarily; never login or change the original default context.
   Credential copies are removed locally in `finally`; no cache content is
   printed or included in source artifacts. This local credential removal is
   unrelated to unapproved Azure resource deletion.
7. Real scoped subscription authentication, provider/API/location/SKU checks,
   inherited at-scope assigned policy reads, exact group/name absence checks,
   Provider-level target validation and create-only full-payload what-if.
   Potential policy auto-create/modify effects or unresolved policy effects
   block rather than silently adding resources or bypassing policy.
   Non-applicability is proven only from resource type or explicitly declared
   approved property values; unsupported conditions remain unknown and block
   potential modifying effects. This is not a complete Azure Policy evaluator.
8. Recheck approval/scenario/artifact hashes and actual absence immediately before
   the single subscription deployment. Capture real parent/nested deployment
   operations and actual resource IDs.
9. Fresh raw ARM **and** CLI reads, exact resource inventory, and empty management-
   plane container inventory. Normalize CLI `enableHttpsTrafficOnly` and ARM
   `supportsHttpsTrafficOnly` explicitly; reject missing/null/wrong-type or
   conflicting aliases. Record the four canonical V2 predicates with real
   provenance, never synthesized response values.

This follows the standalone enterprise Bicep build/preflight/deploy safeguards
within the user-mandated spike roots. It does **not** create an azd `.azure`
workflow, assert its `Validated` status, or manufacture product D10/D12 approvals.
The actual recorded user consent is the operator gate, not a UX/design gate.

## Evidence and limits

Every run persists under `.intent-to-impact\spikes\SPK-03-01\create-a001-*`:
immutable `artifacts\`, exact redacted command argv/streams/exit/timestamps,
tool versions, checksum receipts, target validation/what-if/policy results,
real creation operations, and `baseline.json` only after successful readback.
The receipt distinguishes expected/planned IDs from actual acknowledged IDs.
Streams are hashed **after redaction**. No fake deployment fallback exists.
On the Windows MSI installation the runner uses the launcher's identical native
`python.exe -IBm azure.cli` entrypoint, avoiding CMD interpretation of policy
filter parentheses. Both the replayable `az` argv and actual execution argv are
recorded; this is the real Azure CLI/Bicep, not a substitute compiler.

`baseline.json` uses the actual V2 scenario/promise/verifier/component identifiers.
It establishes only the scoped four-property configuration baseline at its
recorded observation time (V2 freshness limit: 300 seconds). It does not bind
canonical product materialization/design records; owner adapters may later bind
the real hashes/operation receipts. It is not private-network proof, complete
access-control assurance, drift detection/restoration, M0.5, or UI approval.

Standalone guard tests (compiled tests explicitly skip without real artifacts):

```powershell
python -B .\tests\spikes\azure\APPROVAL-SANDBOX-CREATE-001\test_bootstrap.py
```

To test the retained compiled output, set `SPK_BOOTSTRAP_ARTIFACTS` to its absolute
`artifacts` directory before invoking that test command. The bootstrap runner
sets it and runs all tests before any Azure mutation.
