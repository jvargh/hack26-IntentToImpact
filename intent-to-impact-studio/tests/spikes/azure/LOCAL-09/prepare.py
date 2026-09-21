"""Compile and read-only preflight LOCAL-09. There is no deployment operation."""

import argparse
import fnmatch
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import urllib.parse

from evidence import (
    ACCOUNT, DECISION, GROUP, LOCATION, OWNED, PLANNED_IDS, ROOT, SOURCE, SUB, SUB_ID,
    TENANT, ReadOnlyRun, load, now, require, sha, write_json,
)
from guards import (
    ASSOCIATION_TYPE, NSP_TYPE, PROFILE_TYPE, RESOURCE_TYPES, STORAGE_PROPERTIES, STORAGE_TYPE,
    absence_guard, decision_guard, plan_guard, preview_guard, template_guard,
)


def condition_known(condition, resource_type, storage=STORAGE_PROPERTIES):
    condition = {key.lower(): value for key, value in condition.items()}
    for group in ["allof", "anyof"]:
        if group in condition:
            values = [condition_known(child, resource_type, storage) for child in condition[group]]
            if group == "allof":
                return False if False in values else True if all(v is True for v in values) else None
            return True if True in values else False if all(v is False for v in values) else None
    if "not" in condition:
        value = condition_known(condition["not"], resource_type, storage)
        return None if value is None else not value
    field = condition.get("field", "").lower()
    actual = resource_type if field == "type" else None
    if resource_type == STORAGE_TYPE and field.startswith(STORAGE_TYPE.lower() + "/"):
        actual = {k.lower(): v for k, v in storage.items()}.get(field[len(STORAGE_TYPE) + 1:])
    if type(actual) not in [str, bool]:
        return None
    if "exists" in condition:
        return str(condition["exists"]).lower() == "true"
    for operator in ["equals", "notequals"]:
        value = condition.get(operator)
        if type(value) in [str, bool] and not str(value).startswith("["):
            equal = str(actual).lower() == str(value).lower()
            return equal if operator == "equals" else not equal
    for operator in ["in", "notin"]:
        values = condition.get(operator)
        if isinstance(values, list) and all(isinstance(v, str) and not v.startswith("[") for v in values):
            found = str(actual).lower() in [v.lower() for v in values]
            return found if operator == "in" else not found
    return None


def effect_override_value(overrides):
    require(len(overrides) == 1 and set(overrides[0]) == {"kind", "value"}
            and overrides[0]["kind"] == "policyEffect"
            and str(overrides[0]["value"]).lower() in {"audit", "auditifnotexists", "deny", "denyaction", "disabled", "manual"},
            "Policy override requires explicit review")
    return overrides[0]["value"]


def policy_review(run, assignments):
    cache, reviewed, excluded, blockers, future_drift, overrides_reviewed = {}, [], [], [], [], []

    def definition(identifier, supplied, depth=0, effect_override=None):
        require(depth < 4, "Unexpected policy nesting")
        if identifier not in cache:
            cache[identifier] = run.rest(f"policy-definition-{len(cache)}", identifier, "2023-04-01")
        props = cache[identifier]["properties"]
        values = {k: v.get("defaultValue") for k, v in (props.get("parameters") or {}).items()}
        values.update({k: v["value"] for k, v in supplied.items()})

        def resolve(value):
            if isinstance(value, str) and value.startswith("[parameters('") and value.endswith("')]"):
                return values.get(value[13:-3])
            return value

        if "policyDefinitions" in props:
            for member in props["policyDefinitions"]:
                params = {k: {"value": resolve(v["value"])} for k, v in (member.get("parameters") or {}).items()}
                definition(member["policyDefinitionId"], params, depth + 1, effect_override)
            return
        rule = props["policyRule"]
        effect = effect_override if effect_override is not None else resolve(rule["then"]["effect"])
        reviewed.append({"id": identifier, "effect": effect})
        present = condition_known(rule["if"], STORAGE_TYPE)
        hypothetical = condition_known(rule["if"], STORAGE_TYPE, {**STORAGE_PROPERTIES, "supportsHttpsTrafficOnly": False})
        if present is False and hypothetical is not False and str(effect).lower() in {"modify", "append", "deny", "denyaction"}:
            future_drift.append({"definitionId": identifier, "effect": effect,
                                 "finding": "Hypothetical HTTPS=false may be denied or rewritten; no seed was performed."})
        if all(condition_known(rule["if"], kind) is False for kind in RESOURCE_TYPES):
            excluded.append(identifier)
        elif str(effect).lower() not in {"audit", "auditifnotexists", "deny", "denyaction", "disabled", "manual"}:
            blockers.append({"definitionId": identifier, "effect": effect,
                             "reason": "Potential unapproved modifying/deploying policy effect or unresolved expression"})

    for assignment in assignments:
        props = assignment.get("properties", assignment)
        if props.get("enforcementMode") == "DoNotEnforce":
            continue
        if props.get("notScopes") or props.get("resourceSelectors"):
            blockers.append({"assignmentId": assignment["id"], "reason": "Scope selectors/exclusions require review"})
        overrides = props.get("overrides") or []
        effect_override = None
        if overrides:
            try:
                effect_override = effect_override_value(overrides)
                overrides_reviewed.append({"assignmentId": assignment["id"], "effectiveEffect": effect_override,
                                           "reason": "Unconditional non-mutating effect override; original policy condition still evaluated"})
            except ValueError:
                blockers.append({"assignmentId": assignment["id"], "reason": "Policy override requires explicit review"})
        definition(props["policyDefinitionId"], props.get("parameters") or {}, effect_override=effect_override)
    result = {"assignmentsCount": len(assignments), "uniqueDefinitionsRead": len(cache),
              "reviewedEffects": reviewed, "excludedByTypeOrDeclaredValue": excluded,
              "blockers": blockers, "hypotheticalHttpsDriftPolicies": future_drift,
              "reviewedEffectOverrides": overrides_reviewed,
              "methodLimit": "Only type and explicitly declared values prove non-applicability; unresolved write effects block."}
    write_json(run.root / "policy-review.json", result)
    run.receipt["policyReview"] = {"file": "policy-review.json", "sha256": sha(run.root / "policy-review.json")}
    return result


def permitted(permission, action):
    return any(any(fnmatch.fnmatchcase(action.lower(), pattern.lower()) for pattern in entry["actions"])
               and not any(fnmatch.fnmatchcase(action.lower(), pattern.lower()) for pattern in entry.get("notActions", []))
               for entry in permission["value"])


def preflight(run, artifacts):
    for key, suffix in [
        ("profile-read-schema", "network-security-perimeter-profiles"),
        ("association-read-schema", "network-security-perimeter-associations"),
        ("nsp-read-schema", "network-security-perimeters"),
    ]:
        run.public_get(key, f"https://learn.microsoft.com/en-us/rest/api/network-security-perimeter/{suffix}/get?view=rest-network-security-perimeter-2025-01-01")
    context = run.data("context", ["account", "show", "--query", "{id:id,tenantId:tenantId,state:state}"])
    require(context["id"] == SUB and context["tenantId"] == TENANT and context["state"] == "Enabled", "Wrong CLI scope/tenant")
    live = run.rest("live-subscription", SUB_ID, "2022-12-01")
    require(live["subscriptionId"] == SUB and live["state"] == "Enabled", "Authentication/live scope read failed")
    for namespace, kind, version in [("Microsoft.Network", "networkSecurityPerimeters", "2025-01-01"),
                                     ("Microsoft.Storage", "storageAccounts", "2025-06-01")]:
        provider = run.data(namespace + "-provider", ["provider", "show", "--namespace", namespace])
        require(provider["registrationState"] == "Registered", f"{namespace} not registered; do not register")
        definitions = [entry for entry in provider["resourceTypes"] if entry["resourceType"].lower() == kind.lower()]
        require(len(definitions) == 1 and version in definitions[0]["apiVersions"], "Pinned API unavailable")
        require(any(region.lower().replace(" ", "") == LOCATION for region in definitions[0]["locations"]), "Region unavailable")
    run.receipt["childApiSupportBasis"] = "Published 2025-01-01 child schemas plus Provider validation; provider metadata lists parent NSP, not separate child types."
    permissions = run.rest("action-permissions", SUB_ID + "/providers/Microsoft.Authorization/permissions", "2022-04-01")
    required_actions = [
        "Microsoft.Resources/subscriptions/resourceGroups/write", "Microsoft.Resources/deployments/write",
        "Microsoft.Resources/deployments/validate/action", "Microsoft.Resources/deployments/whatIf/action",
        "Microsoft.Storage/storageAccounts/write", "Microsoft.Storage/storageAccounts/read",
        "Microsoft.Storage/storageAccounts/joinPerimeter/action",
        "Microsoft.Network/networkSecurityPerimeters/write", "Microsoft.Network/networkSecurityPerimeters/profiles/write",
        "Microsoft.Network/networkSecurityPerimeters/resourceAssociations/write",
        "Microsoft.Network/locations/networkSecurityPerimeterOperationStatuses/read",
    ]
    run.receipt["actionPermissions"] = {action: permitted(permissions, action) for action in required_actions}
    require(all(run.receipt["actionPermissions"].values()), "Required action permissions not established")
    exists = run.data("target-rg-exists", ["group", "exists", "--name", GROUP])
    name = run.data("target-name", ["storage", "account", "check-name", "--name", ACCOUNT])
    absence_guard(exists, name)
    run.receipt["targetPresence"] = {"resourceGroupExists": exists, "nameAvailable": name["nameAvailable"],
                                    "children": "No RG: proposed NSP/profile/association cannot already exist at this scope."}
    sku = run.rest("storage-sku", SUB_ID + "/providers/Microsoft.Storage/skus", "2025-06-01")
    require(not sku.get("nextLink") and any(s["name"] == "Standard_LRS" and s["kind"] == "StorageV2" and
            LOCATION in s["locations"] and not s.get("restrictions") for s in sku["value"]), "Storage SKU restriction/unknown")
    assignments = run.data("policy-assignments", ["policy", "assignment", "list", "--scope", SUB_ID, "--filter", "atScope()"])
    exemptions = run.data("policy-exemptions", ["policy", "exemption", "list", "--scope", SUB_ID, "--filter", "atScope()"])
    review = policy_review(run, assignments)
    if exemptions:
        review["blockers"].append({"reason": "Existing policy exemptions need explicit scope review; none changed"})
    common = ["--location", LOCATION, "--name", "local09-readonly-preflight",
              "--template-file", artifacts / "main.arm.json",
              "--parameters", "@" + str(artifacts / "infra" / "main.parameters.json"),
              "--validation-level", "Provider"]
    validation = run.data("provider-validation", ["deployment", "sub", "validate", *common], timeout=300, required=False)
    preview = run.data("full-what-if", ["deployment", "sub", "what-if", *common, "--no-pretty-print",
                                     "--result-format", "FullResourcePayloads"], timeout=300, required=False)
    require(validation is not None and not validation.get("error"), "Provider validation unavailable/failed")
    require(preview is not None, "What-if unavailable/failed")
    preview_guard(preview)
    run.receipt["targetValidation"] = "passed"
    run.receipt["whatIf"] = "all-five-exact-resources-create-only"
    require(not review["blockers"], "Unresolved policy applicability or extra policy-created resources; see policy-review.json")
    run.receipt["policyApplicability"] = "reviewed-no-unresolved-modifying-effects"


def pricing_retry(run):
    filters = {
        "storage": "serviceName eq 'Storage' and armRegionName eq 'eastus2' and skuName eq 'Hot LRS' and priceType eq 'Consumption'",
        "nsp": "serviceName eq 'Virtual Network' and contains(meterName, 'Perimeter') and priceType eq 'Consumption'",
    }
    prices = {"currency": "USD", "nspUnitPrice": None, "storageMeters": [],
              "nspStatus": "unavailable-not-zero", "totalCost": None,
              "limitation": "No NSP rate located is not free-service proof. Final cost acknowledgement needs current pricing confirmation."}
    for label, query in filters.items():
        url = "https://prices.azure.com/api/retail/prices?" + urllib.parse.urlencode({
            "api-version": "2023-01-01-preview", "$filter": query})
        entry = run.public_get("prices-" + label, url)
        if entry["status"] != "retrieved":
            continue
        response = load(run.root / entry["file"])
        require(not response.get("NextPageLink"), "Unreviewed price pagination")
        if label == "storage":
            prices["storageMeters"] = [{key: item[key] for key in [
                "meterId", "productName", "meterName", "retailPrice", "unitOfMeasure", "currencyCode", "effectiveStartDate"
            ]} for item in response["Items"] if item["isPrimaryMeterRegion"] and item["tierMinimumUnits"] == 0
               and item["productName"] == "Blob Storage" and item["meterName"] in [
                   "Hot LRS Data Stored", "Hot Read Operations", "LRS List and Create Container Operations"]]
        else:
            prices["nspCandidateMeterCount"] = len(response["Items"])
    write_json(run.root / "pricing-summary.json", prices)
    run.receipt["pricing"] = {"file": "pricing-summary.json", "sha256": sha(run.root / "pricing-summary.json"),
                              "status": "NSP-pricing-unconfirmed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-only", action="store_true")
    args = parser.parse_args()
    run = ReadOnlyRun("candidate")
    try:
        decision_guard(load(DECISION), load(ROOT / "infra" / "main.parameters.json"))
        plan_guard(load(ROOT / ".azure" / "infrastructure-plan.json"))
        artifacts = run.root / "artifacts"
        artifacts.mkdir()
        for path in (ROOT / "infra").rglob("*"):
            if path.is_file():
                target = artifacts / path.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        for name in ["insights.json", "infrastructure-plan.json"]:
            target = artifacts / ".azure" / name
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(ROOT / ".azure" / name, target)
        shutil.copyfile(DECISION, artifacts / "LOCAL-09.json")
        for path in SOURCE.iterdir():
            if path.is_file():
                target = artifacts / "guard-source" / path.name
                target.parent.mkdir(exist_ok=True)
                shutil.copyfile(path, target)
        run.command("cli-version", ["version", "--output", "json"])
        run.command("bicep-version", ["bicep", "version"])
        toolchain = load(SOURCE / "toolchain.json")
        require(toolchain["bicepVersion"].lstrip("v") in (run.root / "bicep-version.stdout.txt").read_text(encoding="utf-8"),
                "Compiler does not match the manifest; use scoped restore, never an unrecorded compiler fallback")
        run.receipt["compilerBinarySha256"] = sha(OWNED / toolchain["binaryRelativeToLocal09Evidence"])
        for number, output in enumerate(["main.arm.json", "main.repeat.arm.json"], 1):
            run.command(f"bicep-build-{number}", ["bicep", "build", "--file", artifacts / "infra" / "main.bicep",
                                               "--outfile", artifacts / output, "--no-restore"])
        require(sha(artifacts / "main.arm.json") == sha(artifacts / "main.repeat.arm.json"), "Nonrepeatable compile")
        template_guard(load(artifacts / "main.arm.json"))
        availability = run.command("checkov-availability", ["checkov", "--version"], azure=False, required=False)
        if availability["succeeded"]:
            run.command("checkov-scan", ["checkov", "--framework", "arm", "--file", artifacts / "main.arm.json",
                                        "--skip-download", "--output", "json"], azure=False, timeout=180)
        else:
            run.receipt["scannerException"] = {
                "status": "unavailable-not-passed",
                "selfReview": "Exact five-resource allowlist, immutable scope, HTTPS/TLS, no anonymous/shared key, SecuredByPerimeter, deny fallback, real Enforced association, zero rules; NSP replaces PE by explicit LOCAL-09. No IAM/secrets/data/log sinks.",
            }
        run.environment["SPK_LOCAL09_ARTIFACTS"] = str(artifacts)
        run.command("local-tests", [sys.executable, "-B", SOURCE / "test_local09.py"], azure=False, timeout=60)
        frozen = {str(path.relative_to(artifacts)): sha(path) for path in artifacts.rglob("*") if path.is_file()}
        for path in artifacts.rglob("*"):
            if path.is_file():
                path.chmod(stat.S_IREAD)
        manifest = {
            "schemaVersion": "1.0.0", "decisionId": "LOCAL-09", "decisionSha256": sha(DECISION),
            "compiledSha256": sha(artifacts / "main.arm.json"),
            "parametersSha256": sha(artifacts / "infra" / "main.parameters.json"),
            "files": frozen, "plannedResourceIds": PLANNED_IDS, "actualResourceIds": [],
            "canonicalScenarioId": None, "canonicalScenarioHash": None,
            "finalDeploymentConfirmation": "pending",
        }
        write_json(run.root / "candidate-manifest.json", manifest)
        run.receipt["candidateManifest"] = {"file": "candidate-manifest.json", "sha256": sha(run.root / "candidate-manifest.json")}
        if not args.local_only:
            pricing_retry(run)
            preflight(run, artifacts)
        require(sha(DECISION) == manifest["decisionSha256"] and
                all(sha(artifacts / path) == checksum for path, checksum in frozen.items()), "Candidate or decision changed")
        run.finish("local-only-prepared" if args.local_only else "technical-preflight-passed-pricing-and-final-confirmation-pending")
    except Exception as error:
        run.receipt["failure"] = run.redact(f"{type(error).__name__}: {error}")
        run.finish("blocked-no-deployment")
    print(json.dumps({"status": run.receipt["status"], "failure": run.receipt.get("failure"),
                      "receipt": str((run.root / "receipt.json").relative_to(ROOT))}, indent=2))
    return 1 if run.receipt["status"] == "blocked-no-deployment" else 0


if __name__ == "__main__":
    raise SystemExit(main())
