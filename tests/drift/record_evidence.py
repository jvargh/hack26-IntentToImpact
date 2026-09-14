"""Record local deterministic evidence only in the ENG-03-01 owned output folder."""

from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from bootstrap import ROOT
from fixtures import evaluate_arguments, fixture_input, refresh, unicode_fixture_input
from engines.drift import evaluate_cp01, project_coverage
from state.case_store import canonical_bytes, seal
from tools.contracts.integrity import ReferenceIntegrityError
from tools.contracts.validate import validate_contract, fragment_validator

DESTINATION = ROOT / ".intent-to-impact" / "spikes" / "ENG-03-01"


def record_verdicts():
    base = fixture_input()
    cases = []

    def record(name, inputs, **arguments):
        output = evaluate_cp01(inputs, **evaluate_arguments(**arguments))
        coverage = project_coverage(inputs, output)
        validate_contract(output, "D17")
        fragment_validator("projections", "CoverageSummary").validate(coverage)
        assert all(item["origin"] == "fixture" for item in output["evidence"])
        cases.append({"fixtureId": name, "input": asdict(inputs),
                      "arguments": evaluate_arguments(**arguments),
                      "evaluation": output, "coverage": coverage})

    record("CP01-desired", base)
    record("CP01-unicode-context", unicode_fixture_input())
    for name, action in (
        ("CP01-explicit-https-false", "false"),
        ("CP01-https-null", "null"),
        ("CP01-https-missing", "missing"),
        ("CP01-mismatch-and-unknown", "mixed"),
        ("CP01-partial-snapshot", "partial"),
        ("CP01-unconfirmed-promise", "unconfirmed"),
    ):
        inputs = deepcopy(base)
        properties = inputs.snapshot["observations"][0]["properties"]
        if action == "false":
            properties["supportsHttpsTrafficOnly"] = False
        elif action == "null":
            properties["supportsHttpsTrafficOnly"] = None
        elif action == "missing":
            del properties["supportsHttpsTrafficOnly"]
        elif action == "mixed":
            properties.update(supportsHttpsTrafficOnly=False, minimumTlsVersion=None)
            inputs.snapshot["completeness"] = "partial"
        elif action == "partial":
            inputs.snapshot["completeness"] = "partial"
        else:
            inputs.promise_contract["confirmedPromiseIds"] = []
        record(name, refresh(inputs))
    record("CP01-stale-prior-proof", base, as_of="2026-09-12T17:10:00Z")
    record("CP01-no-binding", refresh(replace(base, binding=None)))
    record("CP01-untrusted", replace(base, trusted_sources=()))
    inputs = deepcopy(base)
    for item in (inputs.run, inputs.promise_contract, inputs.binding, inputs.snapshot, *inputs.operations):
        item["runMode"] = "live"
    record("CP01-fixture-in-live", refresh(inputs))
    for field, name, value in (
        ("scope", "CP01-wrongscope", {**base.run["scope"], "scopeId": "SCOPE-OTHER"}),
        ("scenario", "CP01-wrongscenario", {**base.snapshot["scenario"], "scenarioId": "DEMO-CASE-CLAIMS-V1"}),
        ("scenario", "CP01-wrongscenariohash", {**base.snapshot["scenario"], "scenarioHash": "sha256:" + "0" * 64}),
    ):
        inputs = deepcopy(base)
        inputs.snapshot[field] = value
        inputs = refresh(inputs)
        try:
            evaluate_cp01(inputs, **evaluate_arguments())
        except ReferenceIntegrityError as error:
            cases.append({"fixtureId": name, "input": asdict(inputs),
                          "rejected": type(error).__name__, "reason": str(error)})
        else:
            raise AssertionError(name + " was not rejected")
    return {
        "evidenceOrigin": "live-local", "sourceEvidenceOrigin": "fixture",
        "providerProof": False, "cases": cases,
        "count8unknowns": project_coverage(base, None),
    }


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    commands = [
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", r"tests\drift", "-p", "test_*.py", "-q"],
        [sys.executable, "-B", r"tools\contracts\generate.py", "--bundle", "all", "--check"],
        [sys.executable, "-B", r"tools\contracts\write_risk_examples.py", "--check"],
    ]
    results = []
    for command in commands:
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        results.append({"command": command, "exitCode": run.returncode,
                        "stdout": run.stdout, "stderr": run.stderr})
    verdicts = record_verdicts()
    archive = DESTINATION / "history" / "before-unicode-interoperability"
    previous = json.loads((archive / "verdict-fixtures.json").read_text(encoding="utf-8"))
    current_cases = {case["fixtureId"]: case for case in verdicts["cases"]}
    assert all(
        canonical_bytes(case) == canonical_bytes(current_cases[case["fixtureId"]])
        for case in previous["cases"]
    )
    assert previous["count8unknowns"] == verdicts["count8unknowns"]
    (DESTINATION / "verdict-fixtures.json").write_bytes(canonical_bytes(verdicts))
    source_files = sorted(
        [*ROOT.joinpath("engines", "drift").glob("*.py"),
         ROOT / "engines" / "drift" / "README.md",
         *ROOT.joinpath("tests", "drift").glob("*.py"),
         *ROOT.joinpath("contracts", "schemas", "1.0.0").glob("*.json"),
         ROOT / "contracts" / "registry" / "1.0.0.json",
         ROOT / "contracts" / "examples" / "1.0.0" / "risk-examples.json",
         ROOT / "contracts" / "examples" / "1.0.0" / "run-manifest.json",
         ROOT / "contracts" / "examples" / "1.0.0" / "evidence-reference.json",
         ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json",
         ROOT / "tools" / "contracts" / "validate.py",
         ROOT / "tools" / "contracts" / "integrity.py",
         ROOT / "apps" / "control-plane" / "state" / "case_store.py",
         ROOT / "apps" / "control-plane" / "policy" / "guard.py",
         ROOT / "apps" / "control-plane" / "policy" / "capabilities.v1.json",
         ROOT / "reporting" / "continuity" / "graph.py"]
    )
    receipt = seal({
        "taskId": "ENG-03-01", "evidenceOrigin": "live-local", "providerProof": False,
        "recordedAt": datetime.now(timezone.utc).isoformat(),
        "commands": results,
        "historicalVerdictsUnchanged": True,
        "archivedEvidence": {
            str(path.relative_to(DESTINATION)): "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(archive.glob("*.json"))
        },
        "scenarioSemanticHash": fixture_input().scenario["stateChecksum"],
        "fileHashes": {
            str(path.relative_to(ROOT)): "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_files
        },
        "verdictFixtureHash": "sha256:" + hashlib.sha256(canonical_bytes(verdicts)).hexdigest(),
        "verdicts": [
            {"fixtureId": item["fixtureId"],
             "status": item["evaluation"]["status"] if "evaluation" in item else "rejected",
             "hash": item["evaluation"]["stateChecksum"] if "evaluation" in item else None}
            for item in verdicts["cases"]
        ],
        "limitations": [
            "Historical V2 fixture semantics only; no V3/NSP migration, Azure/provider proof or human gate.",
            "Evaluator remains pure; real store/policy calls are isolated live-local integration tests.",
            "All result proof remains fixture-origin. Synthetic origin-matrix metadata is a unit test, not provider proof.",
            "Trusted caller must authenticate D22/D03/baseline and exact D15/E01 raw source and normalization.",
            "Only CP-01 runtime configuration verifier implemented; other promises stay unknown.",
            "Coverage reducer trusts upstream rows; project_coverage validates/recomputes CP-01.",
        ],
    })
    (DESTINATION / "evidence.json").write_bytes(canonical_bytes(receipt))
    print(json.dumps({
        "taskId": receipt["taskId"], "commandsPassed": all(item["exitCode"] == 0 for item in results),
        "verdictCases": len(verdicts["cases"]), "evidenceChecksum": receipt["stateChecksum"],
    }))
    return 0 if all(item["exitCode"] == 0 for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
