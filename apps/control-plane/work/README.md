# FND-04-01 — bounded durable work coordinator 1.0.0

`WorkCoordinator` coordinates local work using the accepted **CaseStore as the only
writer** and the accepted **Policy as the authority boundary**. It does not run
models, providers, commands, an HTTP/SSE server, background workers or a scheduler.
It creates no approvals and performs no business eligibility evaluation.

## Consumption and authority

```python
from work import WorkCoordinator

work = WorkCoordinator(case_store, policy, stored_run_id)
queued = work.enqueue(
    trusted_entry, request_projection,
    idempotency_key=client_idempotency_key,
    payload=validated_domain_input,
    dependencies={"requirements": current_requirement_reference},
    facts=owning_engine_facts,
)
claimed = work.claim(
    worker_entry, queued.work_id,
    expected_revision=current_case_revision, facts=fresh_engine_facts,
)
# A separately authorized future runner may execute the command. This package does not.
completed = work.complete(
    worker_entry, claimed.work_id, claimed.claim_id,
    expected_revision=latest_revision, result_ref=stored_validated_result_reference,
    facts=latest_engine_facts,
)
```

The future trusted adapter supplies opaque policy entry/fact handles, never a
client/model E08. Every entry needs `read-case` **and** an explicit grant for the
work capability. New enqueue/claim/complete/fail operations are guarded by policy
with current engine facts/revision. Domain input validation and proof eligibility
remain the owning engine's responsibility.

Only registry profiles **read**, **propose**, and **provider** can represent work.
Human approvals, materialization and operator deploy/seed/reset/verify commands
are deliberately **not background jobs**: the current policy provides no delegated
system-worker authority for these human-only actions. There is no bypass or
impersonation to make them runnable. Models may enqueue only their permitted local
requests. Claim/complete/fail/reconcile require a trusted **system/worker** entry.
Live provider jobs still require the policy's live mode and explicit engine
execution authorization, but this coordinator never executes them.

## APIs

| API | Behavior |
| --- | --- |
| `enqueue(entry, request, idempotency_key=..., payload=..., dependencies=..., facts=...)` | Persist queued E03, immutable metadata, E04 and idempotency record in one case commit |
| `read_work(entry, work_id)` | Read current E03 status and validate its metadata reference |
| `claim(worker, work_id, expected_revision=..., facts=...)` | Queued → running; persist one claim/actual executor before any future external work |
| `complete(worker, work_id, claim_id, expected_revision=..., result_ref=..., facts=...)` | Running → succeeded only with exact claim owner, current dependencies and captured result reference |
| `fail(worker, work_id, claim_id, expected_revision=..., error_ref=..., facts=...)` | Running → failed using an actual stored, validated E07 |
| `reconcile(worker, work_id, expected_revision=...)` | Running → recovery-required; queued changed inputs → stale; valid queued/terminal work stays unchanged |
| `acknowledge_presentation(human_entry, work_id, presentation_id=..., seen_sequence=..., expected_revision=...)` | Idempotent E04-linked local presentation metadata; no approval or Human Attention claim |

Mutating transitions return `TransitionReceipt(work_id, receipt_ref, status, reused,
claim_id)`. `claim_id` is returned only on a successful new claim. The receipt reference
points to an immutable **schema-valid E03 snapshot**; an enqueue retry therefore returns
the same original queued receipt even if that work has since progressed. Use
`read_work` for current status. A reused receipt is history, not fresh runtime proof.

Inputs use the policy's local request projection: capability, actionId, subjectId,
expectedRevision, boundChecksums. For propose/provider jobs, **every bound input must
be a pinned current D01 section reference** in `dependencies`, with exactly matching
checksum keys. This bounded interface intentionally does not support arbitrary
external/free-floating dependency selectors. Payloads are JSON objects limited to
64 KiB; top-level caller/activity/scope authority fields are forbidden.

## Durable representation and shared hashing

- `case.json.work`: schema-valid E03 snapshots and checkpoints.
- `case.json.events`: authoritative ordered E04 events, unique IDs and contiguous
  sequence numbers. `events.ndjson` remains CaseStore's derived/rebuildable export.
- `case.json.idempotencyRecords`: existing core shape, returning immutable E03 refs.
- E03 first checkpoint: immutable local work metadata ref; includes command, input
  payload, dependency refs, trusted E08 ref and registry-owned activity class.
- Later checkpoints: claim and captured result/error refs.
- E04 `payloadRefs`: immutable event metadata, actual E08, work snapshot and relevant
  claim/result/presentation refs. No undeclared E03/E04/D01 root fields are added.

All persisted artifacts use `CaseStore.put_artifact/read_artifact`; all state changes
use `CaseStore.commit`. All canonical checksums use accepted `seal`/`canonical_bytes`,
including the **shared trailing newline**. State and policy sources are not edited.
The accepted policy checksum correction is exercised by reading stored E08 artifacts.

The E04 `actor` comes from the actual trusted entry executing the transition.
An originating human or trusted human initiator is retained separately through
automatic work. It never changes a worker into a human approver.
`activityClass` comes from the policy registry, stored in immutable metadata rather
than an undeclared root field. For example, local `validate-contracts` stays
`demo-operator`; generation requests stay `product-workflow`.

## Idempotency, concurrency and recovery

- Same enqueue key + request/payload/dependencies/caller → same receipt, no new event.
  Original `expectedRevision` is excluded from the identity hash so a lost response
  can be resolved after the accepted commit changed revision.
- Changed input with the same key → explicit `idempotency-conflict`.
- Same completion claim/status/result reference → same receipt, even after a lost
  commit response. Changed result or changed executor cannot silently replace it.
- Claim is one-shot: a running item is never claimed again. There are no leases,
  lease stealing, fencing or worker retry loops.
- Stale expected revisions are explicit. **There is no automatic commit retry**.
  The caller may reload current status and hashes, obtain fresh engine facts, and
  retry if only an unrelated revision changed. Relevant dependency changes deny.
- A CaseStore commit race is surfaced unchanged; no second writer or own JSON
  replacement strategy is introduced.
- Failure before case replacement may leave unreachable immutable artifacts. They
  are not canonical success and are not automatically deleted.
- Failed capture leaves work running. Restart/reconcile makes an uncertain outcome
  `recovery-required`, not queued/succeeded. It does not re-execute any external call.
  Operator/owning-engine resolution is intentionally outside this task.
- Work/idempotency caps of 1,000 and event cap of 10,000 reject new writes; records
  are never pruned. Claims/finishes consume idempotency slots too. Internal
  `claim:`, `finish:`, `reconcile:`, `presentation:` keys are reserved.

A derived export failure is logged by the accepted store after canonical commit;
it does not erase canonical events. Call `CaseStore.rebuild_event_projection` when
needed. This is not an external message-broker outbox or delivery guarantee.

## Presentation / E05 boundary

E05/seen semantics were coordinated with contracts-owner. No accepted E05 is consumed
or generated here. Presentation acknowledgements are explicitly **noncanonical local
work metadata** referenced by valid E04, with a same-work existing event sequence.
Only a trusted human adapter may acknowledge; duplicates add no events. They do not
prove rendering, user attention, question presentation, elapsed away time, completion
or consent, and do not produce Product Human Attention / Operator Action metrics.
The future E05 owner must define those canonical semantics before reporting counts.

## Tests and evidence

From repository root, use the existing contracts environment:

```powershell
& .\contracts\.venv\Scripts\python.exe -B -m unittest discover -s .\tests\work -p test_coordinator.py -v
& .\contracts\.venv\Scripts\python.exe -B .\tests\work\record_evidence.py
```

Tests use fixture inputs and actual isolated local storage directories beneath
`.intent-to-impact\spikes\FND-04-01\`; those per-test directories are cleaned.
A bounded child interpreter proves cross-process restart reading; no long-lived
background process is launched. Tests cover idempotency/conflicts, attribution,
dependency staleness, a concurrent unrelated commit, before/after-commit faults,
failed capture, export interruption/rebuild, uncertain reconciliation, caps, and
presentation deduplication. Evidence pins core/state/policy source hashes.

Limits: no cloud/runtime proof, power-loss guarantee, hostile OS-owner protection,
distributed locking, domain result validation, canonical E05/attention accounting,
HTTP/SSE transport, automatic retries or UX gate approval.
