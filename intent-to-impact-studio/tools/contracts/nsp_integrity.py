"""Explicit schema-2/V3 source and relationship validation; never produce a runtime verdict."""

from datetime import datetime, timedelta

from .integrity import ReferenceIntegrityError, semantic_checksum
from .registry_support import select_registry
from .validate import fragment_validator, identify_contract, validate_contract

VERSION = "2.0.0"
LEGACY = "1.0.0"
MEMBERS = ("storage", "perimeter", "profile", "association", "configuration")
COLLECTIONS = ("profileAccessRules", "effectiveAccessRules")


def _require(condition, message):
    if not condition:
        raise ReferenceIntegrityError(message)


def scenario_identity(scenario):
    return {
        "scenarioId": scenario["scenarioId"], "scenarioVersion": scenario["scenarioVersion"],
        "scenarioHash": scenario["stateChecksum"],
    }


def validate_v3_scenario(value):
    validate_contract(value, "SCENARIO-V3", schema_version=VERSION)
    profile = select_registry(VERSION)["scenarioProfile"]
    _require(scenario_identity(value) == {key: profile[key] for key in ("scenarioId", "scenarioVersion", "scenarioHash")}, "Scenario does not match the explicitly published V3 profile")
    _require(semantic_checksum(value) == value["stateChecksum"], "V3 scenario checksum mismatch")
    desired = {"storage": value["desiredStorageConfiguration"], "nsp": value["desiredNspConfiguration"]}
    _require(semantic_checksum(desired) == value["desiredStateChecksum"], "V3 desired-state checksum mismatch")
    _require(semantic_checksum(value["cp01Verifier"]) == value["verifierChecksum"], "V3 verifier checksum mismatch")
    cp01 = next(item for item in value["promises"] if item["promiseId"] == "CP-01")
    _require(set(cp01["componentIds"]) == set(value["boundaryComponentIds"].values()), "CP-01 boundary component mismatch")
    _require(cp01["verifierIds"] == [value["cp01Verifier"]["verifierId"]], "CP-01 verifier linkage mismatch")
    _require(cp01["requiredEvidenceKinds"] == value["cp01Verifier"]["requiredEvidenceKinds"], "CP-01 evidence-kind linkage mismatch")


def validate_v3_run_context(run, scenario):
    """D22 schema1 is genuinely compatible; its scenario tuple must explicitly bind V3."""
    validate_contract(run, "D22", schema_version=LEGACY)
    _require(run["stateChecksum"] == semantic_checksum(run), "Run manifest checksum mismatch")
    _require(
        {key: run[key] for key in ("scenarioId", "scenarioVersion", "scenarioHash")} == scenario_identity(scenario),
        "Source run is not bound to the V3 scenario/version/hash",
    )


def _walk(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _is_link(value):
    return set(value) == {"contractId", "schemaVersion", "artifact", "scenario"}


def _arm_equal(left, right):
    return isinstance(left, str) and isinstance(right, str) and left.casefold() == right.casefold()


def _child_of(child, parent, kind):
    return isinstance(child, str) and isinstance(parent, str) and child.casefold().startswith(parent.casefold() + "/" + kind.casefold() + "/")


def validate_binding_resources(resources):
    fragment_validator("nsp", "BindingResources", schema_version=VERSION).validate(resources)
    _require(_child_of(resources["profileId"], resources["perimeterId"], "profiles"), "Bound profile belongs to a different perimeter")
    _require(_child_of(resources["associationId"], resources["perimeterId"], "resourceAssociations"), "Bound association belongs to a different perimeter")
    _require(_child_of(resources["configurationId"], resources["storageId"], "networkSecurityPerimeterConfigurations"), "Bound configuration belongs to a different storage account")


def _source_ids(observation, resources):
    for member, field in (
        ("storage", "storageId"), ("perimeter", "perimeterId"), ("profile", "profileId"),
        ("association", "associationId"), ("configuration", "configurationId"),
    ):
        value = observation[member]["value"]
        if value is not None and resources[field] is not None:
            _require(_arm_equal(value["id"], resources[field]), f"Observation source {member} ID mismatch")
    for collection, field in (("profileAccessRules", "profileId"), ("effectiveAccessRules", "configurationId")):
        source = observation[collection]["sourceResourceId"]
        if source is not None and resources[field] is not None:
            _require(_arm_equal(source, resources[field]), f"Rule collection source {collection} ID mismatch")


def assert_established_boundary_sources(observation, resources):
    """Validate the supplied proof-view shape/foreign keys; do not evaluate arbitrary snapshots."""
    fragment_validator("nsp", "VerifiedBoundaryObservation", schema_version=VERSION).validate(observation)
    validate_binding_resources(resources)
    _source_ids(observation, resources)
    storage, perimeter, profile, association, configuration = (observation[name]["value"] for name in MEMBERS)
    _require(perimeter["perimeterGuid"].casefold() == resources["perimeterGuid"].casefold(), "Perimeter GUID differs from approved binding")
    _require(_arm_equal(association["privateLinkResourceId"], storage["id"]), "Association targets a different storage account")
    _require(_arm_equal(association["profileId"], profile["id"]), "Association targets a different profile")
    _require(_child_of(profile["id"], perimeter["id"], "profiles"), "Observed profile/perimeter relationship mismatch")
    _require(_child_of(association["id"], perimeter["id"], "resourceAssociations"), "Observed association/perimeter relationship mismatch")
    _require(profile["id"].rsplit("/", 1)[-1].casefold() == profile["name"].casefold(), "Profile name/ID mismatch")
    _require(association["id"].rsplit("/", 1)[-1].casefold() == association["name"].casefold(), "Association name/ID mismatch")
    _require(_arm_equal(configuration["perimeterId"], perimeter["id"]), "Effective configuration perimeter mismatch")
    _require(configuration["perimeterGuid"].casefold() == perimeter["perimeterGuid"].casefold(), "Effective configuration perimeter GUID mismatch")
    _require(configuration["associationName"].casefold() == association["name"].casefold(), "Effective configuration association mismatch")
    _require(configuration["profileName"].casefold() == profile["name"].casefold(), "Effective configuration profile mismatch")
    _require(configuration["accessMode"] == association["accessMode"] == "Enforced", "Effective association is not Enforced")
    _require(configuration["accessRulesVersion"] == profile["accessRulesVersion"], "Effective/profile access rule versions differ")
    for collection, version in (
        ("profileAccessRules", profile["accessRulesVersion"]),
        ("effectiveAccessRules", configuration["accessRulesVersion"]),
    ):
        _require(observation[collection]["accessRulesVersion"] == version, f"Rule collection {collection} version mismatch")


def validate_v3_reference_integrity(documents, runs, scenario, external_references=(), *, require_live=False, as_of=None, current_bindings=None):
    validate_v3_scenario(scenario)
    expected = scenario_identity(scenario)
    compatible = select_registry(VERSION)["compatibleSourceContracts"]
    index = {}
    documents = list(documents)
    if require_live:
        _require(as_of is not None, "Live proof validation requires an explicit current time")
        _require(any(value.get("artifactType") == "promise-evaluation" and value.get("promiseId") == "CP-01" and value.get("status") == "verified" for value in documents), "No verified boundary claim is supplied for live proof")
    for value in documents:
        version = value.get("schemaVersion")
        _require(version in {LEGACY, VERSION}, "Unknown source schema version")
        contract = identify_contract(value, schema_version=version)
        if version == LEGACY:
            _require(contract in {"E01", "E04", "E05"}, "A legacy domain/evaluation cannot qualify as a V3 record")
            _require(compatible.get(contract) == version, "Source contract/version is not explicitly compatible")
        validate_contract(value, contract, schema_version=version)
        key = version, contract, value["artifactId"]
        _require(key not in index, "Duplicate versioned artifact identity")
        index[key] = value
        _require(value["stateChecksum"] == semantic_checksum(value), f"Artifact body checksum mismatch: {key}")
        _require(value["runId"] in runs, "Missing trusted source run")
        run = runs[value["runId"]]
        validate_v3_run_context(run, scenario)
        _require(run["runId"] == value["runId"], "Source run index mismatch")
        for field in ("caseId", "scope"):
            _require(value[field] == run[field], f"Source run {field} mismatch")
        if "scenario" in value:
            _require(value["scenario"] == expected, "Artifact scenario/version/hash mismatch")
            _require(value["runMode"] == run["runMode"] and value["purpose"] == run["purpose"], "Artifact run mode/purpose mismatch")

    external = {}
    for reference in external_references:
        fragment_validator("envelope", "VersionedArtifactReference", schema_version=VERSION).validate(reference)
        _require(reference["contractId"] in {"D10", "D11", "D12"} and reference["schemaVersion"] == VERSION, "Unsupported external canonical reference")
        _require(reference["scenario"] == expected, "External reference scenario mismatch")
        key = reference["schemaVersion"], reference["contractId"], reference["artifact"]["artifactId"]
        _require(key not in external, "Duplicate external reference")
        external[key] = reference

    def resolve(reference, owner, *, loaded=False):
        fragment_validator("envelope", "VersionedArtifactReference", schema_version=VERSION).validate(reference)
        _require(reference["scenario"] == expected, "Reference scenario/version/hash mismatch")
        key = reference["schemaVersion"], reference["contractId"], reference["artifact"]["artifactId"]
        if key not in index:
            _require(not loaded and external.get(key) == reference, f"Unresolved exact-version reference: {key}")
            return None
        target = index[key]
        _require(target["stateChecksum"] == reference["artifact"]["checksum"], "Reference checksum mismatch")
        _require(target["caseId"] == owner["caseId"] and target["scope"] == owner["scope"], "Cross-context source reference")
        if target["runId"] != owner["runId"]:
            run = runs[owner["runId"]]
            _require(run["runMode"] == "replay" and run.get("sourceRunId") == target["runId"], "Cross-run reference is not an explicit replay source")
        return target

    def plain(reference, contract, owner, version=VERSION):
        fragment_validator("core", "ArtifactReference").validate(reference)
        return resolve({"schemaVersion": version, "contractId": contract, "artifact": reference, "scenario": expected}, owner, loaded=True)

    def human_link(reference, owner):
        _require(reference.get("scenario") == expected, "Human source link scenario mismatch")
        _require(reference.get("contractId") in {"E04", "E05"}, "Unversioned domain reference is forbidden")
        return resolve({**reference, "schemaVersion": LEGACY}, owner, loaded=True)

    for value in documents:
        for item in _walk(value):
            if _is_link(item):
                resolve(item, value)
            if set(item) == {"reference", "origin"}:
                evidence = resolve(item["reference"], value, loaded=True)
                _require(evidence["origin"] == item["origin"], "Evidence origin does not match loaded source")
            if "evidenceWindow" in item:
                window = item["evidenceWindow"]
                _require(datetime.fromisoformat(window["from"]) <= datetime.fromisoformat(window["to"]), "Reversed evidence window")
        kind = value["artifactType"]
        if kind == "customer-promise-contract" and "CP-05" in value["confirmedPromiseIds"]:
            matching = [record for (version, contract, _), record in index.items() if version == VERSION and contract == "D02" and record["stateChecksum"] == value["requirementChecksum"]]
            _require(len(matching) == 1 and matching[0]["rpoQuestion"]["status"] == "answered", "Confirmed RPO has no matching V3 requirement source")
        elif kind == "runtime-binding" and value["bindingState"] == "bound":
            validate_binding_resources(value["resources"])
            operation = resolve(value["operationReceipt"], value, loaded=True)
            _require(operation["result"] == "acknowledged" and operation["operation"] in {"deploy-baseline", "restore"}, "Binding has no acknowledged baseline operation")
            for field in ("generationManifest", "applicationReceipt", "desiredStateChecksum"):
                _require(value[field] == operation[field], f"Baseline {field} mismatch")
            _require(value["desiredStateChecksum"] == scenario["desiredStateChecksum"], "Baseline is not the V3 desired profile")
            for field, resource_id in operation["deployedResources"].items():
                _require(_arm_equal(value["resources"][field], resource_id), "Deployment/binding resource mismatch")
        elif kind == "runtime-snapshot":
            if value["binding"] is not None:
                binding = resolve(value["binding"], value, loaded=True)
                _source_ids(value["observation"], binding["resources"])
            for name in (*MEMBERS, *COLLECTIONS):
                slot = value["observation"][name]
                _require(all(link in value["evidence"] for link in slot["evidence"]), "Observation references unlisted snapshot evidence")
        elif kind == "promise-evaluation":
            promises = resolve(value["promiseContract"], value, loaded=True)
            promise = next(item for item in promises["promises"] if item["promiseId"] == value["promiseId"])
            _require(value["verifier"]["verifierId"] in promise["verifierIds"], "Evaluation verifier/promise mismatch")
            if value["promiseId"] == "CP-01":
                _require(value["verifier"]["version"] == scenario["cp01Verifier"]["version"] and value["verifier"]["checksum"] == scenario["verifierChecksum"], "Evaluation uses a different verifier profile")
                _require({item["predicateId"] for item in value["predicateResults"]} <= set(scenario["cp01Verifier"]["assertionIds"]), "Unknown V3 assertion ID")
            if value["runtimeSnapshot"] is not None:
                snapshot = resolve(value["runtimeSnapshot"], value, loaded=True)
                _require(snapshot["binding"] == value["binding"], "Evaluation/snapshot binding mismatch")
                _require(all(link in snapshot["evidence"] for link in value["evidence"]), "Evaluation references unlisted snapshot evidence")
            for predicate in value["predicateResults"]:
                _require(all(link in value["evidence"] for link in predicate["evidence"]), "Predicate references unlisted evidence")
                for link in predicate["evidence"]:
                    evidence = resolve(link["reference"], value, loaded=True)
                    _require(predicate["predicateId"] in evidence["supportedAssertionIds"], "Evidence does not support the stated assertion")
            if value["promiseId"] == "CP-01" and value["status"] == "verified":
                _require(
                    len(value["predicateResults"]) == len(scenario["cp01Verifier"]["assertionIds"])
                    and {item["predicateId"] for item in value["predicateResults"]} == set(scenario["cp01Verifier"]["assertionIds"])
                    and all(item["result"] == "pass" and item["evidence"] for item in value["predicateResults"]),
                    "Verified claim omits a declared passing assertion source",
                )
                proof = value["boundaryEvidence"]
                _require(proof["snapshot"] == value["runtimeSnapshot"] and proof["binding"] == value["binding"], "Boundary evidence reference mismatch")
                snapshot = resolve(proof["snapshot"], value, loaded=True)
                binding = resolve(proof["binding"], value, loaded=True)
                _require(snapshot["completeness"] == "complete" and binding["bindingState"] == "bound", "Verified claim lacks complete snapshot/binding")
                _require(proof["observation"] == snapshot["observation"], "Boundary view differs from its source snapshot")
                assert_established_boundary_sources(proof["observation"], binding["resources"])
                at = datetime.fromisoformat(as_of or value["evaluatedAt"])
                if require_live:
                    _require(as_of is not None and value["runMode"] == "live", "Fixture/replay is not live proof")
                for name in (*MEMBERS, *COLLECTIONS):
                    slot = proof["observation"][name]
                    observed_slot = datetime.fromisoformat(slot["observedAt"])
                    _require(observed_slot <= at <= observed_slot + timedelta(seconds=scenario["cp01Verifier"]["maxEvidenceAgeSeconds"]), "Observation is stale or from the future")
                    for link in slot["evidence"]:
                        evidence = resolve(link["reference"], value, loaded=True)
                        _require(evidence["evidenceState"] == "fresh" and evidence["completeness"] == "complete", "Stale/partial source cannot support boundary evidence")
                        observed = datetime.fromisoformat(evidence["observedAt"])
                        _require(observed <= at <= observed + timedelta(seconds=scenario["cp01Verifier"]["maxEvidenceAgeSeconds"]), "Boundary source is outside its freshness window")
                        if evidence["validUntil"] is not None:
                            _require(at < datetime.fromisoformat(evidence["validUntil"]), "Boundary source has expired")
                        if require_live:
                            _require(evidence["origin"] == "live-external" and evidence["eligibility"] == "eligible", "Fixture/local/replayed evidence cannot establish live NSP proof")
        elif kind == "drift-finding" and value["evaluation"] is not None:
            evaluation = resolve(value["evaluation"], value, loaded=True)
            _require(evaluation["promiseId"] == value["promiseId"], "Finding/evaluation promise mismatch")
            _require(value["baseline"] == evaluation["binding"] and value["runtimeSnapshot"] == evaluation["runtimeSnapshot"], "Finding source binding mismatch")
        elif kind == "human-attention-event":
            source = human_link(value["sourceEvent"], value)
            actor = source["actor"] if source["actor"]["kind"] == "human" else source.get("humanInitiator")
            _require(actor is not None and actor["actorId"] == value["actor"]["actorId"], "Human attention lacks human source attribution")
        elif kind in {"requirements", "architecture-proposal", "architecture-model", "architecture-decision-record", "approval", "review-gate-evaluation", "generation-contract"}:
            _validate_design(value, scenario, plain, human_link, current_bindings, as_of)
        for item in _walk(value):
            if item.get("artifactType") in {"operations-risk", "intent-continuity-graph"}:
                _require(item["schemaVersion"] == VERSION and item["scenario"] == expected, "Embedded projection version/scenario mismatch")
                _require(item["stateChecksum"] == semantic_checksum(item), "Embedded projection checksum mismatch")
                for field in ("runId", "caseId", "scope", "scenario", "runMode", "purpose"):
                    _require(item[field] == value[field], f"Embedded projection {field} mismatch")
            if item.get("artifactType") == "intent-continuity-graph":
                _validate_graph(item, scenario, resolve)


def _validate_design(value, scenario, plain, human_link, current_bindings, as_of):
    from .design_integrity import _check_human_event, assert_current_approval_binding

    kind = value["artifactType"]
    roles = {
        "architecture-proposal": {"requirements": "D02"},
        "architecture-model": {"sourceProposal": "D04", "review": "D08", "decision": "D06"},
        "architecture-decision-record": {"architecture": "D05", "review": "D08", "requirements": "D02"},
        "approval": {"gateEvaluation": "D08"},
        "review-gate-evaluation": {"subject": value.get("subjectContractId"), "requirements": "D02"},
        "generation-contract": {"requirements": "D02", "architecture": "D05", "decision": "D06", "gateEvaluation": "D08", "approval": "D07"},
    }.get(kind, {})
    for field, contract in roles.items():
        if value[field] is not None:
            plain(value[field], contract, value)
            _require(value["derivedFrom"].get(field) == value[field]["checksum"], f"Design input checksum mismatch: {field}")
    if kind in {"architecture-proposal", "architecture-model"}:
        expected_ids = set(scenario["boundaryComponentIds"].values())
        options = value["options"]
        _require(len({item["optionId"] for item in options}) == len(options), "Duplicate option ID")
        catalog = {item["candidateId"]: item for item in scenario["candidates"]}
        _require({item["catalogFacts"]["candidateId"] for item in options} == set(catalog), "Incomplete V3 candidate facts")
        for option in options:
            _require(option["catalogFacts"] == catalog[option["catalogFacts"]["candidateId"]], "Option reinterprets V3 catalog facts")
            _require({item["componentId"] for item in option["components"]} == expected_ids, "Option omits NSP topology")
            expected_edges = {
                ("CMP-CLAIMS-NSP-ASSOCIATION", "CMP-CLAIMS-STORE", "associated-storage"),
                ("CMP-CLAIMS-NSP-ASSOCIATION", "CMP-CLAIMS-NSP-PROFILE", "associated-profile"),
                ("CMP-CLAIMS-NSP-PROFILE", "CMP-CLAIMS-NSP", "profile-of"),
            }
            _require({(item["fromComponentId"], item["toComponentId"], item["relation"]) for item in option["relationships"]} == expected_edges, "Option NSP relationship mismatch")
    if kind == "requirements" and value["rpoQuestion"]["confirmation"] is not None:
        confirmation = value["rpoQuestion"]["confirmation"]
        event = human_link(confirmation["attentionEvent"], value)
        _require(event["actor"] == confirmation["actor"] and event["decisionId"] == confirmation["decisionId"] and event["actionId"] == confirmation["actionId"], "RPO confirmation source mismatch")
        _require(event["questionId"] == value["rpoQuestion"]["questionId"] and event["attentionKind"] in {"answered", "confirmed"}, "RPO source is not an explicit answer")
        _require(datetime.fromisoformat(event["occurredAt"]) == datetime.fromisoformat(confirmation["confirmedAt"]), "RPO confirmation time mismatch")
    if kind == "architecture-decision-record" and value["decisionReceipt"] is not None:
        decision = value["decisionReceipt"]
        event = human_link(decision["attentionEvent"], value)
        _check_human_event(decision, event, decision["attentionEvent"], action_id=decision["actionId"], decision_id=decision["decisionId"], kinds={"confirmed"} if decision["outcome"] == "selected" else {"rejected"})
        _require(decision["boundChecksums"] == value["derivedFrom"], "Decision input checksum mismatch")
    if kind == "approval":
        plain(value["binding"]["subject"], value["binding"]["subjectContractId"], value)
        if value["attentionEvent"] is not None:
            event = human_link(value["attentionEvent"], value)
            if value["status"] in {"approved", "rejected"}:
                _check_human_event(value, event, value["attentionEvent"], action_id=value["binding"]["actionId"], decision_id=value["decisionId"], kinds={value["status"]})
    if kind == "generation-contract":
        _require(value["desiredStateChecksum"] == scenario["desiredStateChecksum"], "Generation desired profile mismatch")
        paths = [item["relativePath"].casefold() for item in value["outputs"]]
        _require(len(paths) == len(set(paths)), "Duplicate planned output")
        if value["status"] == "ready":
            decision = plain(value["decision"], "D06", value)
            _require(decision["decisionReceipt"] is not None and decision["decisionReceipt"]["selectedOptionId"] == value["selectedOptionId"], "Generation has no matching human decision")
            for field in ("architecture", "requirements", "promiseContract"):
                _require(value[field] == decision[field], "Generation/decision input mismatch")
            gate = plain(value["gateEvaluation"], "D08", value)
            _require(gate["gate"]["gateId"] == "generation-ready" and gate["gate"]["effectiveStatus"] in {"pass", "pass-with-warnings"}, "Generation references unacceptable checks")
            approval = plain(value["approval"], "D07", value)
            _require(current_bindings is not None and approval["artifactId"] in current_bindings and as_of is not None, "Explicit current V3 approval facts are required")
            _require(approval["binding"]["subjectContractId"] == "D06" and approval["binding"]["subject"] == value["decision"], "Generation approval is for a different subject")
            event = human_link(approval["attentionEvent"], approval) if approval["attentionEvent"] else {}
            assert_current_approval_binding(approval, current_bindings[approval["artifactId"]], as_of, attention_event=event, schema_version=VERSION)
    if kind == "review-gate-evaluation":
        subject = plain(value["subject"], value["subjectContractId"], value)
        options = {item["optionId"] for item in subject.get("options", [])}
        for assessment in value["review"]["optionAssessments"]:
            _require(assessment["optionId"] in options, "Assessment refers to a different option")
            if assessment["eligibility"] == "eligible":
                _require(not any(item["mandatory"] and item["status"] != "pass" for item in assessment["ruleResults"]), "Eligibility contradicts reported mandatory checks")


def _validate_graph(graph, scenario, resolve):
    nodes = {node["nodeId"]: node for node in graph["nodes"]}
    edges = {edge["edgeId"]: edge for edge in graph["edges"]}
    _require(len(nodes) == len(graph["nodes"]) and len(edges) == len(graph["edges"]), "Duplicate graph identity")
    entities = {scenario["intentId"]: "intent", **{p["promiseId"]: "promise" for p in scenario["promises"]},
                **{cid: "component" for cid in scenario["boundaryComponentIds"].values()}}
    pairs = {(scenario["intentId"], p["promiseId"], "defines") for p in scenario["promises"]}
    pairs |= {(p["promiseId"], cid, "implemented-by") for p in scenario["promises"] for cid in p["componentIds"]}
    artifact_types = {"D03": "promise", "D05": "component", "D13": "baseline", "D14": "baseline", "D15": "runtime-snapshot", "D16": "finding", "D17": "evaluation", "E01": "evidence"}
    for node in nodes.values():
        source = node["source"]
        if source["kind"] == "scenario":
            _require(source["scenario"] == scenario_identity(scenario) and entities.get(source["entityId"]) == node["nodeType"], "Graph scenario node mismatch")
        elif source["kind"] == "artifact":
            resolve(source["reference"], graph, loaded=True)
            _require(artifact_types.get(source["reference"]["contractId"]) == node["nodeType"], "Graph artifact node type mismatch")
        elif source["kind"] == "nsp-observation":
            snapshot = resolve(source["snapshot"], graph, loaded=True)
            slot = snapshot["observation"][source["member"]]
            _require(node["nodeType"] == source["member"] and slot["value"] is not None, "Graph fabricates a missing NSP member")
            _require(source["observationState"] == slot["observationState"], "Graph observation state mismatch")
        else:
            _require(node["nodeType"] == source["expectedMember"], "Graph gap member mismatch")
    for edge in edges.values():
        _require(edge["fromNodeId"] in nodes and edge["toNodeId"] in nodes, "Graph edge has unknown endpoint")
        left = nodes[edge["fromNodeId"]]["source"]
        right = nodes[edge["toNodeId"]]["source"]
        support = edge["support"]
        if support["kind"] == "scenario-link":
            _require(support["scenario"] == scenario_identity(scenario), "Graph edge scenario mismatch")
            _require(left["kind"] == right["kind"] == "scenario", "Scenario edge endpoint type mismatch")
            _require(left["entityId"] == support["fromEntityId"] and right["entityId"] == support["toEntityId"], "Scenario edge endpoint mismatch")
            _require((left["entityId"], right["entityId"], edge["relation"]) in pairs and edge["status"] == "supported", "Unsupported scenario edge")
        elif support["kind"] == "artifact-link":
            _require(left["kind"] == right["kind"] == "artifact" and left["reference"] == support["source"] and right["reference"] == support["target"], "Artifact edge endpoint mismatch")
            source = resolve(support["source"], graph, loaded=True)
            _require(any(item == support["target"] for item in _walk(source) if _is_link(item)), "Graph source does not reference target")
            _require(edge["relation"] == "references" and edge["status"] == "supported", "Artifact edge cannot invent status")
        elif support["kind"] == "evaluation":
            evaluation = resolve(support["reference"], graph, loaded=True)
            _require(left["kind"] == "artifact" and left["reference"] == support["reference"] and right["kind"] == "scenario" and right["entityId"] == evaluation["promiseId"] == support["promiseId"], "Graph evaluation linkage mismatch")
            expected = {"verified": "supported", "breached": "broken", "unknown": "gap", "stale": "gap", "not-applicable": "gap"}
            _require(edge["relation"] == "evaluates" and edge["status"] == expected[evaluation["status"]], "Graph contradicts its evaluation source")
        elif support["kind"] == "nsp-relationship":
            _require(left["kind"] == right["kind"] == "nsp-observation", "NSP edge needs observed endpoints")
            _require(left["snapshot"] == right["snapshot"] == support["snapshot"] and left["member"] == support["fromMember"] and right["member"] == support["toMember"], "NSP graph endpoint mismatch")
            snapshot = resolve(support["snapshot"], graph, loaded=True)
            observation = snapshot["observation"]
            a, b = support["fromMember"], support["toMember"]
            _require(observation[a]["observationState"] == observation[b]["observationState"] == "complete", "Partial/stale NSP graph relationship")
            av, bv = observation[a]["value"], observation[b]["value"]
            perimeter = observation["perimeter"]["value"]
            def effective_perimeter_matches():
                return (
                    observation["perimeter"]["observationState"] == "complete" and perimeter is not None
                    and _arm_equal(av["perimeterId"], perimeter["id"])
                    and av["perimeterGuid"] is not None and perimeter["perimeterGuid"] is not None
                    and av["perimeterGuid"].casefold() == perimeter["perimeterGuid"].casefold()
                )
            relations = {
                ("association", "storage", "associated-storage"): lambda: _arm_equal(av["privateLinkResourceId"], bv["id"]),
                ("association", "profile", "associated-profile"): lambda: _arm_equal(av["profileId"], bv["id"]),
                ("profile", "perimeter", "profile-of"): lambda: _child_of(av["id"], bv["id"], "profiles"),
                ("configuration", "storage", "configuration-for"): lambda: _child_of(av["id"], bv["id"], "networkSecurityPerimeterConfigurations"),
                ("configuration", "association", "effective-association"): lambda: effective_perimeter_matches() and _child_of(bv["id"], av["perimeterId"], "resourceAssociations") and av["associationName"] == bv["name"] and av["accessMode"] == bv["accessMode"],
                ("configuration", "profile", "effective-profile"): lambda: effective_perimeter_matches() and _child_of(bv["id"], av["perimeterId"], "profiles") and av["profileName"] == bv["name"] and av["accessRulesVersion"] == bv["accessRulesVersion"],
            }
            relation = a, b, edge["relation"]
            _require(relation in relations and relations[relation]() and edge["status"] == "supported", "Unsupported NSP graph relationship")
        else:
            _require(left["kind"] == "gap" or right["kind"] == "gap", "Gap edge needs a missing member")
            _require(edge["status"] in {"gap", "pending"}, "Gap edge cannot imply proof")
    listed = {row["nodeId"]: row for row in graph["listEntries"]}
    _require(len(listed) == len(graph["listEntries"]) and set(listed) == set(nodes), "Graph/list node mismatch")
    for node_id, row in listed.items():
        incident = {edge["edgeId"] for edge in edges.values() if node_id in {edge["fromNodeId"], edge["toNodeId"]}}
        _require(set(row["relatedEdgeIds"]) == incident, "Graph/list edge mismatch")
