# SPK-04-01: actual local Bicep compilation

Spike-only v1.0.0; source-aligned with `SPK-04` in the approved local
implementation plan and its `SPK-04-01` task packet. No product contracts or
canonical state are created. The sample is **synthetic**, not a complete
deployment architecture or full CP-01 verifier.

## Replay from the workspace root

```powershell
pwsh -NoProfile -File .\tests\spikes\bicep\Run-Spike.ps1
```

Requires PowerShell 7.2+, Python 3.10+ (standard library only), and actual Azure CLI
on PATH. The wrapper returns failure for unexpected command, compiler, hash or
test failures. It creates a fresh, non-overwriting timestamped directory beneath
`.intent-to-impact\spikes\SPK-04-01\`; it has no target/subscription arguments and
does not use an existing Azure login or write to its configuration.

The fixed command sequence records `az version`, `az bicep version`, two real
`az bicep build --no-restore` runs, a real invalid-source build, and unittest.
All commands have timeouts. Source, compiler binary, compiled outputs, generated
mapping and redacted stdout/stderr are SHA-256 hashed. Command timestamps,
argument vectors, exits, expected/actual outcomes and tool versions appear in
`receipt.json`. `[workspace]` and `[user-home]` replace local paths in recorded
arguments/streams; basic credential-pattern redaction is also applied. Hashes
of streams cover the **persisted redacted bytes**, not an unredacted transcript.
Do not add secrets to this fixture.

Azure CLI config, extensions, telemetry settings and temporary paths are isolated
inside each run directory. If and only if the actual version command reports a
missing Bicep compiler, the runner invokes `az bicep install --version v0.34.44`
into that run's `azure-config\bin`. This compiler download is the only potential
network/tool-restore effect; it is recorded separately and is not runtime or
live-external compliance evidence. No Python packages or modules are restored.
There are no external Bicep modules. Failed restoration blocks actual proof;
there is never a hand-authored ARM fallback. A fresh isolated run may need the
same compiler download again. Offline replay requires an available compiler in
the isolated config; this runner intentionally does not read a shared Azure cache.

## What the checks establish

- The resource-group-scoped `main.bicep` really compiles, twice, to identical
  ARM JSON bytes with the recorded compiler.
- The single StorageV2 resource has the pinned `2023-05-01` API, a stable
  `architecture-component-id=CMP-CLAIMS-STORE` tag, disabled public network
  access, disabled anonymous blob access, HTTPS-only, TLS 1.2, and deny-by-default
  network ACLs. Each is a **desired-state property**, not an observed control.
- `promise-mapping.json` labels the source symbol, tag and CP-01 association as
  fixture assumptions. `resource-mapping.json` confirms their structural match
  to the actual compiled resource; it does not turn that assumption into proof.
- Subscription, location and storage name remain required parameters without
  invented values. `subscriptionId` is used only in the intended resource-ID
  output. Actual deployment scope is resource group; compilation cannot enforce
  consistency between an operator's future scope and that parameter.
- `tmp\invalid.bicep` is generated only inside the owned run directory and
  retained as evidence. Its actual nonzero compiler exit must include a BCP
  diagnostic and must not produce ARM JSON. Its command outcome is
  `expected-negative-failure`, **never successful compilation**.
- The unittest run checks actual output, mapping, hashes, mutation rejection,
  meaningful negative results, redaction, and fail-closed outcome classification.

Standalone classification tests (live checks are explicitly skipped):

```powershell
python -B -m unittest discover -s .\tests\spikes\bicep -p test_spike.py -v
```

To recheck an unchanged completed run, set `SPK_BICEP_RUN_DIRECTORY` to its
absolute directory and run the same unittest command. The PowerShell runner
already runs all nine tests against actual evidence before recording success.
Evidence is immutable by convention, not signed or protected against a hostile
local editor. Receipts from earlier source revisions will not satisfy current
source-hash checks.

## Explicit missing proof

No authentication, deployment, target validation, what-if, provider registration,
resource mutation, private endpoint, DNS, authorized private path, storage
operation, identity/RBAC, policy, quotas or complete encryption verification.
The LRS SKU is a fixture choice, not a production recovery recommendation.
Secure transfer is an additional sample property, not a redefinition of CP-03.
**CP-01 runtime status remains unknown** and target preflight is **not-run**.
The task neither satisfies a deployment gate nor approves UX03; later work may
consume the real compiler diagnostic as a validator example.
