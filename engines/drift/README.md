# ENG-03-01 — deterministic CP-01 and PromiseCoverage

This pure local evaluator consumes the **accepted normalized contracts**, not Azure
SDK responses, model answers, environment variables, persistence, or UI decisions.
It evaluates only the V2 CP-01 public-endpoint storage configuration. There is no
private-network requirement and no all-service verifier or finding lifecycle.

V2 is historical under LOCAL-09. This accepted seam does not verify the current
NSP topology; that requires the separately published V3 contract and evaluator
adaptation. No existing V2 evaluation may be relabelled NSP proof.
V2 is historical fixture semantics, not proof of deployment or NSP enforcement.
V3/NSP migration is outside this packet; no human gate is claimed.

## Imports and API

Use the existing contracts virtual environment. Put the repository root,
`apps\control-plane`, and `contracts\generated\1.0.0\python` on the consumer's
`PYTHONPATH`. The test-only `tests\drift\bootstrap.py` sets these roots for tests.
The input dataclass references the generated D22, scenario, D03, D13, D14, D15,
E01 and reference types directly; **schemas and generated files are not copied**.

```python
from engines.drift import EvaluationInput, evaluate_cp01, project_coverage

inputs = EvaluationInput(
    run=trusted_d22,
    scenario=canonical_scenario,
    promise_contract=confirmed_d03,
    binding=d14,
    snapshot=d15,
    evidence=tuple(e01_records),
    operations=tuple(d13_receipts),
    external_references=tuple(trusted_d10_d12_references),
    trusted_sources=tuple(authenticated_d15_and_e01_references),
)
evaluation = evaluate_cp01(
    inputs,
    as_of="2026-09-12T17:05:00Z",
    artifact_id="ART-EVALUATION-CP01",
    evaluation_id="EVALUATION-CP01",
    logical_revision=0,
)
coverage = project_coverage(inputs, evaluation)
```

The caller supplies the cutoff, IDs, revision and immutable run context. Repeating
the same call returns the same D17 bytes/hash and does not mutate its inputs.
`state.case_store.seal`/`canonical_bytes` perform output hashing; the contracts
integrity helper supplies scenario/verifier checksums and reference validation.

## Trust and eligibility

**Schema validity, a checksum, `eligibility: eligible`, collector metadata, and a
caller-written origin do not authenticate a provider.** `trusted_sources` is an
explicit trusted-adapter/caller boundary: exact D15 and E01 artifact links must
have been authenticated outside this module. Do not populate it from untrusted
request JSON. Empty pins yield unknown; fabricated or mismatched pins are rejected.
The adapter must authenticate the raw source checksum, normalized property values,
assertion support, resource/scope and capture times. This module cannot recover
those facts from a self-declared E01. D22, D03 confirmation and baseline receipts
are also trusted caller inputs, not authorization decisions made here.

Every loaded record and reference is checked through the existing frozen-schema
and integrity helpers. A bound D14 needs its acknowledged D13 and exact trusted
D10/D12 links. D03, D14, D15, E01 and D22 must agree on run/case/scope, scenario
ID/version/hash, referenced content and baseline; the selected resource must be
in the trusted scope. Historical V1 evidence is never rebound to a V2 run.

The origin matrix for this **provider-configuration** verifier is:

| Run mode | Permitted evidence origins |
| --- | --- |
| live | live-external |
| fixture | fixture, ux-mock |
| replay | replayed |

Origins are always preserved. Live-local test execution is not Azure configuration
proof. Mode eligibility is necessary but not sufficient: E01 must also be trusted,
explicitly eligible, complete, assertion-linked and fresh. Observed/retrieved/
collected times must be ordered, within the snapshot window, after binding and no
later than the injected cutoff. An explicit expiry is exclusive; the scenario's
maximum age is inclusive. A null expiry does not disable the maximum-age rule.

## Verdicts

- All four exact typed values must match to verify: publicNetworkAccess
  `Enabled`, supportsHttpsTrafficOnly `true`, allowBlobPublicAccess `false`,
  minimumTlsVersion `TLS1_2`.
- Runtime verification additionally needs confirmed CP-01, a complete bound
  baseline, a complete snapshot without gaps/errors, and eligible proof for every
  predicate. Fixture success remains labelled fixture.
- A conclusive current mismatch is breached even when another property is
  missing/null or the snapshot is partial. Missing/partial alone is unknown.
- Null and absent properties have different reason codes. Booleans cannot be
  replaced with integers 0/1. Conflicting observations are unknown, not ordered
  arbitrarily into a pass or breach.
- Expired evidence for otherwise fully matching prior proof is stale, including
  a mixture of current matching predicates and expired matching predicates.
  An expired mismatch is not a current breach; incomplete old proof is unknown.
  A stale/unavailable binding is unknown because there is no eligible baseline.
- Design and delivery return unknown/unsupported-phase, never runtime verified.
  No not-applicable decision, exception approval, finding, closure or Human
  Attention event is invented.

Every D17 is schema-validated and reference-validated before return. Invalid
structure, checksum, references or context raise the existing validation/integrity
errors; structurally valid but missing/untrusted/ineligible proof returns unknown.

## Coverage

`project_coverage` produces the accepted P01 `CoverageSummary` fragment. It
recomputes the selected CP-01 D17 against exactly the supplied inputs before using
it; a fabricated verified/exception record cannot increase coverage. Other
promises remain unknown, including unconfirmed CP-05. There is no fixed 7/8 count.
The projection is as-of its input evaluation, not a silently refreshed wall clock.

`reduce_coverage` is the smaller arithmetic seam for **already trusted runtime
rows**. It is not a verifier and must not receive untrusted/UI-authored rows. A
future caller supplying other verifiers or approved applicability exclusions owns
their evaluation/reference/approval checks. Unknown and stale promises remain in
the denominator; only approved not-applicable rows are excluded, never verified.
Zero applicable rows yields not-assessed and counts 0/0 (no percentage).
Unresolved applicable rows yield partial; wholly resolved applicable rows yield
assessed. Null means no producer assessment in the contract; this reducer has
actually counted the supplied rows and therefore emits integers.

## Validation and evidence

From the repository root:

```powershell
& contracts\.venv\Scripts\python.exe -B -m unittest discover -s tests\drift -p 'test_*.py' -q
& contracts\.venv\Scripts\python.exe -B tests\drift\record_evidence.py
```

The evidence recorder writes only
`.intent-to-impact\spikes\ENG-03-01\evidence.json` and `verdict-fixtures.json`.
The prior 48-test receipt and verdict bytes are preserved under
`history\before-unicode-interoperability` in that same evidence folder.
It records commands/results, source and frozen-input hashes, deterministic
fixture verdicts and rejected-input cases. The 256-case predicate product covers
every combination of matching/mismatching/null/absent values. Counts are tested
over varying row counts. All full-verdict evidence is fixture-origin; an isolated
origin-matrix unit test uses synthetic metadata only, not provider proof.

The positive Unicode regression uses an independent, internally consistent
`rg-caf\u00e9-\u6f22` fixture scope/resource context. It exercises the actual
store create/write/commit/restart/read paths, the policy's read-only system E08,
shared integrity validation, evaluator D17/coverage and graph P06. Every artifact
retains exactly the same checksum across those components. Tampered content and
references still fail. No validation is patched and no alternate serializer is
used. Isolated `unicode-store-*` roots stay under the task evidence directory and
are removed after the test; the evaluator itself remains pure.

### Known limitations

No Azure read, raw-source authentication, authorization, persistence, refresh
scheduler, applicability approval, business gating, recovery/billing verifier,
resource graph, finding lifecycle or full P01 join is implemented by this engine.
Real store/policy calls in the integration test are local test activity, not
provider evidence or a product/human approval.
