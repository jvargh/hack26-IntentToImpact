# SPK-02-01: bounded Windows file-safety proof

Run from the workspace root:

```powershell
python .\tests\spikes\file_safety\run_spike.py
```

The runner preserves actual command output, source hashes, timestamps and the unittest
result under `.intent-to-impact\spikes\SPK-02-01\<run-id>\`. Tests use isolated owned
temporary directories and clean them up.

The experiment covers atomic same-directory replacement, revision rejection,
serialization failure, cross-process single-writer exclusion, normal process restart,
deliberate process interruption before replacement, unreferenced artifacts and
preservation of unrelated file bytes.

An interrupted writer intentionally exits with code 23. The test requires the prior
case bytes to remain unchanged and the OS lock to be released; the surviving staged
file is not promoted into the case. The test suite also requires an actual competing
process to fail with a `writer-busy` diagnostic.

This is not the production state store. It does not establish power-loss durability,
distributed locking, untrusted-root protection or Azure runtime correctness. The later
file-store task must use the approved contracts and add its own integration tests.
