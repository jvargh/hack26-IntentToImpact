# Intent to Impact: numbered user guide

**Applies to:** the current live architecture studio, updated 14 September 2026.  
**Screenshot key:** points **1-12** are in image 1, **13** in image 2, **14-16**
in image 3, and **17** in image 4. Image 5 shows the package-generation error
explained below.  
**Publication:** screenshot numbering is explained in this guide; source
screenshots, raw run evidence and the archived three-minute script are local-only.  
**Setup:** [Repository README](./README.md).  
**Technical detail:** [Engine deep dive](./intent-to-impact-technical-deep-dive.md).

## 1. Start the correct application

From the project root:

```powershell
.\tools\Run-LiveStudio.ps1
```

Open <http://127.0.0.1:5173/>. If it is already running, do not start a second
server on that port.

- **Ready - configuration only** means the configured model integration is
  available to attempt a request. It is not proof a model call has succeeded.
- Do not use `npm run dev` or `npm run preview` alone. They are frontend-only;
  an API request can receive the HTML page instead of JSON and produce
  **The live service returned unreadable JSON**.
- **Draft mode** was an offline prototype and is retired. It appears in the old
  screenshots but not the current toolbar. Old `/draft` links open the studio.
- Submitted prompts, documents, results and decisions are stored unencrypted
  locally. The developer installation shares run history between local browser
  sessions; a new checkout defaults to session-private history unless explicitly
  configured otherwise.
  Do not enter secrets or data you are not authorized to send to the model.

## 2. What each numbered point does

### Point 1 - Project name

Give the engagement a recognizable name, such as **Order fulfilment-#1**.
It helps identify the request in history. The title is not an Azure resource
group or a deployment target.

**Expected:** the title is carried into the submitted run. A title edit is an
unsent input change until another explicit analysis request.

### Point 2 - Business prompt and example inputs

Describe the customer outcome, process, constraints, existing systems and unknowns.
Use **Load example inputs** for the fictional order-fulfilment scenario.

**Expected:** the example fills input fields and attaches sample source text.
It makes no AI call and does not draw a canned architecture. Check the
model-processing consent box, then select **Generate architecture** to run AI.

**Important:** loading the example replaces the working input. Reopen a saved
run through history rather than loading the example over an outcome you are
trying to inspect.

### Point 3 - Process documents

Attach UTF-8 TXT or Markdown documents. Click an attached document to preview
the exact text and close the source drawer when finished.

**Limits:** five documents, at most 150,000 combined text characters, and up to
1 MB per file at local intake. PDF/Word extraction is not available in this path.

**Expected:** the source is read locally first. It is sent to the configured
Foundry deployment only after explicit model-processing consent and submission.
Editing original sources starts a new analysis rather than silently reusing
the previous design's source snapshot.

### Point 4 - Synthesis response validation

This marker is an **activity event**, not a button.

The first model call proposes an architecture. The service checks response shape,
source references and supported component identities before continuing.

**Expected:** concise stage messages. There should not be an endless list of
received-character counters. An invalid proposal is not replaced by sample data.

### Point 5 - Separate assurance begins

This is another activity event. After synthesis validation, the service makes a
separate no-tools model call to review the proposal against its sources.

**Expected:** assurance runs after synthesis, not merely a second name for the
same response. The two calls have distinct recorded response IDs.

### Point 6 - Assurance response validation

The service checks the second model response, source references and the presence
of all nine review dimensions.

**Expected:** assurance can still report warnings or blockers. A valid review
is not necessarily a favorable verdict.

### Point 7 - Complete

**Complete** means both model calls returned acceptable results and the new
proposal was recorded.

It does not mean that application code has been implemented, an Azure deployment
has succeeded, or every blocker is resolved. In a restored run, these are
**saved events**, not newly executed work.

### Point 8 - Architecture workspace and result identity

The main workspace displays the current proposal and its origin:

| Label | Meaning |
|---|---|
| LIVE MODEL RESULT | Result returned by the observed real model job |
| SAVED MODEL RESULT | A completed result reopened from local history |
| PREVIOUS RESULT - NOT CURRENT | Working input changed, another request is running, or an earlier attempt failed |

Do not build from a stale working view. Restore the intended saved run, or
generate a new design from the changed input.

### Points 9 and 10 - Alternatives and summary

The two markers cover the alternative-comparison area and its summary. Select
each alternative to compare actual returned component boundaries, rationale,
trade-offs and conditional cost notes.

**Expected:** the topology and inspector change to the selected alternative.
**MODEL RECOMMENDATION** is the model's preference, not mandatory human selection.
An existing package for one alternative is not automatically a package for another.

### Point 11 - Topology and layout controls

| Action | Expected result |
|---|---|
| Click a block | Inspect that component and its requirement links |
| Re-layout | Restore automatic block placement and connection routes |
| Fit | Fit the current geometry without undoing manual block positions |
| Left to right / Top to bottom | Recompute the flow direction |
| Expand / Restore panels | Give the diagram more room, then restore context |
| Labels | Show all connection labels; selected/hovered connections expose labels otherwise |
| Drag a block / Shift + arrows | Move a block in the local visual view |
| Ctrl/Cmd + plus/minus | Zoom while the canvas is hovered/focused |
| Ctrl + wheel | Zoom around the pointer |
| Ctrl/Cmd + 0 | Fit the current view |
| List view | Read all components and full connection descriptions |

These actions do not call AI or change the stored architecture. A node drag is
not an approved architectural revision. A visually clear connection is also not
proof its application handler or access permission is implemented.

### Point 12 - Inspect

With a component selected, Inspect shows its service, responsibility and linked
requirements. Without a component selected, it explains the selected alternative.

Review **Why this alternative**, trade-offs and cost notes. Existing external
integrations are boundaries the package does not provision.

**Expected:** source evidence explains why a component was proposed. Model cost
notes are not a priced Azure quote or measured bill.

### Point 13 - Sources

1. Open **Sources**.
2. Select a requirement to highlight only the components with that requirement ID.
3. Select a source link to open its exact submitted prompt/document/refinement.
4. Close the drawer to continue.

**Expected:** the requirement-to-component relationship is inspectable.
Sources are normally whole-document links, not semantic proof that every claim
is entailed by a verified passage.

### Point 14 - Assurance

Assurance contains Business fit, Security, Reliability, Performance, Cost,
Integration, Compliance, Operations and Delivery.

Select a lens to filter its finding; select it again to show all findings.
Severity is **info**, **warning**, or **blocker**.

Findings review the proposal as a whole. The current contract does not contain
dimension-to-component impact links, so selecting Security does not invent
affected-node highlights.

### Point 15 - Request recommended change

Use this when the recommendation is a reasonable starting point.

1. Select the desired architecture alternative and assurance lens.
2. Click **Request recommended change**.
3. Inspect the exact finding, recommendation and target alternative.
4. Edit the prefilled **Design change instruction** if needed.
5. Select the fresh revision/model consent checkbox.
6. Click **Approve & regenerate**.
7. Wait for new synthesis and independent assurance.
8. Review **View change & decision record**, the latest finding and revised graph.

**Expected:** a new immutable result, not an in-place edit. The decision records
the original finding, parent result/hash, selected option and human instruction.
The original result remains in history.

**Approval means permission to revise.** It is not a waiver, final design approval
or a guarantee that the new severity will be lower.

### Point 16 - Challenge finding

Use this when you disagree with the finding or want a different design correction.

1. Click **Challenge finding** on the selected lens.
2. Enter evidence, the disputed assumption and your proposed direction in the
   initially empty instruction field.
3. Review the exact target and give fresh consent.
4. Click **Approve & regenerate**.
5. Inspect the revised design and the new independent review.

Example direction for the order-status finding:

> Challenge whether polling alone meets the original status-update requirement.
> Do not invent a confirmed channel or delivery target. Keep channels and freshness
> as open questions, separate known requirements from assumptions, and identify
> application notification work that the bounded catalog does not implement.

This is a request to reason about the supplied evidence, not permission to invent
new provider capabilities.

**Shared safeguards for points 15-16**

- Ten non-padding characters minimum, 2,000-character instruction maximum.
- The exact server-composed finding/instruction context must fit 4,000 characters.
- Editing the instruction clears consent.
- Changing working inputs or the selected alternative invalidates an open approval.
- Cancel before submission makes no model call.
- Closing the panel after submission only hides progress; the server job continues.
- A failed revision retains its failure/approval evidence and leaves the old result unchanged.
- A lower model severity is not verified risk resolution.
- New instructions create chargeable synthesis and assurance calls. There is no automatic retry.

### Point 17 - Generate or regenerate deployment package

1. Select the current desired architecture alternative.
2. Open **Build**.
3. Select **I confirm package generation only. Do not deploy Azure resources.**
4. Click **Generate deployment package**, or **Regenerate deployment package**
   if a previous build result is displayed.
5. Wait for the real compiler result.
6. For **COMPILED**, verify the compiler version and exit code 0.
7. Select **Download compiled ZIP**.

**Regenerate** recompiles the selected stored result and option without another
AI call. It creates a new build ID. Prior builds and their evidence remain in
history rather than being overwritten.

The successful ZIP contains eight files: Bicep, compiled ARM JSON, parameters,
catalog, compiler configuration, README, manifest and validation record.
Required existing Entra/integration values are intentionally not fabricated.

**Blocked or failed builds:** review diagnostics. No successful ZIP action is
offered. Repeating the same invalid design cannot repair it; use a revision or
select a supported alternative.

## 3. Image 5: why the package was blocked

The reported saved run is **Order fulfilment-#1**. Its selected alternative,
**AppService API + Service Bus queue + Functions workers**, did not contain the
duplicate pair reported by the error.

The duplicate pair was in the **unselected Functions-first alternative**:
the same Functions host pointed to the same queue for both enqueue and consume
descriptions. The builder applied selected-topology restrictions to every
alternative and stopped before running Bicep.

The correction scopes those build-only topology restrictions to the selected
alternative, while preserving whole-result schema and reference checks.
A malformed unselected alternative must not prevent building the supported
selection. Selected self-connections and duplicate directed connections remain
explicitly unsupported; they are not silently removed.

There is a second design issue in the original proposal: a connection labeled
**consume** points **application -> queue**, which the fixed catalog treats as
a sender. The catalog must not derive extra permissions from prose:

| Direction | Infrastructure meaning |
|---|---|
| Application -> Service Bus | Data Sender |
| Service Bus -> application | Data Receiver |
| Both opposite edges | Producer and consumer responsibilities represented separately |

New model instructions make that distinction explicit. Inspect existing queue
edges and their package warnings; correct a mislabeled or reversed design
through a new revision. Compilation does not prove the worker has a functioning
consumer or that the original diagram's prose matches the generated permissions.

**Recovery:** reopen the affected saved run, select the AppService/queue alternative
and regenerate. The old failed record remains available as evidence.

## 4. Deploy to Azure: guided handoff

### What the button does

After a successful current build, **Deploy to Azure** opens a guided handoff.
It verifies the recorded SHA-256 hashes of the compiled ARM JSON and parameter
file and lists the template's required inputs.

It does **not** send a template, create resources, run deployment validation,
select a subscription, or mark the package deployed. The studio keeps
`deploymentStatus: not-deployed` because it does not observe portal operations.

### Step-by-step

1. Open **Deploy to Azure** for the compiled package.
2. Read any unresolved assurance blockers and package limitations.
3. Download the exact **ARM template** and **parameter file**.
4. Gather an approved subscription, resource group, region, expected resource
   inventory and cost approval.
5. Supply the real existing Entra application ID, external HTTPS endpoints and
   same-tenant callback caller IDs required by this particular template.
6. Acknowledge the manual-handoff boundary, then select **Open Azure Portal deployment**.
7. Sign in to the approved tenant and select **Build your own template in the editor**.
8. Load the downloaded ARM template (or paste its JSON), then Save.
9. Choose the target and enter all required parameter values.
10. Select **Review + create**. Resolve validation errors, outstanding design
    blockers and policy/quota/RBAC/region issues before proceeding.
11. Only after authorized review of the billable resources, select **Create**.
12. Inspect Azure deployment operations and resource state. Implement/deploy
    application code and run application-level tests separately.

Official reference:
[Microsoft: create and deploy ARM templates using the portal](https://learn.microsoft.com/azure/azure-resource-manager/templates/quickstart-create-templates-use-the-portal#edit-and-deploy-the-template).

### Deployment limitations and verification status

- The current catalog enables public endpoints; known inherited public-network
  policy may reject them. Do not weaken policy to force a demo success.
- The existence of an ERP/payment/warehouse source declaration does not prove
  that provider's callback token/signature capability.
- App Service/Functions hosts are not completed business applications. Handlers,
  authentication clients, replay protection and consumer behavior require code.
- Hash checks prove file integrity, not target deployability.
- **Actual Azure provisioning is not claimed verified.** The required target,
  integration values and final resource/cost approval were not supplied for this
  change. Only the handoff can be validated without those inputs.
- Uploading the template to the portal is a deliberate later action. The studio
  does not publish it at a public URL or automatically transfer local source text.

## 5. Run history and continuation

**Run history** is outside the numbered markers but completes the journey.

- Select an earlier successful, failed or running run.
- **Open this run** restores its original inputs and outcome; confirm before
  replacing unsaved working input.
- **Download run record ZIP** includes original sources, execution records,
  approvals and the package index.
- **Download saved package** retrieves an existing compiled ZIP without a new build.
- Reopening a running job resumes polling, not submission.
- Portal deployments are not automatically imported as local success records.

## 6. Scenario checklist

| Scenario | Expected result | Evidence method |
|---|---|---|
| 1-3: enter/load inputs and inspect a document | No inference until explicit consent and Generate | Browser controls and source drawer |
| 4-7: inspect stages | Synthesis, validation, separate assurance, validation, complete/error | Real stored events; live revision runs for new execution |
| 8: reopen saved run | Saved origin label; no inference | History browser check |
| 9-10: switch alternatives | Correct graph, rationale and selected option | Browser checks against actual saved result |
| 11-13: layout, inspect, source tracing | Layout does not alter design; links show submitted sources | Browser interactions |
| 14: assurance lenses | Exactly nine dimensions, actual severity | Browser and canonical validation |
| 15: recommendation cancel/approve | Prefilled instruction; cancel is free; approve creates new reviewed result | Browser plus server/UI tests |
| 16: challenge cancel/approve | Empty instruction; evidence and consent required; new independent review | Browser plus server/UI tests |
| Stale or tampered approval | Rejected before applying a revision | UI/server tests |
| Revision failure | Prior design preserved; approval/error retained | Injected-failure tests |
| 17: original package error | Unselected duplicate no longer blocks selected supported topology | Exact saved-case compiler regression |
| 17: regenerate twice | Two real compiler runs, distinct build IDs, matching ZIP hashes | Browser/compiler check |
| Azure handoff | Verified JSON, required parameters, acknowledgement and portal navigation | Browser and local hash/shape tests |
| Actual Azure provisioning | Requires supplied targets, validation and explicit approval | Not executed or verified in this change |

### Recorded verification - 14 September 2026

The evidence paths below are relative to the operator-local
`.intent-to-impact\spikes` directory, which is deliberately excluded from Git.
They document the executed checks, but are not downloadable repository files.
Reproduce them using the included tests and newly generated fictional runs;
the original saved job IDs do not exist in a fresh checkout.

| Verification | Result and evidence |
|---|---|
| Numbered surfaces 1-17; exact original failing selection; two builds and downloads; history; real portal navigation | **Passed.** `NUMBERED-GUIDE/64ee05aec6c247b8b79cea9103fdc973/receipt.json`. The only two POSTs were package builds; no inference or Azure deployment. |
| Point 15: approve the actual Business fit recommendation | **Passed with real synthesis and assurance.** `DESIGN-CHANGE/c2d731bb495f46e7b308c1895558d593/receipt.json`. New job: `job_670a7e4371716476429c8d958ebdc637`. |
| Point 16: approve an explicit challenge to the same finding | **Passed with real synthesis and assurance.** `DESIGN-CHANGE/76474b8ad572403cbf1808f27266a7bc/receipt.json`. New job: `job_a2be8cb8dbf8a064b30eed6374f8f4a5`. |
| Package from recommendation revision | **Compiled and downloaded; hashes matched.** `DESIGN-CHANGE/523fa3f5b0204f458205e47a0077f874/receipt.json`. No additional inference. |
| Package from challenge revision | **Compiled and downloaded; hashes matched.** `DESIGN-CHANGE/138e3c1a128940aebc09a702ef6c04a3/receipt.json`. No additional inference. |
| Unit/contract regressions | Publication check: **89 studio/routing/client/layout/handoff tests**, generated-contract consistency, TypeScript and production build passed. Earlier backend verification: **25 bundle tests**, **19 model/validation tests**, **16 approval tests**. These are scoped suites, not an all-repository certification. |
| Actual Azure resource creation | **Not executed or verified.** Portal navigation/file preparation passed; target values and final provisioning approval remain required. |

Both successful revision runs kept the Business fit result at **warning** rather
than fabricating customer confirmation. Both returned queue-consumer connections
in the correct **queue -> application** direction.

During validation, an earlier live revision was rejected because its model output
used the literal kind `servicebus` as an endpoint instead of a declared component
ID. The ambiguous kind-level prompt example was clarified with concrete ID
examples and a regression check. A new explicitly initiated validation run
succeeded. The rejected run was preserved:
`DESIGN-CHANGE/93d223c312a9495785e9b5366df73173/receipt.json` (local-only).
No endpoint was guessed or silently repaired, and no failed output was promoted.

The two original-case builds had distinct IDs,
`8e7a15d5e1ad484d899dcc6a699cec02` and `943f08f0564749e480e131f256dedfc9`.
Both used Bicep 0.47.16, exited 0, produced eight-file ZIPs whose file hashes
matched, and left the original saved result bytes unchanged.

For a rehearsal on the original developer installation, use the newer successful
recommendation or challenge run above through **Run history**. Their saved build
is available without another model call. On a fresh checkout, first generate
your own fictional example and package; Git does not distribute saved runs.
Continue to inspect unresolved findings; a successful package is not release approval.

## 7. Troubleshooting

| Symptom | Cause / next action |
|---|---|
| Unreadable JSON at connection | Frontend-only server may be answering API calls with HTML. Stop that server and use the combined launcher. |
| Generate fails with a source-reference error | A result cited unavailable source data. Preserve the failed run; do not substitute example output. |
| Connection endpoint does not exist in its option | The model supplied an unknown ID, possibly a service kind instead of a component ID. The result is rejected rather than guessing the intended node. Preserve the failed run; a subsequent explicit request is a new model execution. |
| One analysis already running | Wait for the active job; opening history does not start another call. |
| Revision instruction too large | Shorten the direction; the server must preserve the exact original finding without truncation. |
| Buttons disabled after editing input | The displayed result is stale. Reopen it or generate from the new input. |
| Build blocked by selected duplicate/self-edge | Correct the selected graph through a revision; different operation labels do not override direction rules. |
| Queue consumer warning | Review queue-to-host direction and generated Data Receiver role; do not infer correctness from a consume label. |
| Deploy to Azure unavailable | Build must be compiled, relevant to the current result/option, and not stale or busy. |
| Handoff hash/JSON failure | Do not upload those files. Regenerate and recheck the package. |
| Portal asks for Entra/integration values | These are real prerequisites, not values the studio can invent. |
| Portal validation fails | Inspect target policy, permissions, quota, names, region and parameters. No studio-side success should be claimed. |

## 8. Validation commands

Run UI checks from `apps\experience`:

```powershell
npm run typecheck
npm test -- src\studio\views\DeploymentPanel.test.tsx src\studio\StudioApp.test.tsx src\studio\client.test.ts
npm run build
```

From the project root, the numbered browser test exercises a saved result,
actual build/regeneration/download and optionally opens the portal sign-in page.
It does not submit an analysis or an Azure deployment:

```powershell
& .\.intent-to-impact\spikes\UI-01-01\browser\.venv\Scripts\python.exe -B .\tests\experience\numbered_studio_browser.py --job job_d7b0179e97d82a29d1ba2c93f800644d --option opt-a-appservice-queue --open-portal
```

Real recommendation/challenge tests are opt-in and chargeable. Each successful
revision runs synthesis and assurance. Choose a known saved fictional example;
do not replace it with confidential customer input in an unattended test:

```powershell
& .\.intent-to-impact\spikes\UI-01-01\browser\.venv\Scripts\python.exe -B .\tests\experience\design_change_browser.py --execute-live --parent-job job_d7b0179e97d82a29d1ba2c93f800644d --dimension business --intent recommendation
& .\.intent-to-impact\spikes\UI-01-01\browser\.venv\Scripts\python.exe -B .\tests\experience\design_change_browser.py --execute-live --parent-job job_d7b0179e97d82a29d1ba2c93f800644d --dimension business --intent challenge --instruction "Challenge polling as an unconfirmed channel. Keep channel and freshness open, separate requirements from assumptions, and identify application work without claiming it implemented."
```

If a browser assertion fails after a job succeeds, inspect history first. Use
`--resume-job` to continue validating the completed revision without paying for
another inference. Match its dimension, intent and original instruction.
