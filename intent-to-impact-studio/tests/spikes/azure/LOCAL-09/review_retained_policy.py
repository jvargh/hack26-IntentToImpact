"""Re-review hash-verified real captured policy evidence; no new Azure requests."""

import shutil
import stat

from evidence import DECISION, OWNED, ROOT, SOURCE, ReadOnlyRun, load, require, sha
from prepare import policy_review


SNAPSHOT = OWNED / "candidate-20260913T012617540781Z"


class CapturedPolicies:
    def __init__(self, run, entries):
        self.root, self.receipt, self.entries = run.root, run.receipt, entries
        self.consumed = []

    def rest(self, key, identifier, api):
        require(api == "2023-04-01" and identifier in self.entries, "Uncaptured policy evidence; do not invent a response")
        entry = self.entries[identifier]
        require(sha(entry["path"]) == entry["sha256"], "Captured policy changed")
        self.consumed.append({"definitionId": identifier, "sourceFile": entry["path"].name, "sha256": entry["sha256"]})
        return load(entry["path"])


def main():
    run = ReadOnlyRun("policy-snapshot-review")
    try:
        source = load(SNAPSHOT / "receipt.json")
        require(source["azureMutationCommandsExecuted"] == 0, "Expected a read-only source snapshot")
        manifest = load(SNAPSHOT / "candidate-manifest.json")
        require(sha(DECISION) == manifest["decisionSha256"], "Decision changed since original preflight")
        definitions = {}
        for command in source["commands"]:
            for stream in ["stdout", "stderr"]:
                require(sha(SNAPSHOT / command[stream]["file"]) == command[stream]["sha256"], "Captured command evidence changed")
            if command["id"].startswith("policy-definition-"):
                path = SNAPSHOT / command["stdout"]["file"]
                definitions[load(path)["id"]] = {"path": path, "sha256": command["stdout"]["sha256"]}
        captured = CapturedPolicies(run, definitions)
        result = policy_review(captured, load(SNAPSHOT / "policy-assignments.stdout.txt"))
        source_copy = run.root / "reviewer-source"
        source_copy.mkdir()
        source_hashes = {}
        for name in ["prepare.py", "guards.py", "evidence.py", "review_retained_policy.py"]:
            target = source_copy / name
            shutil.copyfile(SOURCE / name, target)
            source_hashes[name] = sha(target)
            target.chmod(stat.S_IREAD)
        run.receipt.update({
            "purpose": "local-re-review-of-real-policy-snapshot",
            "evidenceOrigin": "live-local", "underlyingEvidenceOrigin": "live-external",
            "freshAzureReadsPerformed": False,
            "sourceReceipt": str((SNAPSHOT / "receipt.json").relative_to(OWNED)),
            "sourceReadWindow": [source["startedAt"], source["finishedAt"]],
            "sourceCompiledSha256": manifest["compiledSha256"],
            "consumedPolicyEvidence": captured.consumed,
            "reviewerSourceHashes": source_hashes,
        })
        require(not result["blockers"], "Unresolved policy effects remain")
        run.finish("retained-policy-evidence-reviewed-no-unresolved-write-effects")
    except Exception as error:
        run.receipt["failure"] = str(error)
        run.finish("policy-review-blocked")
    print(str((run.root / "receipt.json").relative_to(ROOT)))
    return 1 if run.receipt["status"] == "policy-review-blocked" else 0


if __name__ == "__main__":
    import argparse
    argparse.ArgumentParser(description=__doc__).parse_args()
    raise SystemExit(main())
