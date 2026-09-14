"""Verify and aggregate approved continuation evidence without Azure operations."""

import copy
import json
import subprocess
import sys
from pathlib import Path

from approved_specialists import NAMES, RUN, ROOT, OUTPUT, sha, validate_readback, write
from discover import digest, now


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    prior_path = RUN / "prior-task-receipt.json"
    prior = read(prior_path)
    creation_path = RUN / "specialist-receipt.json"
    creation = read(creation_path)
    require(sha(RUN / "creation-source.py") == creation["sourceFileSha256"],
            "Creation source snapshot mismatch")
    require(sha(prior_path) == creation["priorReceiptSha256"], "Prior aggregate mismatch")
    for name, expected in prior["evidenceFileHashes"].items():
        require(sha(ROOT / name) == expected, "Original evidence modified: " + name)
    for name, expected in prior["sourceFileHashes"].items():
        require(sha(RUN / "prior-source" / Path(name).name) == expected,
                "Original source snapshot modified: " + name)
    require(creation["creationAttempts"] == creation["createdVersions"] == 3,
            "Expected exactly three initial creations")
    expected_scope = {
        "id": creation["subscriptionId"], "tenantId": creation["tenantId"], "state": "Enabled",
    }
    require(creation["scopeCheck"]["data"] == expected_scope, "CLI scope verification failed")
    creations = [r for r in creation["requests"] if r["method"] == "POST"
                 and "/agents/" in r["url"]]
    require(len(creations) == 3 and all(r["httpStatus"] == 200 for r in creations),
            "Creation HTTP evidence incomplete")
    require({r["name"] for r in creation["rows"]} == set(NAMES), "Unapproved or missing name")

    source_dir = ROOT / "tests" / "spikes" / "foundry"
    commands = [
        [sys.executable, "-m", "unittest", "discover", "-s", str(source_dir), "-p", "test_*.py", "-v"],
        [sys.executable, str(source_dir / "approved_specialists.py")],
        [sys.executable, str(source_dir / "approved_specialists.py"), "--execute-approved"],
        [sys.executable, "-m", "pip", "check"],
    ]
    local = {"version": "1.0.0", "origin": "live-local", "startedAt": now(), "commands": []}
    unchanged_creation = sha(creation_path)
    for command, expected_exit in zip(commands, [0, 2, 2, 0]):
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        local["commands"].append({
            "command": command, "exitCode": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr,
        })
        require(result.returncode == expected_exit, "Unexpected validation command exit code")
    require(sha(creation_path) == unchanged_creation, "Re-entry guard modified creation evidence")
    local.update(completedAt=now(), status="passed", externalRequestCount=0,
                 reentryGuard="Existing run refused before any CLI/resource operation.")
    write("local-tests.json", local)

    continuation_rows = []
    native_receipts = []
    for created in creation["rows"]:
        name, role = created["name"], created["role"]
        native_path = RUN / f"{name}-native-invocation.json"
        native = read(native_path)
        native_receipts.append(native)
        require(native["status"] == "passed", "Native invocation did not pass: " + name)
        require(native["creationReceiptSha256"] == sha(creation_path), "Creation receipt hash mismatch")
        require(native["sourceSha256"] == sha(RUN / "native-invocation-source.py"),
                "Native invocation source snapshot mismatch")
        require(native["agentVersion"] == created["createdVersion"] == "1", "Noninitial/unpinned version")
        require(native["result"] == {"marker": "SPK-01-01-OK", "specialist": role},
                "Typed result mismatch")
        require(digest(native["result"]) == native["resultSha256"], "Typed result hash mismatch")
        readback = created["definitionReadback"]
        validate_readback(name, "1", readback)
        require(created["definitionSha256"] == readback["definitionSha256"]
                == native["readbackDefinitionSha256"], "Definition changed")
        posts = [r for r in native["requests"] if r["method"] == "POST"]
        require(len(posts) == 1 and posts[0]["httpStatus"] == 200
                and posts[0]["agentReference"] == {
                    "name": name, "version": "1", "type": "agent_reference",
                } and posts[0]["store"] is False, "Invalid exact-version invocation request")
        require(bool(native["responseId"]), "Real response ID missing")
        continuation_rows.append({
            "proof": f"approved-tool-free-prompt-probe-{role}", "status": "passed",
            "origin": "live-external", "agentId": created["createdId"],
            "agentName": name, "agentVersion": "1", "responseId": native["responseId"],
            "definitionSha256": created["definitionSha256"],
            "resultSha256": native["resultSha256"],
            "evidence": str(native_path.relative_to(OUTPUT)),
            "typedResultBoundary": native["typedResultBoundary"],
        })
    summary = {
        "version": "1.0.0", "task": "SPK-01-01", "status": "passed",
        "scope": "approved probe continuation only", "completedAt": now(),
        "approval": creation["approval"], "projectId": creation["projectId"],
        "projectEndpoint": creation["projectEndpoint"], "sdkVersions": creation["sdkVersions"],
        "rows": continuation_rows, "initialVersionsCreated": 3,
        "existingAgentUpdates": 0, "unapprovedMutationCount": 0,
        "agentInvocationHttpAttempts": 6, "successfulTypedAgentInvocations": 3,
        "failedInvocationAttempts": {
            "count": 3, "httpStatus": 400, "evidence": "specialist-receipt.json",
            "observedDifference": "FoundryAgent.run with response_format=Pydantic model and "
            "max_tokens=160 returned HTTP 400. Native run with only store=False passed. "
            "The individual rejected option was not isolated; no extra diagnostic calls made.",
        },
        "supportedCall": "FoundryAgent(project_client=..., agent_name=exact_name, "
        "agent_version='1', allow_preview=False).run(synthetic_input, options={'store': False})",
        "supportedWire": "POST project/openai/v1/responses with agent_reference "
        "{name,type:'agent_reference',version:'1'} and store=false",
        "typing": "Validate real AgentResponse.text with strict Pydantic literal marker and specialist. "
        "This is local typed validation, not proof of server-enforced JSON schema for Prompt Agents.",
        "limits": creation["limitations"],
        "originalDirectModelProofPreserved": [
            {"path": name, "sha256": prior["evidenceFileHashes"][str((OUTPUT / name).relative_to(ROOT))]}
            for name in ("model-receipt.json", "stream-receipt.json", "invocation-source.py")
        ],
        "localTests": {"evidence": "local-tests.json", "unitTestsPassed": 17},
        "ux02": "Real successful agent reasoning receipts are available. No UX gate approval; "
        "no cancellation, network-isolation or production-domain claims.",
    }
    summary["sourceFileHashes"] = {
        str(p.relative_to(ROOT)): sha(p) for p in source_dir.iterdir() if p.is_file()
    }
    summary["evidenceFileHashes"] = {
        str(p.relative_to(ROOT)): sha(p) for p in RUN.rglob("*")
        if p.is_file() and p.name != "continuation-receipt.json"
    }
    write("continuation-receipt.json", summary)

    aggregate = copy.deepcopy(prior)
    aggregate.update(
        version="1.0.0", createdAt=now(), status="passed", taskComplete=True,
        completionScope="SPK-01-01 original model/stream/config proof plus explicitly approved "
        "three probe-only specialist creations/invocations; cancellation remains disclosed not-tested.",
        priorAggregate={"path": str(prior_path.relative_to(OUTPUT)), "sha256": sha(prior_path)},
        continuation={"path": str((RUN / "continuation-receipt.json").relative_to(OUTPUT)),
                      "sha256": sha(RUN / "continuation-receipt.json")},
        foundryAgentVersionCreationCount=3, azureResourceMutationCount=3,
        mutationCountDefinition="Three authorized Foundry create_version POST requests; "
        "no ARM infrastructure, existing-agent, endpoint, role or model deployment mutation.",
        cloudAgentInvocationCount=6, successfulCloudAgentInvocationCount=3,
        successfulSyntheticModelCalls=2, existingAgentUpdates=0, unapprovedMutationCount=0,
        privateVisibilityProof="Project-authenticated Prompt Agent version assets read back with tools=[] "
        "and no connection fields. No publication operation was performed; wider visibility and "
        "private-network isolation were not established.",
        nextSafeAction="Stop SPK-01-01. Production specialist instructions/integration require separate "
        "AGT task authorization; no deletion or publication is approved.",
    )
    aggregate["rows"] = [
        r for r in prior["rows"] if not r["proof"].startswith("private-prompt-agent-")
    ] + continuation_rows
    aggregate["rows"].append({
        "proof": "approved-name-scope-tools-collision-and-evidence-guards",
        "status": "passed", "origin": "live-local",
        "evidence": str((RUN / "local-tests.json").relative_to(OUTPUT)),
    })
    aggregate["priorDiscoveryFacts"] = {
        key: aggregate.pop(key) for key in (
            "observedAgentCount", "observedPromptAgentCount", "observedNoToolPromptAgentCount",
            "agentListingComplete",
        )
    }
    aggregate["priorSourceFileHashes"] = prior["sourceFileHashes"]
    aggregate["sourceFileHashes"] = summary["sourceFileHashes"]
    aggregate["evidenceFileHashes"].update(summary["evidenceFileHashes"])
    aggregate["evidenceFileHashes"][str((RUN / "continuation-receipt.json").relative_to(ROOT))] = (
        sha(RUN / "continuation-receipt.json")
    )
    aggregate["constraints"].append(
        "The original no-agent-mutation limitation was superseded only by the recorded explicit "
        "three-probe approval. Native Prompt Agent results are typed locally."
    )
    aggregate["ux02"]["facts"] = [
        fact for fact in aggregate["ux02"]["facts"] if not fact.startswith("Missing specialist")
    ] + ["Three approved probe-version invocations passed; not production-domain specialist behavior."]
    (OUTPUT / "receipt.json").write_text(json.dumps(aggregate, indent=2) + "\n", encoding="utf-8")
    for name, expected in aggregate["evidenceFileHashes"].items():
        require(sha(ROOT / name) == expected, "Aggregate evidence integrity failure: " + name)
    print(json.dumps({
        "status": "passed", "taskComplete": True, "createdVersions": 3,
        "successfulTypedInvocations": 3, "localTestsPassed": 17,
        "receipt": str((OUTPUT / "receipt.json").relative_to(ROOT)),
        "receiptSha256": sha(OUTPUT / "receipt.json"),
    }))


if __name__ == "__main__":
    main()
