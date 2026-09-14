# Early experience preview — UI-01-01 / UI-04-01, mock-first phase

This historical component viewer is no longer the default product entry.
Open `http://127.0.0.1:5173/?view=legacy-risk&scene=FX-09` explicitly.
The business-first frontend is documented in [README.md](./README.md).

A runnable **React / TypeScript / Vite** review preview of the seven accepted
initial snapshots. Shared shell, promise/risk presentation, supplied continuity
map + ordered list, and loaded-record evidence inspection are implemented.
This is **not full live-task acceptance**, the whole mock or all 18 interactions.

> **Historical fixture:** V2 public-endpoint examples are not current NSP proof.
> LOCAL-09 requires Storage behind NSP **Enforced**, with **zero external access
> rules**. Current V3 contracts/fixtures are pending. Do not re-label these V2
> snapshots or use the preview to pass GATE-UX01.

## Run locally (parent/reviewer)

Node >=22.19 and npm are required. Versions and the lockfile are pinned in this
app only; no root workspace, cloud tools or external runtime service is needed.

```powershell
Set-Location apps\experience
npm ci
npm run verify
npm run dev -- --port 5173 --strictPort
```

Open `http://127.0.0.1:5173/`. Direct review link:
`http://127.0.0.1:5173/?scene=FX-09`.
Stop the foreground server with Ctrl+C. The orchestrator has independently verified
the built preview in a real headless Edge browser; human review remains pending.
The attached review server uses `npm run preview -- --port 5173 --strictPort`.

For the built output, run `npm run build` then
`npm run preview -- --port 4173 --strictPort`.

## Review surfaces

- Use **Review scene** to open any of the seven complete authored snapshots.
  The dominant action uses the exact lowercase `allowedActions.actionId` and its
  explicit canned map; secondary controls inspect variants/evidence only.
- FX-01 is unconfirmed/unknown; FX-09 is the historical HTTPS-required risk;
  FX-10 is prepared; FX-11 remains verification-pending; FX-12 is fixture-verified
  with remaining unknowns. Missing and stale variants are separately selectable.
- The map draws only supplied edges. **Ordered list** uses supplied `listEntries`,
  full node labels and identical supported/broken/gap/pending meaning. Narrow
  layouts start in list view; source inspection is keyboard accessible there.
- **Inspect evidence** opens a modal showing source, observed time, synthetic
  resource, origin, freshness, eligibility and supported assertions before hashes.
  Close, Escape and Tab/Shift+Tab are supported; focus returns to the opener.
- Empty catalogs, unknown scenes/actions, corrupted/missing files and unsafe
  contexts stop visibly. They never fall back to a live API or a success screen.

The warm-paper/dark-ink/teal presentation imports the exact existing
`design\tokens\tokens.v1.css` selected by `tokens.v2-manifest.json` through the
Vite alias `@design-tokens.css`. No new/divergent token source, external font,
icon package, CDN or design service is used. Local serif/body/code stacks are
preserved. Focus, reduced motion, wrapping and the 48rem narrow breakpoint match
the accepted token guidance. Real browser checks cover all seven scenes at 1440,
768, 390 and 320 CSS pixels, graph-caption/node separation, drawer focus trapping
and return, unknown-scene errors and absence of external requests/console errors.
They do not constitute actual browser zoom testing or human UX approval.

The browser runner uses an isolated Edge profile and requires an existing Edge
installation plus the test dependency in `tests\experience\requirements.txt`.
From the repository root, with the built preview running on port 5173:

```powershell
python -m venv .\.intent-to-impact\spikes\UI-01-01\browser\.venv
& .\.intent-to-impact\spikes\UI-01-01\browser\.venv\Scripts\python.exe -m pip install -r .\tests\experience\requirements.txt
& .\.intent-to-impact\spikes\UI-01-01\browser\.venv\Scripts\python.exe -B .\tests\experience\browser_smoke.py
```

Each run preserves screenshots, source hashes and a pass/fail receipt in a unique
directory under `.intent-to-impact\spikes\UI-01-01\browser`. The browser closes
after testing; the independently started preview server remains for human review.

## Data and type boundary

`src\data\fixtureTransport.ts` eagerly bundles only accepted **initial-v2-r2** JSON
through Vite raw imports. It performs a table lookup between complete snapshots,
not an HTTP request or product workflow. `crypto.subtle` checks their exact file
hashes locally (localhost is a secure context); no data is sent anywhere.
The build groups immutable raw fixtures into per-scene static asset chunks and
separates vendor code; these are ordinary same-origin JS assets, not live APIs.

R2 is the validated handoff at `fixtures\experience\initial-v2-r2\manifest.json`,
with `fixtureRevision=2`, new run/case/artifact identities and corrected shared
ASCII-escaped semantic checksums. Unicode display text, the V2 scenario hash,
projection shapes and exact action IDs are unchanged. The original `initial-v2`
files are preserved historical evidence but **must not be loaded as valid data**;
there is no fallback import or dev-server allowlist for that root.
The binding check uses the unique accepted fixture receipt:
`.intent-to-impact\spikes\MOCK-01-01\R2\20260913T014015Z-d3614a83\evidence-receipt.json`.
File-hash, schema, reference and mock-only validation remain strict. This UI does
not rewrite semantic hashes or relax validation to accommodate the defective
original payloads. Both revisions remain historical V2, not current NSP/V3 proof.

Canonical types are **type-only imports** from
`contracts\generated\1.0.0\typescript\{core,risk,projections}.d.ts`.
AJV 2020 type guards use the existing canonical JSON schemas through a
synchronous local registry; no remote schema retriever or handwritten substitute
model exists. Fixture-only mode/origin guards, typed reference presence, graph/list
parity and a matching supplied verification reference fail closed. They do not
compute eligibility, coverage, predicate verdicts, permissions or allowed actions.
Only the producer's provided counts/statuses/actions are displayed.

Presentation props (`LoadedScene`, `SceneChoice`, component props) are C-owned
view adapters, not new canonical contracts. The frozen fixture files, schemas,
generated types, design sources and past evidence are never edited by this app.
`check:legacy` verifies the accepted R2 fixture manifest/receipt, all fixture files, frozen
V2 schemas and shared token hashes separately from the primary build. If V3 arrives, request its
accepted handoff rather than modifying canonical inputs or enabling a live mode.
Mutable registry/helper hashes are not frozen fixture input pins; the fixture
owner records their versions in the unique validation receipt.

The initial closed-schema limitations still apply:

- No P02/P03 question/option engine, P04 approval/materialization controls,
  full P07/P08 receipt/attention view or full P09 API is invented.
- Evidence inspection is a read-only view of loaded E01/D15/etc. fixture records.
  Opaque D10/D11/D12 references are not promoted to supported graph proof.
- Browsing risk from the initial scene does not confirm RPO, approve a design,
  materialize files, deploy, seed or restore anything. The graph is not editable.
- Historical `verified` is always qualified as a fixture example. Normal current
  promise confirmation, operation authorization and human gate review are separate.

## Validation and evidence

```powershell
npm run typecheck
npm test
npm run build
npm run verify:legacy
```

`verify:legacy` runs those real npm commands, captures output/source hashes and writes
separate phase receipts under `.intent-to-impact\spikes\UI-01-01\R2\<verification-id>\`
and `.intent-to-impact\spikes\UI-04-01\R2\<verification-id>\`, without overwriting
earlier receipts. It prints the exact new receipt paths and starts no long-lived process.
Tests are colocated: transport safety/navigation and focused jsdom component
tests for one dominant CTA, disabled loading, pending/unknown/stale wording,
historical/mode disclosure, map/list parity, drawer focus/Escape, narrow semantic
mode, empty/error states and no live fallback.

Typecheck, DOM tests and production asset build are **live-local validation**.
Content remains **fixture/ux-mock**, ineligible for live proof. No production
integration, actual browser screenshot, human aesthetic approval or GATE-UX01
pass is claimed.
