"""Read-only diagnostics for the retained policy-blocked artifact; cannot create resources."""

from bootstrap import (
    APPROVAL_FILE, LOCATION, OWNED, SCENARIO_FILE, SUB_SCOPE,
    Run, inspect_template, load, now, require, sha, validate_inputs,
)


BLOCKED_RUN = OWNED / "create-a001-20260913T001027370380Z"


def main():
    run = Run(False)
    try:
        prior = load(BLOCKED_RUN / "receipt.json")
        artifact = BLOCKED_RUN / "artifacts"
        require(prior["status"] == "blocked" and prior["azureMutationAttempted"] is False,
                "This diagnostic requires the retained non-mutating blocked run")
        require(all(sha(artifact / name) == checksum for name, checksum in prior["artifactHashes"].items()),
                "Immutable blocked artifacts changed")
        require(sha(APPROVAL_FILE) == prior["approvalFileSha256"], "Approval changed")
        require(sha(SCENARIO_FILE) == prior["scenario"]["fileSha256"], "Scenario changed")
        validate_inputs(load(APPROVAL_FILE), load(SCENARIO_FILE), load(artifact / "main.parameters.json"))
        inspect_template(load(artifact / "main.arm.json"))
        run.receipt["purpose"] = "read-only-policy-blocker-diagnostics"
        run.receipt["blockedArtifactReceipt"] = str((BLOCKED_RUN / "receipt.json").relative_to(OWNED))
        run.receipt["creationDisabled"] = True
        run.copy_auth()
        exemptions = run.data("existing-scope-exemptions", [
            "policy", "exemption", "list", "--scope", SUB_SCOPE, "--filter", "atScope()",
        ], required=False)
        run.receipt["exemptionReadSucceeded"] = exemptions is not None
        common = [
            "--location", LOCATION, "--name", run.deployment_name,
            "--template-file", artifact / "main.arm.json",
            "--parameters", "@" + str(artifact / "main.parameters.json"),
            "--validation-level", "Provider",
        ]
        run.data("blocked-target-validation", ["deployment", "sub", "validate", *common],
                 required=False, timeout=240)
        run.data("blocked-target-what-if", ["deployment", "sub", "what-if", *common,
                 "--no-pretty-print", "--result-format", "FullResourcePayloads"],
                 required=False, timeout=300)
        run.absence("post-diagnostics")
        run.receipt["status"] = "blocked-inherited-policy-no-creation"
    except Exception as error:
        run.receipt["status"] = "blocked-diagnostics-incomplete-no-creation"
        run.receipt["failure"] = run.redact(f"{type(error).__name__}: {error}")
    finally:
        run.cleanup_local_auth()
        run.receipt["finishedAt"] = now()
        run.save()
    print(run.receipt["status"])
    print(str((run.root / "receipt.json").relative_to(OWNED)))


if __name__ == "__main__":
    main()
