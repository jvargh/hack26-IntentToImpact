# Studio infrastructure catalog

`bundle.build_bundle(stored_result, option_id, server_output_root)` validates the
shared `studio.schema.json` and source/requirement/component relationships before
rendering this closed catalog. Schema and reference integrity apply to the whole
stored result; deployment-topology restrictions apply only to the selected option.
An unselected option's self-connection or duplicate directed pair does not block
the selected build. Selected self-connections and duplicate directed pairs remain
blocked with option/edge IDs and correction guidance: connect distinct components
and consolidate parallel logical operations into one edge per directed pair.
The stored result is never rewritten or silently deduplicated.
Labels, responsibilities and connection labels
are data in the manifest, never Bicep, commands, filenames or module references.
Only the server supplies the output root. Every attempt has a new UUID directory.
The live service uses `.intent-to-impact\studio\runs\builds`; standalone local
builds may use `.intent-to-impact\studio\builds`, and tests use the specifically
allowlisted `STUDIO-BUNDLE` evidence subtree. Unrelated paths remain rejected.
Canonical model service tokens (`AppService`, `Functions`, `Storage`, `ServiceBus`,
`KeyVault`, `Client`) map to their same-service catalog aliases, not arbitrary services.

## Supported deployment contracts

> **WARNING — queue direction, not prose, determines permissions.** App Service
> and Functions host → queue grants only **Data Sender**; queue → host grants only
> **Data Receiver**. A label such as “Consume queue messages; abandon/dead-letter
> on failure” on a host → queue edge does **not** grant receive permission.
> Correct that edge's direction before deployment; a host that both produces and
> consumes needs two opposite directed edges. Compilation does not verify handlers,
> retries or dead-letter behavior, and no worker implementation is generated or
> verified. Implement and test application behavior separately. This warning also
> appears in the BuildResult and manifest limitations.

* App Service: Linux B1 dedicated plan, Node 22 LTS, user-assigned identity.
* Functions: Linux B1 dedicated plan (not Consumption/Flex), Python 3.12,
  Functions v4, always-on, package deployment, dedicated identity-based host
  storage. No Azure Files content share or connection-string storage keys.
* Storage: StorageV2 Standard LRS, private `data` blob container, OAuth only.
* Service Bus: Standard namespace with one `work` queue; Entra-only data access.
* Key Vault: Standard, RBAC, soft delete and purge protection; no secrets created.
* Client and external HTTPS API: existing integrations, not deployed resources.

Connection contracts are explicit, rather than interpreting free-text labels as
permissions: app → blob means container-scoped Blob Data Contributor; app → queue
means queue-scoped Data Sender; queue → app means queue-scoped Data Receiver;
app → vault means vault-scoped Secrets User. External → app supplies an explicitly
required existing same-tenant Entra caller-client-ID parameter and adds it to the
target's Easy Auth allowlist; authentication remains required and anonymous requests
return 401. Provider-native signed webhooks are not generated: if the provider cannot
obtain an Entra token, an authenticated adapter is a deployment prerequisite.
An inbound-only external integration does not require an unused outbound URL.
App → app supplies endpoint/audience
and allows the calling managed identity in Easy Auth. Client → app needs the
existing Entra application. App → external HTTPS API requires an existing URL and
application-side authentication. Other edges, disconnected nodes, dependency
cycles, unknown service aliases or zero deployable components are blocked.

All app connections require application code that reads the generated settings
and uses Azure Identity. Queue consumers additionally need a supported Service
Bus extension/SDK and an implemented handler. Function host storage receives
account-scoped Blob Data Owner and Queue Data Contributor; it does NOT grant
subscription/resource-group Contributor. Event Grid, Durable Functions and
storage-trigger workflows are not implemented and must not be represented as
generic blob connections. Dedicated hosting intentionally avoids Azure Files'
shared-key requirement.

The supplied parameter file intentionally omits required existing Entra client ID
and external API URLs: supply those deployment parameters after external setup;
no fake client IDs, credentials or application binaries are fabricated.
Identity-only Easy Auth is configured for bearer-token validation, not a
secret-backed interactive sign-in flow. The existing API registration must expose
the `api://<entraApplicationClientId>` audience and request access-token version 2;
configure the browser's delegated scope and consent separately. External API
URLs must be HTTPS. The current endpoint catalog targets Azure public cloud.

The deployment scope is a resource group. `location` defaults to
`resourceGroup().location`; there is no fixed sandbox or `eastus2` default.
Select an approved target resource group/region that satisfies business and
data-residency requirements, or explicitly supply an approved `location`
parameter. The model contract has no validated region field. Compilation does
not validate regional availability, data residency or compliance, including EU
requirements. Do not assume the existing development sandbox is an approved
deployment target.

## Validation and provenance

Pinned official AVM modules are used for plan, identity and vault.
The catalog records why key-free site/Storage/Service Bus templates are explicit:
the inspected Storage/Service Bus modules unconditionally evaluate key outputs,
and actual site-module compilation retained conditional key-retrieval branches.
Local templates and catalog hashes, the shared-schema hash, result/input hashes,
source and requirement mappings, model receipt hashes, compiler command/version,
exit and diagnostics are packaged. Module references are server constants;
restoration uses a package-specific cache and no Azure login. The local compiler
configuration's absolute cache path is recorded in validation.json. The
downloadable bicepconfig.json omits that machine-specific setting so it is portable.

`compiled` means actual Bicep process exit 0 and a parsed ARM resource template,
not successful deployment or production readiness. No Azure deployment, what-if,
policy/quota/RBAC/region/availability check, cost forecast or workload test runs.
Public endpoints remain enabled but authenticated; a target policy denying
public access (including the user's known public-network policy) can reject them.
No private-network compliance is claimed. Deploying creates billable resources.
