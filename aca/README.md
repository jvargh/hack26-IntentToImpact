# Intent to Impact on Azure Container Apps

**Deployed judge demo:** <https://intent2impact-hack26.yellowmeadow-9b9c790a.eastus2.azurecontainerapps.io/>

**Current runtime status:** intentionally stopped at the user's request after
verification. The app, image, NFS data and deployment configuration are retained.
Start the container app when judges need access. A stopped app does not stop
registry, storage or other retained-resource charges.

**Verified 17 September 2026:** no-sign-in Load Example -> Generate, both scripted
revision actions, real Linux Bicep compilation, eight-file ZIP hashes, visitor
history isolation and saved-run/package recovery after container restart all
passed. No Foundry model calls were made in this verification.

This directory containerizes the **existing studio**, not a model-generated
customer workload. It retains the React interface, synthesis/assurance pipeline,
approval records, history, Bicep compilation, downloads and manual deployment
handoff. Existing localhost mode remains the default outside hosted configuration.

## Judge demo: no Foundry usage

ACA now defaults to `STUDIO_MODEL_MODE=simulated`. This is an explicitly labeled
simulation, not a fallback when a real model fails. The simulator and generated
example input live in this directory. Local `Run-LiveStudio.ps1` continues to
use the real Foundry model and its normal consent flow.

1. Open the ACA URL.
2. Click **Load example inputs**.
3. Click **Generate architecture**; no Foundry-processing consent is required.
4. Explore both alternatives, blocks, source links and nine scripted findings.
5. Use **Request recommended change** or **Challenge finding** and approve the
   scripted demonstration. The entered instruction is recorded, not interpreted
   by AI; the returned changes are authored examples.
6. Generate/regenerate a package and download it. Bicep compilation is real,
   while the manifest and README clearly identify simulated design input.
7. Reopen the simulated run in history.

Custom prompts/documents are not supported in this mode; altered example sources
are rejected with guidance to reload the example. Editing a project title is
allowed. Nothing is sent to Foundry, no model credentials are acquired, and
simulation records cannot be labeled as live response receipts.

The ACA identity's unused Foundry inference grant was removed for this demo.
The infrastructure template only creates that grant when live mode is explicitly
selected. Registry image-pull access is retained; local Azure CLI access is unchanged.

This eliminates **model inference charges**, not ACA/registry/storage hosting costs.
The UI banner, result origin, activity, assurance panel, approvals, history and
downloaded package distinguish simulation from live evidence.

`node aca\Generate-Example.mjs` regenerates the exact input fixture from the live
frontend's example constants. `--check` detects drift; the Docker build runs it.
Use `Judge-Check.py` to validate the no-sign-in example/revision/build/history
journey. `Verify.py --execute-live` is reserved for deliberately enabled live mode.

```powershell
& .\.intent-to-impact\spikes\UI-01-01\browser\.venv\Scripts\python.exe -B .\aca\Judge-Check.py
```

The verification session cookie is saved only in ignored `.local` state.
After an authorized idle-container restart, `Judge-Check.py --recover-job <jobId>`
verifies that session's simulated run and compiled package survive without
generating another response.

Recorded local receipts:

- `.local/judge-check-70bce5ba76a244cfb306ddc76f3a0879/receipt.json`: full judge journey.
- `.local/judge-check-c4a49d65321d41af870178163c2afb57/receipt.json`: cold stop/start recovery on a different replica.

The cold-restart check explicitly verified the original replica was gone before
reopening history and downloading the persisted package. Do not use ACA's rolling
`revision restart` operation for this single-writer store: it can start a second
pod while retaining the first, so the new pod correctly fails the exclusive lock.
Deactivate the idle revision, allow it to stop, then activate it instead. A
previous read-only recovery check after a rolling restart is retained locally,
but is not used as cold-restart proof.

These local receipts are not distributed with Git. Hosted live-model mode was
not proven functional (its initial identity call received 403); it is not used
by the judge deployment. Local real-model behavior remains unchanged.

To opt into chargeable Foundry execution on ACA, explicitly pass `-LiveModels`
to the deployment script after configuring/validating runtime permissions. It
is not enabled automatically, and `STUDIO_MODEL_MODE=simulated` is rejected
outside ACA hosting.

**Current access choice:** the user requested a public demo without sign-in.
The deployed app uses `STUDIO_AUTH_MODE=anonymous-demo` and ACA authentication
is disabled. HTTPS, secure session cookies, exact-origin/CSRF checks and existing
job limits remain. History is isolated to each browser session; other visitors'
saved prompts and packages are not exposed. Anyone with the URL can consume
shared compute/demo capacity; model charges occur only if live mode is explicitly
enabled later. Do not enter confidential information.

To reproduce this explicit public mode, include `-PublicDemo` with deployment.
Omitting it retains the template's safer Entra-authenticated default.

## Architecture

- One ACA Consumption replica and one Python worker, 1 vCPU / 2 GiB.
- HTTPS ingress supports built-in Microsoft Entra authentication; in that mode only the
  configured operator object ID is permitted. The backend validates principal
  identity and tenant on every application/API request.
- User-assigned managed identity pulls the private ACR image and invokes the
  existing Foundry model. No developer CLI login/token is copied into the image.
- Premium Azure Files NFS persists the existing file-backed run directory using
  a private endpoint and private DNS through a VNet-integrated environment.
  Inherited policy disables local/shared-key authentication, so the initial SMB
  mount was rejected. NFS uses private-network authorization without account keys.
- **NFS transport is not encrypted by ACA.** Only the private endpoint is reachable;
  public storage access remains disabled, and data is encrypted at rest. This
  is a documented demo trade-off, not a claim of end-to-end transport encryption.
- A small root init container sets ownership of the new mount to UID 10001 and
  mode 0700; the application and compiler then run as that non-root user.
- The container has a pinned Linux Bicep binary verified against its official
  release SHA-256. Models still cannot execute arbitrary infrastructure code.
- Log Analytics has 30-day retention and a 0.1 GiB/day ingestion limit.

The file-backed architecture is deliberately single-instance. A writer lock
prevents two workers from sharing mutable records concurrently. Revision updates
use ACA's manual multiple-revision lifecycle but keep **only one revision active**,
with one replica. The deployment stops the old revision first and accepts brief downtime
instead of unsafe overlapping writers. Active model/build work should finish
before an update. There is no automatic retry of interrupted model calls.

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | Locked Node build stage, Python runtime, non-root user and Linux compiler |
| `Dockerfile.dockerignore` | Explicit source allowlist; excludes local histories, credentials and dependencies |
| `Volume.Dockerfile` | Minimal mount-ownership init container; no app data or credentials |
| `main.bicep` | Subscription-scoped orchestrator and target resource group |
| `platform.bicep` | ACR, identity, environment, private file share/network and logs |
| `app.bicep` | Image, mount, probes, HTTPS ingress and Entra auth configuration |
| `inference-role.bicep` | Narrow model-inference role at the existing Foundry account |
| `Deploy.ps1` | Default what-if; explicit provisioning/build/push/update orchestration |
| `Verify.py` | Real hosted browser/model/compiler test or saved-history recovery check |

AVM versions are pinned in source. Storage uses an explicit resource because the
inspected storage module exposes account-key outputs; the final private NFS mount
does not use those keys. Local `.local` state and secret parameters are
ignored by Git and by the Docker build context. Protect this directory with the
operator's OS account and never share it. No existing local run data is migrated.

## Prerequisites

- Azure CLI, Docker Desktop using Linux containers, PowerShell 7 and Bicep.
- Current default subscription and authenticated deployment operator.
- Resource deployment, role-assignment and Entra application-registration permissions.
- Current project pins Foundry to `jv-eastus2-proj` / `gpt-5.2` in the existing
  demo subscription. A different tenant/project requires an explicit reviewed
  configuration change, not an API input.

## Preview

If Docker's network cannot complete verified TLS to the Python package host,
do not use `--trusted-host` or disable TLS checks. Optionally download compatible
Linux wheels through the host's verified package feed, then rebuild offline:

```powershell
& .\.intent-to-impact\studio\.venv\Scripts\python.exe -m pip download --only-binary=:all: --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 --platform linux_x86_64 --python-version 313 --implementation cp --abi cp313 --abi abi3 -r .\apps\control-plane\studio\requirements.txt --dest .\aca\wheelhouse
```

The build uses a populated `wheelhouse` without network package resolution.
Wheels are ignored by Git; no host Python environment or credentials are copied.
An empty wheelhouse uses the normal verified online pip install.

From the repository root:

```powershell
.\aca\Deploy.ps1
```

This runs Azure what-if without resource creation. It reports the subscription,
resource group and region. No model call is made.

## Provision and publish

After reviewing the plan and costs:

```powershell
.\aca\Deploy.ps1 -Provision
```

The script:

1. Resolves the default Azure CLI subscription and operator.
2. Deploys the named platform infrastructure and runtime identity roles.
3. Creates a single-tenant Entra registration and a 90-day client credential.
   The credential is kept out of source and command-line parameters.
4. Builds the exact current source with Docker and pushes a versioned image to ACR.
5. Deploys the app and auth configuration, with one replica.
6. Records target/image/nonsecret identifiers locally and prints the HTTPS URL.

Model calls, storage, ACR, private endpoint, logging and compute incur charges.
The indicative monthly infrastructure range is $50-$120 with the Premium NFS
share (100 GiB provisioned minimum) under the stated
single-replica assumptions, excluding variable model use and data/transaction
costs. This is not a quote or a spending cap.

## Updating

Wait for active work to finish, then:

```powershell
.\aca\Deploy.ps1 -Provision -ApproveRestart
```

For the current no-sign-in demo, append `-PublicDemo`. To resume after publishing
an image successfully, use `-Image <this-registry>/<app>:<tag>`; this skips registry
login/build/push. Registry login otherwise has a 90-second timeout rather than
hanging indefinitely.

The script retains the existing registration/secret and stable resource names.
It deactivates old revisions before launching a new writer. Do not enable
multiple replicas/revisions or share this data volume across separate apps.

The Entra credential expires after 90 days and must be rotated explicitly.
NFS mounting does not require a storage account key. Do not disable authentication
to troubleshoot a failed sign-in.

The app registration exposes an admin-consented `access_as_user` scope and
preauthorizes the first-party Azure CLI client. That allows the signed-in
allowlisted operator to run the verification tool using their own delegated
token. It does not grant other users access: the tenant/object-ID gates remain.
No access token is written to source, logs or verification receipts.

## Verification checklist

- `/healthz` responds without customer data or credentials.
- Entra mode: anonymous users cannot access the studio or any saved run/API data.
- Public mode: anonymous visitors can use the studio, but cannot read another
  browser session's runs or bypass CSRF/model consent.
- An unauthorized tenant/object ID cannot use the app even with a session cookie.
- The permitted operator can sign in and establish the studio CSRF/session state.
- Real example generation produces distinct synthesis and assurance receipts.
- Both contextual revision actions preserve their original parent/approval.
- Package generation executes Linux Bicep and downloads matching file hashes.
- Restart retains cloud history and compiled packages; no local histories leak.
- The localhost launcher/tests retain existing behavior.

Provisioning success alone does not establish these behaviors. Record actual
verification results separately; never label a fake model fixture as cloud
inference evidence.

With the existing browser-test Python environment, run:

```powershell
& .\.intent-to-impact\spikes\UI-01-01\browser\.venv\Scripts\python.exe -B .\aca\Verify.py --execute-live
```

This is chargeable, uses fictional repair-status input and performs real cloud
synthesis, assurance and compilation. Use `--saved-job <jobId>` after a restart
to verify recovery without another model call. The Azure CLI operator must be
the permitted identity. Receipts and downloaded samples stay under `.local`.

## Scope limits

This is a protected single-operator hackathon deployment, not a multi-tenant SaaS.
Azure Files encrypts at rest, but application records are not individually
encrypted. Access to the storage account remains sensitive. Existing schema,
job count and storage admission limits are retained.

Hosting the studio on ACA does **not** cause its generated workload packages to
be deployed automatically. The product's Deploy to Azure button remains a manual
verified-file/Portal handoff, with separate target values and approval.

## Cleanup

Resource-group deletion destroys persisted cloud runs and packages. Export any
needed records first. Review the exact target in `.local/deployment-state.json`.
Delete only this deployment's resource group when explicitly authorized, and
separately remove its Entra application/identity role assignment if no longer
needed. The existing Foundry account/project is shared and must not be deleted.
