# Live architecture studio

**Updated:** 14 September 2026. For the documentation index and fresh-checkout
dependency setup, start with the [repository README](../../../README.md).
The [numbered user guide](../../../docs/intent-to-impact-user-guide.md) is the maintained
walkthrough of the current UI and validated scenarios.

The default page is now an interactive AI studio, not the earlier document wizard.
Enter a business prompt, optionally attach text/Markdown process documents, explicitly
consent to model processing, and generate an architecture using the existing Foundry
`gpt-5.2` deployment.

## Run the combined service

From the repository root:

```powershell
.\intent-to-impact-studio\tools\Run-LiveStudio.ps1
```

Open **http://127.0.0.1:5173/**. The script builds frontend assets and starts the
same-origin, IPv4-loopback Python API. After building successfully, it stops any
existing studio or Vite server recognized as belonging to this workspace on port
5173, waits for release, and starts the replacement. It refuses to stop unrelated
or unidentifiable processes. Finish active work first; a restart may interrupt
model/build jobs, but does not delete saved runs. `-SkipBuild` reuses built assets
and performs the same port cleanup.
The isolated Python environment and pinned dependencies are documented in
[the backend guide](../control-plane/studio/README.md). Stop with Ctrl+C.

For a standalone stop, run `.\intent-to-impact-studio\tools\Stop-LiveStudioPort.ps1` from the repository
root, or `.\Stop-LiveStudioPort.ps1` from `tools`. It infers the workspace from
the script location and invokes cleanup directly. Dot-sourcing is import-only,
as required by the launcher's build-before-stop sequence.

Do not use `npm run dev` or `npm run preview` as the live application: they only serve frontend assets
and cannot supply the authenticated model/job/build APIs.

## Current behavior

- A real streamed synthesis call produces requirements, process steps, assumptions,
  targeted questions, alternatives, components and connections.
- A separate real assurance call reviews nine dimensions against the sources.
- The canvas renders the returned topology with pan/zoom, movable nodes,
  component inspection and a responsive list view.
  Hover over or focus the canvas to use **Ctrl/Cmd + plus/minus** (including
  Ctrl + `=` and numpad keys). **Ctrl + mouse wheel** and trackpad pinch-style
  wheel gestures zoom around the pointer; **Ctrl/Cmd + 0** fits the layout.
  The toolbar provides the same zoom controls, bounded to 25-180%.
  Browser shortcuts in input fields/outside the canvas and normal wheel scrolling
  are not intercepted. Canvas zoom is inactive in list view.
- Automatic topology placement uses pinned Dagre layered layout, including
  crossing reduction, cycle/feedback handling and individual connection routes.
  **Re-layout** restores automatic placement after dragging; **Fit** now changes
  only the camera and preserves manually positioned blocks. Choose **Left to right**
  or **Top to bottom**, and use **Expand** to temporarily hide the side panels
  and review summaries so the diagram gets the available workspace. **Restore
  panels** brings the context back; errors remain visible in expanded mode.
  Connection labels appear on selection/hover; **Labels** shows them all. The
  complete connection text remains available in List view. These are visual
  controls only: they do not change the design, assurance, sources or packages,
  and make no model calls.
- Source links show the exact submitted prompt/document/refinement snapshot.
- Original-source changes start a new analysis; refinement of unchanged sources
  produces a distinct model result and a change summary.
- The build panel requests deterministic infrastructure generation and displays
  actual compilation diagnostics/file previews. ZIP download is permitted only
  for a successful compiler receipt.

**Integration status:** the complete browser-to-model generation, separate assurance,
interactive canvas, live refinement, actual Bicep compilation and browser ZIP
download have passed an end-to-end run. The downloaded archive's eight file hashes
matched every preview/receipt. Unsupported designs and compilation failures remain
explicit errors, never sample-package fallbacks.

The package contains `main.bicep`, `main.parameters.json`, compiled `main.json`,
`bicepconfig.json`, `catalog.json`, `manifest.json`, `validation.json` and a README.
It is **compiled infrastructure**, not a deployed business application. Supply the
required existing Entra API application ID, any external HTTPS endpoints, an
approved target resource group/region and application code. Target policy, quotas,
permissions, regional availability and runtime behavior are not validated by the
compiler. Public endpoints may be blocked by a target's policy.

Loading example inputs makes no model call and loads no canned architecture.
Model output remains a proposal, not design approval, compliance certification,
priced capacity or deployed-state proof. No Azure deployment endpoint is exposed.

The built-in order-fulfilment example now has an explicit end-to-end Playwright
regression (`--example --build`), rather than relying on a different custom scenario.
Its named ERP/payment/warehouse integrations carry server-bound source quotations.
The activity timeline shows a few real operation stages; chunk character counts
are not customer-facing progress.

## Challenge a finding and approve a design change

In **Assurance**, select a review lens (for example **Security**), then:

1. Choose **Request recommended change** to prefill the model's recommendation,
   or **Challenge finding** to explain a disagreement and propose a correction.
2. Review the original finding and selected architecture alternative. Edit the
   instruction (10-2000 characters); no model call occurs while drafting.
3. Give fresh model-processing consent and click **Approve & regenerate**.
   The server binds this revision permission to the exact immutable parent result,
   selected option, and finding. Editing the instruction clears the checkbox;
   changed working inputs or alternatives invalidate the open approval panel.
4. Synthesis generates a new proposal, followed by an independent assurance call.
   The workspace shows the before/after finding, instruction, local approval
   record and model change summary. An unresolved blocker stays visible.
5. Review the revised alternatives, then separately use **Build** to generate
   a compiled infrastructure package for the new result.

This action **approves a revision request, not the resulting design or a risk
exception**. It never lowers severity locally, bypasses security requirements,
implements business application handlers, or deploys Azure resources. A changed
AI severity is not verified resolution. Failure preserves the previous design;
the failed request and its approval remain in history. Closing the panel during
generation only hides it; the server job continues.

Approval uses the local `demo-human` identity, not independently authenticated
production sign-off. **Run history** and the downloaded run-record ZIP retain the
approval alongside the resulting or failed job. Earlier runs without approvals
remain readable; subsequent revisions require fresh consent.

The focused Playwright regression is
`intent-to-impact-studio\tests\experience\design_change_browser.py --execute-live --parent-job <saved-example-job> --build`
(run with the existing browser-test Python environment from the workspace root).
It exercises the actual saved Security blocker, explicit approval, real synthesis
and assurance, compiled eight-file ZIP hashes, and exported decision history.
For an already completed revision, use `--resume-job <revision-job>` instead of
`--execute-live` to finish verification without another inference call.

## Guided Azure deployment handoff

After a successful current build, **Deploy to Azure** opens a preparation panel.
The browser verifies the exact compiled ARM and parameter-file SHA-256 hashes,
lists required parameters, shows unresolved blockers and explains target checks.
You can download those JSON files and, after acknowledgement, open Azure Portal
to load the template and review the deployment manually.

The studio does not upload/host the template, select a target, create resources,
or observe deployment success. The local build receipt remains `not-deployed`.
Actual provisioning requires real target/integration values, resolved blockers
and separate approval of billable resources. Portal navigation and file integrity
must not be reported as successful Azure resource deployment.

See the [numbered user guide](../../../docs/intent-to-impact-user-guide.md) for complete
steps, scenario coverage, troubleshooting and evidence.

The exact reported order-fulfilment package now compiles independently of a
malformed unselected alternative. Selected self-loops/duplicate pairs still
produce actionable diagnostics. Queue direction (not prose) determines sender
and receiver roles; packages expose this limitation rather than silently
inferring permissions.

The numbered browser regression verified the original selected package,
regenerated it with a distinct build ID, checked both downloaded ZIP hashes,
and opened the real Azure Portal handoff without uploading or creating resources.
Both contextual assurance actions also passed real synthesis/re-review and
subsequent package-download checks. See the guide's recorded verification table.

## Run history

Use **Run history** in the workspace toolbar, then select an earlier run from the
dropdown. Successful, failed and in-progress runs are retained. You can:

- **Open this run** to restore its original prompt, documents, architecture,
  review and available package. Unsaved working input requires confirmation before
  replacement. A restored completed result is labelled **Saved model result**.
- **Download run record ZIP** for the original input/document text, result,
  activity/error record and saved-package index.
- **Download saved package** for a previously compiled infrastructure ZIP,
  without regenerating it.
- Reconnect to an in-progress job by polling it, without creating another model
  request. Refining a saved result creates a new run after fresh model consent.

At the user's explicit selection, this installation uses **shared local workspace
history**, including earlier browser sessions. Anyone using the local studio can
view those saved inputs/documents/results. This is a single-user demo choice, not
production multi-user isolation. The deployment setting is stored outside source
control at `.intent-to-impact\studio\settings.json`:

```json
{"historyScope": "workspace"}
```

The safe default without that setting is `"session"`, preserving session-owner
isolation. Changing the local setting requires a server restart. Records remain
under `.intent-to-impact\studio\runs`; history does not scan unrelated spike/test
folders. Run ZIPs contain source documents, but exclude authentication cookies,
CSRF tokens and internal ownership/idempotency records. Treat downloaded records
as customer data.

Neither the sharing setting nor saved runs are included in Git. A collaborator's
checkout starts with the safe default and an empty run history.

Actual Edge testing reopened a stored run from an earlier session, downloaded both
its run record and original compiled package, restored the canvas/inputs, and
reloaded history without making any model or build POST. Evidence:
`.intent-to-impact\spikes\RUN-HISTORY\e90df6d30eab47c491f0f4fbbe87b979\receipt.json`.

## Data and security boundary

Attaching files only reads local UTF-8 TXT/Markdown text. Generate sends the
consented prompt/documents to the configured Microsoft Foundry project and incurs
inference charges. **Submitted text, results and receipts are also stored
unencrypted locally** under `.intent-to-impact\studio\runs`. Do not submit secrets
or content you cannot send to that project.

Azure credentials stay on the server. Browser requests use a server-issued
HttpOnly/SameSite cookie, CSRF token, exact local Origin and custom client header.
No permissive CORS or external browser fetches are used. This is a local demo,
not production authentication or isolation from an OS administrator.

The response schema is authoritative at
`intent-to-impact-studio\apps\control-plane\studio\studio.schema.json`. Types and **static, CSP-safe**
validators are generated from it; browser startup does not require `unsafe-eval`.
Failed responses do not fall back to fixture data. Interrupted jobs require
explicit recovery, not automatic inference replay.

## Validate

The latest scoped execution summary is maintained in the
[user guide](../../../docs/intent-to-impact-user-guide.md#recorded-verification---14-september-2026).
Counts and receipt paths below document earlier incremental runs; they are not
one fresh full-suite result. Raw receipts, browser environments and saved job
IDs live under ignored local directories and do not accompany a checkout.
Historical `check:legacy`/`verify:legacy` also require local fixture acceptance
receipts; use `check:studio`, type-checking and the live-studio tests for the
maintained source-only path.

From `intent-to-impact-studio\apps\experience`:

```powershell
npm run generate:studio
npm run check:studio
npm run typecheck
npm test
npm run build
npm run verify
```

Generation uses the repository's pinned JSON-Schema-to-TypeScript tooling and the
app's AJV/esbuild dependencies. Generated files must not be hand-edited.
`verify` records build/test evidence, not live-model proof.

Explicit synthetic, chargeable end-to-end tests from the repository root:

```powershell
& .\.intent-to-impact\spikes\UI-01-01\browser\.venv\Scripts\python.exe -B .\intent-to-impact-studio\tests\experience\live_studio_browser.py --execute-live
& .\.intent-to-impact\studio\.venv\Scripts\python.exe -B .\intent-to-impact-studio\tests\studio\live_smoke.py --execute-live --refine
```

The browser runner's optional `--build --refine` flags test actual package generation
and another live revision. They passed in the integrated run recorded at
`.intent-to-impact\spikes\STUDIO-BROWSER\40fca57df67d46b99ad45eec8b19a1a7\receipt.json`.
The local test suites passed 108 frontend tests and 60 backend/generator tests,
including two real compiler cases. None of
these commands deploys Azure resources. Each attempt preserves separate receipts.

To exercise the actual **Load example inputs** button without substituting test data:

```powershell
& .\.intent-to-impact\spikes\UI-01-01\browser\.venv\Scripts\python.exe -B .\intent-to-impact-studio\tests\experience\live_studio_browser.py --execute-live --example --build
```

The corrected built-in flow passed live synthesis/assurance, explicit integration
provenance, concise progress, component inspection, four viewport widths and the
compiled ZIP download. Evidence:
`.intent-to-impact\spikes\STUDIO-BROWSER\3f1553cb8934444abddd7abb696c12cc\receipt.json`.
After these corrections, 109 frontend and 66 backend/generator tests pass.

Canvas keyboard/wheel controls have additional isolated-browser coverage:

```powershell
& .\.intent-to-impact\spikes\UI-01-01\browser\.venv\Scripts\python.exe -B .\intent-to-impact-studio\tests\experience\canvas_zoom_browser.py
```

This test replays a stored design into the UI (no inference or backend proof), but
uses actual Edge key presses and mouse-wheel events. It checks pointer anchoring,
limits, Fit, input/outside scope and list-mode behavior. The focused canvas/studio
unit suite has 31 passing tests, including 13 dedicated zoom tests.

The earlier offline draft workbench is retired: its navigation link and lazy-loaded
route have been removed. Old `/draft` bookmarks now open the live studio, and the
production bundle no longer includes the workbench UI. Shared document-reading
and example helpers remain; previously saved browser drafts are neither deleted
nor automatically sent to the model. [DRAFT-MODE.md](./DRAFT-MODE.md) is historical
documentation only, not a supported startup path.
The old risk fixture view is retained for development regression only, not as the
live product or a substitute for model output.
