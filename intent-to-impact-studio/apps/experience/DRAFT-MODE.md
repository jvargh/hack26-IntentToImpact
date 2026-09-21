# Retired: business-first architecture workbench

**Retired from product navigation and routing on 14 September 2026.** Old `/draft`
bookmarks now open the live studio documented in [README.md](./README.md).
The original component/tests remain for historical reference; shared input helpers
are still used by the live studio. Existing browser draft data has not been deleted.

The descriptions below document the earlier offline prototype, not current
product functionality.

Start with a business problem and process documentation. Work through
**Your business -> Understanding -> Architecture -> 360 review -> Design brief**.
This was the first business-first prototype before live synthesis and compilation.

## Current startup

Use the combined live service from the repository root:

```powershell
.\tools\Run-LiveStudio.ps1
```

Open **http://127.0.0.1:5173/**. Frontend-only dev/preview servers do not provide
the live API. This retired mode is no longer an offline alternative.

## Historical capabilities

- Enter your project name and business prompt.
- Attach and inspect actual UTF-8 `.txt`, `.md` or `.markdown` source text.
  Limit: five files, 1 MB each, 150,000 combined characters; prompt limit 12,000.
  Unsupported, empty, binary, duplicate and oversized documents produce errors.
- Review and edit the goal, actors, process, existing systems and constraints.
- Answer clarification questions and record open decisions.
- Compare three **reference patterns**, inspect their responsibilities/data flows,
  manually select a pattern and write a rationale.
- Work through nine review dimensions: business fit, security/privacy, reliability,
  performance, cost, integration/data, compliance, operations and delivery.
- Export a real Markdown brief containing your inputs, answers, selected pattern,
  logical-flow diagram in Mermaid, review notes and unresolved questions.
- Explicitly save a draft in this browser, resume it, or clear it.

**Try the worked example** loads an illustrative order-to-fulfilment process with
source-linked understanding, four prefilled editable clarification answers and
review findings. The separate example clarification-workshop document identifies
the sample workload, recovery, budget/timeline and ownership assumptions. They are
not real customer confirmations, calculated costs or validated targets. Custom
projects still start with unanswered questions. It is a deliberate demonstration,
not the result of a live analysis. It is never silently substituted for custom input.

## Truth, privacy and persistence boundaries

**AI analysis is not connected.** A custom prompt is copied literally into the
editable goal; the frontend does not claim to extract a process, infer controls,
recommend a design, price resources or assess compliance. Its other brief fields
remain for the author to fill. The same clarification checklist is offered
explicitly rather than presented as model-generated questions.

Patterns are starter references, not architecture generated from uploaded documents.
Review status records the author's checklist progress, not a server verdict or
approval. Changing source inputs invalidates illustrative findings and prior
selection/review state. Changing the pattern requires re-review; notes are retained.
No costs, runtime status, deployment success or governance approval is invented.

Files are read locally and kept in memory until **Save draft** is used. Saving is
opt-in and includes source text in `localStorage`, under
`intent-to-impact.business-draft.v1`. This is not encrypted, multi-user storage or
canonical backend case state. Use non-sensitive demo documents on shared devices.
No document, prompt or draft is sent over the network. Raw attachment bodies are
excluded from the Markdown export; manually entered/quoted brief content is included.
Clear removes only this app's draft key. Corrupt or inaccessible storage is reported,
not silently replaced. Unsaved changes do not survive a reload.

Document text is rendered as text, not executable HTML or trusted instructions.
PDF and Word files are not silently accepted without extraction; export their
contents as UTF-8 text for this iteration.

## Backend increments after frontend review

The local `DesignDraft` in `src/business/model.ts` is a versioned **presentation
draft**, not a competing canonical D01/D02/approval schema. The next integrations
should map user inputs into backend-owned contracts, preserving origin and source
references:

1. Controlled ingestion/extraction, including PDF/Word, provenance and deletion.
2. Source-grounded understanding and consequential clarification questions.
3. Architecture synthesis, diagrams, alternatives and current cost assumptions.
4. Independent multidimensional review with explicit missing evidence.
5. Human-approved implementation handoff and runtime continuity.

Connect each capability explicitly. Do not hide a service failure behind sample
data, reinterpret local checklist completion as approval, or promote an example into
live proof. The intake-led UI is not blocked by NSP sandbox provisioning.

## Validate

```powershell
npm run typecheck
npm test
npm run build
npm run verify
```

`verify` writes unique, source-hashed command receipts under
`.intent-to-impact\spikes\UI-BUSINESS-FIRST`. Unit/component tests include the retained
historical viewer regressions; passing them is not human UX acceptance.
The completed phase passed **77 unit/component tests**, strict typechecking and
the production build. **28 real-browser checks** cover both the custom and example
journeys, actual text-file reading, source-dialog keyboard behavior, explicit
save/resume, exported content, no external requests and all five steps at
1440/768/390/320 CSS-pixel widths. These reflow checks do not claim a full
accessibility audit or real browser-zoom certification.

With the built server running, the real-browser runner uses existing Edge and the
isolated Playwright environment:

```powershell
& .\.intent-to-impact\spikes\UI-01-01\browser\.venv\Scripts\python.exe -B .\tests\experience\business_browser_smoke.py
```

Run that command from the repository root. If the environment is missing, create an
isolated venv and install `tests\experience\requirements.txt`. The test opens an
isolated browser profile, never the user's personal browser profile.

## Historical component viewer

The old seven-scene view remains at
`http://127.0.0.1:5173/?view=legacy-risk&scene=FX-09` for regression work only.
Its files, fixtures and evidence are not relabelled as the new user journey.
Run `npm run check:legacy` for its separate frozen-input checks.
See [LEGACY-PREVIEW.md](./LEGACY-PREVIEW.md) for its original scope and limits.
