# Live architecture studio backend

**Updated:** 14 September 2026. See the [repository setup guide](../../../README.md),
[technical deep dive](../../../intent-to-impact-technical-deep-dive.md), and
[numbered user guide](../../../intent-to-impact-user-guide.md).

The built experience and API share **http://127.0.0.1:5173**. This is a
single-machine demonstration, not production authentication. The OS/process owner
can read its local files. Never publish this server or place it behind a proxy.

## Run

From the repository root in PowerShell:

```powershell
& .\.intent-to-impact\studio\.venv\Scripts\python.exe -m pip install -r .\apps\control-plane\studio\requirements.txt
$env:PYTHONPATH = (Resolve-Path .\apps\control-plane).Path
& .\.intent-to-impact\studio\.venv\Scripts\python.exe -m studio.serve
```

Create that isolated virtual environment with `python -m venv
.\.intent-to-impact\studio\.venv` if absent. Build `apps\experience` using its
existing production build command first. No development proxy or CORS is needed.
The server binds exactly `127.0.0.1`, disables proxy headers, and never serves
source code or environment files. No Azure credential is sent to the browser.

The approved current Azure CLI identity must select subscription
`463a82d4-1896-4332-aeeb-618ee5a5aa93`, tenant
`5bb5fa45-2dcc-4310-bbc5-883021e9d84b`, state `Enabled`. Only existing project
`https://jv-eastus2-proj-resource.services.ai.azure.com/api/projects/jv-eastus2-proj`
and model `gpt-5.2` are used. Endpoint/model settings cannot come from API input.
Health reports configuration/import readiness, **not** successful inference.

The checkout retains this configured demo endpoint, not credentials. A new
operator needs authorized access or a separately reviewed configuration change.
Ignored environments, compiler binaries, session settings and saved runs must
be set up locally; they are not distributed with this repository.

## Browser protocol

1. `GET /api/studio/session` with `X-Studio-Client: 1` mints a one-hour
   `HttpOnly; SameSite=Strict` session cookie and returns `{csrfToken}`.
2. Every other API GET requires that cookie and `X-Studio-Client: 1`.
3. POST requires the cookie, custom client header, exact
   `Origin: http://127.0.0.1:5173`, `X-CSRF-Token`, and JSON content type.
4. `POST /api/studio/analyses` accepts canonical `AnalysisRequest` and returns
   the complete `StudioJob` with HTTP 202; poll `/api/studio/jobs/{jobId}`.
5. Build through `POST /api/studio/builds`; download only the owned build's
   returned `/api/studio/builds/{buildId}/download` URL.

`studio.schema.json` is the sole canonical contract; runtime validation uses
jsonschema, never a parallel handwritten Pydantic contract. Duplicate JSON keys,
unknown source/requirement/graph references, unsupported services, repeated review
dimensions and credential-like content fail explicitly. Model output is untrusted.
Documents are delimited as data; no tools, URLs, shell execution or model-generated
infrastructure execution are allowed.

## Live behavior and local persistence disclosure

Consent must be `true` before any user prompt/document is transmitted to Foundry.
**Prompts, document text, revisions, results and receipts persist locally** under
`.intent-to-impact\studio\runs` and are not encrypted by this application. Do not
submit secrets or documents you cannot send to the approved Foundry project.
Remove/archive this folder only while the server is stopped. By default, retain
the existing session cookie to access owned results after restart until its
original expiry. The explicit `historyScope: workspace` operator setting allows
all authenticated local studio sessions to read saved runs/results/packages,
including runs created by older sessions. The user selected that shared mode for
this installation; it is not production multi-user isolation. New analyses and
refinements still require explicit model consent and current CSRF validation.
There is no automatic deletion, inference replay or cloud deployment.

## Run history API

- `GET /api/studio/history`: bounded, newest-first summaries and effective scope.
- `GET /api/studio/history/{jobId}`: original inputs, job/result and package index.
- `GET /api/studio/history/{jobId}/builds/{buildId}`: full saved build receipt,
  only if it belongs to that run.
- `GET /api/studio/history/{jobId}/download`: a run-record ZIP, including source
  text but no session cookies, CSRF values, owner keys or idempotency records.

All history routes retain the normal loopback/custom-header/session protections.
Inputs are checked against their persisted hashes before being returned.
Document filenames are not used as ZIP paths; document bodies use fixed numbered
entries. Existing compiled-package downloads reuse the authenticated build route.
Restoring/reading/exporting runs makes no model or compiler call.

`create_app` defaults to session scope. `studio.serve` reads the local
`.intent-to-impact\studio\settings.json` setting, accepting only `historyScope`
equal to `session` or `workspace`; malformed settings stop startup. Workspace
sharing must be deliberately enabled, not requested by a browser parameter.

## Model execution and storage limits

Each job makes one streamed synthesis call and one separate streamed assurance
call. Both now request provider-enforced **strict JSON Schema output**, derived
from the canonical contract with per-request source-ID enums. An initial request
cannot emit `refinement` as a citation when no refinement source exists. The SDK
wire guard checks the exact structured format before sending the request; there
is no downgrade to plain JSON mode. The original runtime shape, length and
relationship checks still run after generation.

Each run retains its synthesis/assurance response-format schemas beside its
receipts. Only definitions reachable from that model output are sent; optional
fields become explicitly nullable where the canonical schema already permits null.
Provider format restrictions do not weaken the canonical runtime validation.

Customer progress contains bounded stage updates, not an entry per received
character batch. Character counts remain internal to the output-size guard.
The UI folds counters from older runs into optional technical diagnostics.
No fake progress or reasoning text is emitted. Invalid or failed responses do not become
results, and no fallback provider/fixture/automatic repair is used. Each call has
a 120-second ceiling, the job 300 seconds, CLI processes 20 seconds, SDK retries
zero. Cancellation means remote completion may be unknown. Interrupted jobs are
marked failed/recovery-needed on restart and never auto-retried.

One inference job runs at a time; extra submissions return 429. Bounds: 64 jobs,
64 builds, 16 unexpired sessions, 200 MiB local storage threshold, 800 KiB request
body, 5 documents/150,000 total text characters, 12,000 prompt characters.
New jobs reserve 4 MiB of headroom, builds 24 MiB; new submissions can therefore
be rejected before the storage threshold. Package requests have a 120-second
deadline and one-at-a-time admission, in addition to the generator's own compiler
timeout. A timed-out compiler thread may still finish locally; its idempotency
record is failed and is never automatically rerun.
Idempotency keys are session-scoped; changed input with the same key returns 409.
Refinements require an owned previous result and unchanged original sources;
they create a new immutable result. Replace sources by starting a new analysis.
`prompt` and `refinement` are reserved source IDs and cannot be document IDs.
A nonempty revision instruction adds the source metadata
`{"id":"refinement","name":"Refinement instruction"}`. Both model passes are
instructed to cite `refinement` for changed constraints, never retroactively
attribute them to the original `prompt`. That source ID is rejected when the
request has no refinement text.

## Contextual design-change authorization

The existing `POST /api/studio/analyses` endpoint optionally accepts `designChange`:

```json
{
  "optionId": "an-existing-option-id",
  "finding": {
    "dimension": "security",
    "severity": "blocker",
    "finding": "Exact stored finding text",
    "recommendation": "Exact stored recommendation text",
    "sourceIds": ["prompt"]
  },
  "intent": "recommendation",
  "confirmRevision": true
}
```

This is an additional property on the normal `AnalysisRequest`, not a standalone
request. `intent` is `recommendation` or `challenge`; both authorize a new
architecture synthesis followed by the existing separate assurance call.
`previousResultId` must identify the exact visible immutable parent result.
`refinement` is the original human-approved direction, 10–2,000 characters
(at least 10 after trimming). Prompt and documents must be unchanged.
The option must exist in that parent and the entire finding object must match
its stored review, including severity, recommendation and source ordering.
Missing confirmation, foreign parents, tampered context and changed sources fail
before scheduling inference. Existing generic refinements remain unchanged.

The server wraps the direction with the selected option, exact old finding and
instructions to change the architecture and independently re-review it. The
selected option ID should be preserved and recommended if feasible; otherwise
the model must explain why. Approval never authorizes suppressing blockers,
bypassing security, implementing application code or deployment. Exact wrapped
context exceeding 4,000 characters is rejected rather than truncated. This
effective `refinement` remains the cited refinement source in both model calls.

Before execution, the server persists an immutable `change-approval.json` and
an optional `StudioJob.changeApproval` containing:
`baseResultId`, `baseResultHash` (canonical SHA-256 of the complete parent result),
`optionId`, exact `finding`, `intent`, original `instruction`, exact wrapped
`refinement`, server-generated `approvedAt`, `actor: "demo-human"` and
`scope: "design-revision-only"`. This records **permission to revise, not risk
acceptance or sign-off of the resulting design**. The actor is a demo label,
not authenticated enterprise identity. No build/deployment gate is changed.

Idempotency binds the full submitted metadata and returns the same job and
approval timestamp on an unchanged retry. Input, parent and approval hashes
and the exact contextual binding are checked during recovery and history reads;
corruption stops recovery rather than silently dropping the authorization.
Failed/interrupted jobs retain it without changing the parent result or clearing
its original blocker. Existing records need not have this optional field.
`SavedRun.job` and the run archive's `run.json` expose the same receipt; saved
`inputs.refinement` is the exact wrapped source, while `changeApproval.instruction`
retains the original user direction.

Targeted validation (injected fixture model only; no live inference):

```powershell
& .\.intent-to-impact\studio\.venv\Scripts\python.exe -m unittest discover -s .\tests\studio -p "test_design_changes.py" -v
```

External integrations use `service=External HTTPS API` separately from their business
name. `externalDependency.name` and `sourceId` must identify an affirmative existing,
retained or user-owned integration in that source. The server binds `quote` to the
literal source clause, instead of trusting a model-authored quotation or comparing
a technical service label with prose. Unknown, proposed, negated and mismatched
dependencies still fail closed. The initial model proposal is retained separately
for debugging; it is not promoted to a validated result.

Results are **model proposals**, not compiler/security/business approval. Build
generation imports `studio.bundle.build_bundle` lazily and passes only the stored,
validated result. Its actual compiler outcome is returned unchanged; deployment
is never performed. Bundle generation has its own compiler timeout.

Build-only topology restrictions now apply to the selected alternative. A
duplicate edge in an unselected alternative does not block a supported choice;
the full result still undergoes schema and reference validation. Selected
self-connections and duplicate directed pairs are rejected with edge/option IDs.
Queue direction determines sender/receiver permissions, never descriptive labels.
Concrete endpoint-ID examples in the model prompt avoid confusing component kinds
such as `servicebus` with actual node IDs; unknown IDs remain validation failures.

The UI's **Deploy to Azure** feature is a verified-file/manual portal handoff,
not a backend provisioning endpoint. No template is automatically uploaded,
no target is preselected and no portal result is promoted to local deployment
success. Actual resource creation remains unverified pending target values and
separate approval.

## Validation and evidence

Latest targeted checks: 25 bundle tests (including real compiles), 19 model/
validation tests and 16 contextual approval tests. Both browser-driven assurance
actions produced fresh synthesis and independent review, followed by compiled
downloads. The exact original package case also regenerated successfully twice.
These are scoped results; see the user guide for the no-deployment boundary.
Raw evidence is intentionally operator-local and excluded from Git.

```powershell
& .\.intent-to-impact\studio\.venv\Scripts\python.exe -m unittest discover -s .\tests\studio -p "test_*.py"
& .\.intent-to-impact\studio\.venv\Scripts\python.exe .\apps\control-plane\studio\live_smoke.py
```

Tests explicitly inject fake clients; the default client is always live.
`first_smoke.py` reuses the previously working bounded SDK spike but saves new
synthetic proof in a unique `.intent-to-impact\spikes\STUDIO-LIVE-API` subfolder.
`live_smoke.py` exercises final HTTP routes in-process using synthetic sources,
then writes immutable response IDs, durations and hashes. It leaves no server
running and never overwrites historical receipts.
