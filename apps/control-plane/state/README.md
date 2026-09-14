# FND-02-01: local case store

The `CaseStore` is a bounded Windows/local-filesystem persistence component.
It consumes frozen core JSON Schemas; it is not an HTTP API, workflow engine,
authentication service, approval bypass, scheduler, or cloud adapter.

- One atomically replaced `case.json` owns the current logical revision and references.
- Immutable `run-manifest.json` fixes run mode, purpose, case, scenario and scope.
- Domain section payloads live in immutable content-addressed artifact files.
- Events remain in `case.json`; `events.ndjson` is rebuildable, non-authoritative output.
- OS-backed writer exclusion has no lease stealing, fencing or distributed behavior.
- Malformed JSON, checksum mismatch, duplicate keys and stale revisions fail explicitly.
- Artifacts are not active until a committed case references them.
- Neither a local case commit nor a materialized file attests to Azure deployment.

Callers are trusted owning engines. They must apply the command policy, state-machine
rules, approvals and idempotency before committing. This component does not infer
eligibility from the supplied document. The future API must not expose raw `commit`
or accept a browser-selected root.

Current run layout:

```text
<server-configured-root>\
  <run-id>\
    run-manifest.json
    artifacts\<checksum>.json
    cases\<case-id>\
      case.json
      writer.lock
      events.ndjson
```

Use the pinned validator environment from the core contract task:

```powershell
& .\contracts\.venv\Scripts\python.exe -B -m unittest discover -s .\tests\state -p test_case_store.py -v
& .\contracts\.venv\Scripts\python.exe -B .\tests\state\record_evidence.py
```

Tests use owned temporary directories, real cross-process writer contention, bounded
interruption injection, restart, immutable-mode checks and preserved unrelated files.
They do not prove power-loss durability, hostile OS-user protection or arbitrary
network/cloud-sync filesystem support. An externally modified artifact is a conflict,
not a reason to silently repair or overwrite user bytes.

After an event-export failure, the canonical commit is still valid and a warning is
logged; `rebuild_event_projection` derives the export again from committed events.
No projection failure is converted into an unrecorded approval or runtime success.
