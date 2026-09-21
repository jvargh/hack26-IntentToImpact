"""One approval, one new RG/account. No update, seed, role or delete capability."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys


SOURCE = Path(__file__).resolve().parent
WORKSPACE = SOURCE.parents[3]
REPOSITORY_ROOT = WORKSPACE.parent if WORKSPACE.name == "intent-to-impact-studio" else WORKSPACE
OWNED = REPOSITORY_ROOT / ".intent-to-impact" / "spikes" / "SPK-03-01"
APPROVAL_ID = "APPROVAL-SANDBOX-CREATE-001"
APPROVAL_FILE = REPOSITORY_ROOT / ".intent-to-impact" / "execution" / "decisions" / f"{APPROVAL_ID}.json"
SCENARIO_FILE = WORKSPACE / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json"
SCENARIO_HASH = "sha256:a140b136272f077c82dcd1d38e8e2c13b0aa7aea192be2a80112ccc744213e9a"
SUBSCRIPTION = "463a82d4-1896-4332-aeeb-618ee5a5aa93"
TENANT = "5bb5fa45-2dcc-4310-bbc5-883021e9d84b"
GROUP = "rg-intent-to-impact-demo"
ACCOUNT = "iticlaimsv2a4f726"
LOCATION = "eastus2"
SUB_SCOPE = f"/subscriptions/{SUBSCRIPTION}"
GROUP_ID = f"{SUB_SCOPE}/resourceGroups/{GROUP}"
ACCOUNT_ID = f"{GROUP_ID}/providers/Microsoft.Storage/storageAccounts/{ACCOUNT}"
NESTED_DEPLOYMENT = "spk03-a001-storage"
PARAMETERS = {"location": LOCATION, "resourceGroupName": GROUP, "storageAccountName": ACCOUNT}
SETTINGS = {
    "kind": "StorageV2", "sku": "Standard_LRS", "accessTier": "Hot",
    "publicNetworkAccess": "Enabled", "supportsHttpsTrafficOnly": True,
    "allowBlobPublicAccess": False, "allowSharedKeyAccess": False,
    "minimumTlsVersion": "TLS1_2", "isHnsEnabled": False,
    "networkDefaultAction": "Allow", "networkBypass": "None",
}
PROPERTIES = {key: value for key, value in SETTINGS.items()
              if key not in {"kind", "sku", "networkDefaultAction", "networkBypass"}}
PROPERTIES["networkAcls"] = {"defaultAction": "Allow", "bypass": "None", "ipRules": [], "virtualNetworkRules": []}
FOUR = {key: SETTINGS[key] for key in ["publicNetworkAccess", "supportsHttpsTrafficOnly", "allowBlobPublicAccess", "minimumTlsVersion"]}


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def semantic_checksum(value):
    # Same serialization convention as tools/contracts/integrity.py; no product IDs are created.
    data = json.dumps({k: v for k, v in value.items() if k != "stateChecksum"},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n"
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def validate_inputs(approval, scenario, parameters):
    require(approval.get("approvalId") == APPROVAL_ID, "Missing/wrong approval ID")
    require(approval.get("status") == "approved-for-scoped-creation", "Creation not approved")
    require(approval.get("recordType") == "explicit-user-operator-consent" and
            approval.get("userResponse", "").lower() == "yes", "Explicit operator consent missing")
    require(approval.get("scope") == {"subscriptionId": SUBSCRIPTION, "resourceGroup": GROUP,
                                    "location": LOCATION, "storageAccountName": ACCOUNT}, "Approval scope mismatch")
    require(approval.get("storageSettings") == SETTINGS, "Approved settings mismatch")
    require("Seed drift, reset or delete resources" in approval.get("prohibitedOperations", []), "Seed/delete prohibition missing")
    require(semantic_checksum(scenario) == SCENARIO_HASH == scenario.get("stateChecksum"), "Scenario checksum mismatch")
    require(scenario.get("scenarioId") == "DEMO-CASE-CLAIMS-V2", "Scenario V2 required")
    require(scenario.get("desiredStorageConfiguration") == FOUR, "Canonical desired properties mismatch")
    require(scenario["desiredStateChecksum"] == semantic_checksum(FOUR), "Desired-state hash mismatch")
    require(scenario["componentId"] == "CMP-CLAIMS-STORE", "Wrong component")
    require({p["property"]: p["expected"] for p in scenario["cp01Verifier"]["predicates"]} == FOUR, "Verifier predicate mismatch")
    require(parameters.get("parameters") == {k: {"value": v} for k, v in PARAMETERS.items()}, "Parameter scope mismatch")


def inspect_template(template):
    require("subscriptionDeploymentTemplate" in template.get("$schema", ""), "Subscription template required")
    require(set(template["parameters"]) == set(PARAMETERS), "Unexpected template parameters")
    for key, value in PARAMETERS.items():
        require(template["parameters"][key].get("allowedValues") == [value], f"Parameter not pinned: {key}")
    resources = template.get("resources", [])
    require(len(resources) == 2, "Only RG and local nested deployment are permitted")
    rg, module = resources
    require(rg["type"] == "Microsoft.Resources/resourceGroups" and
            rg["name"] == "[parameters('resourceGroupName')]" and
            rg["location"] == "[parameters('location')]", "Unexpected RG resource")
    require(module["type"] == "Microsoft.Resources/deployments" and module["name"] == NESTED_DEPLOYMENT,
            "Unexpected nested deployment")
    require(module.get("resourceGroup") == "[parameters('resourceGroupName')]", "Nested scope mismatch")
    props = module["properties"]
    require(props.get("mode") == "Incremental" and "templateLink" not in props, "Remote/destructive deployment forbidden")
    require(props["parameters"] == {"location": {"value": "[parameters('location')]"},
                                  "storageAccountName": {"value": "[parameters('storageAccountName')]"}},
            "Nested parameter binding mismatch")
    children = props["template"].get("resources", [])
    require(len(children) == 1, "Only one storage resource is permitted")
    account = children[0]
    require(account["type"] == "Microsoft.Storage/storageAccounts" and account["apiVersion"] == "2023-05-01",
            "Unauthorized resource/API")
    require(account["name"] == "[parameters('storageAccountName')]" and
            account["location"] == "[parameters('location')]", "Storage scope mismatch")
    require(account["kind"] == "StorageV2" and account["sku"] == {"name": "Standard_LRS"}, "Storage SKU mismatch")
    require(account["properties"] == PROPERTIES, "Unauthorized storage property or seed")
    require(account["tags"] == {"architecture-component-id": "CMP-CLAIMS-STORE",
                                "operator-approval-id": APPROVAL_ID, "scenario-id": "DEMO-CASE-CLAIMS-V2"},
            "Storage mapping/ownership tag mismatch")
    require(set(account) == {"type", "apiVersion", "name", "location", "kind", "sku", "tags", "properties"},
            "Unexpected resource field/identity/child resources")
    text = json.dumps(template).lower()
    for forbidden in ["listkeys(", "deploymentScripts".lower(), "roleassignments", "reference(subscription("]:
        require(forbidden not in text, f"Forbidden template operation: {forbidden}")
    return {"resourceGroupId": GROUP_ID, "storageAccountId": ACCOUNT_ID,
            "infrastructureResourceTypes": ["Microsoft.Resources/resourceGroups", "Microsoft.Storage/storageAccounts"],
            "nestedDeploymentMetadata": NESTED_DEPLOYMENT}


def normalize(raw):
    properties = raw.get("properties", raw)
    observed, mapping = {}, {}
    for key, expected in FOUR.items():
        aliases = ["supportsHttpsTrafficOnly", "enableHttpsTrafficOnly"] if key == "supportsHttpsTrafficOnly" else [key]
        present = [name for name in aliases if name in properties]
        require(bool(present), f"Missing actual property: {key}")
        values = [properties[name] for name in present]
        require(all(type(value) is type(expected) for value in values), f"Null/wrong-type property: {key}")
        require(all(value == values[0] for value in values), f"Conflicting HTTPS aliases: {present}")
        observed[key], mapping[key] = values[0], present
    return {"properties": observed, "sourcePropertyNames": mapping,
            "matchesDesired": observed == FOUR}


def require_absent(group_exists, name_result):
    require(group_exists is False, "Target RG already exists unexpectedly; no adoption or update")
    require(name_result.get("nameAvailable") is True, "Storage name unavailable/unknown; no alternate name allowed")


def inspect_what_if(result):
    require(not result.get("error"), "What-if reported an error")
    expected = {GROUP_ID.lower(), ACCOUNT_ID.lower()}
    permitted = expected | {f"{GROUP_ID}/providers/Microsoft.Resources/deployments/{NESTED_DEPLOYMENT}".lower()}
    seen = set()
    for change in result.get("changes", []):
        identifier = change["resourceId"].lower()
        require(identifier in permitted, f"What-if contains unauthorized resource: {identifier}")
        require(change["changeType"] == "Create", f"What-if not create-only: {change['changeType']}")
        seen.add(identifier)
    require(expected <= seen, "What-if did not conclusively preview both approved creates")


def policy_type_condition(condition, resource_type):
    """Prove non-applicability only from type or an explicitly declared storage property."""
    normalized = {key.lower(): value for key, value in condition.items()}
    if len(normalized) != len(condition):
        return None
    condition = normalized
    if "allof" in condition:
        values = [policy_type_condition(c, resource_type) for c in condition["allof"]]
        return False if False in values else True if all(v is True for v in values) else None
    if "anyof" in condition:
        values = [policy_type_condition(c, resource_type) for c in condition["anyof"]]
        return True if True in values else False if all(v is False for v in values) else None
    if "not" in condition:
        value = policy_type_condition(condition["not"], resource_type)
        return None if value is None else not value
    field = condition.get("field", "")
    declared = None
    if field.lower() == "type":
        declared = resource_type
    elif resource_type.lower() == "microsoft.storage/storageaccounts":
        prefix = "microsoft.storage/storageaccounts/"
        known = {key.lower(): value for key, value in PROPERTIES.items()}
        if field.lower().startswith(prefix) and field[len(prefix):].lower() in known:
            declared = known[field[len(prefix):].lower()]
    if isinstance(declared, (str, bool)):
        if condition.get("exists") in ["true", True]:
            return True
        if condition.get("exists") in ["false", False]:
            return False
        for operator in ["equals", "notequals"]:
            value = condition.get(operator)
            if isinstance(value, (str, bool)) and not str(value).startswith("["):
                equal = str(value).lower() == str(declared).lower()
                return equal if operator == "equals" else not equal
        for operator in ["in", "notin"]:
            values = condition.get(operator)
            if isinstance(values, list) and all(isinstance(v, str) and not v.startswith("[") for v in values):
                found = str(declared).lower() in [v.lower() for v in values]
                return found if operator == "in" else not found
    return None


class Run:
    def __init__(self, execute):
        for path in [REPOSITORY_ROOT / ".intent-to-impact", OWNED.parent, OWNED]:
            require(not path.is_symlink() and not getattr(path, "is_junction", lambda: False)(), "Reparse output path")
        self.root = OWNED / ("create-a001-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        self.root.mkdir(parents=True, exist_ok=False)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.auth = self.root / "session-auth"
        self.auth.mkdir()
        (self.root / "tmp").mkdir()
        self.environment = os.environ.copy()
        self.environment.update({
            "AZURE_CONFIG_DIR": str(self.auth), "AZURE_EXTENSION_DIR": str(self.root / "extensions"),
            "AZURE_CORE_COLLECT_TELEMETRY": "false", "AZURE_CORE_CHECK_VERSION": "false",
            "AZURE_BICEP_CHECK_VERSION": "false", "AZURE_BICEP_USE_BINARY_FROM_PATH": "false",
            "BICEP_CACHE_ROOT_DIRECTORY": str(self.root / "bicep-cache"),
            "DOTNET_CLI_HOME": str(self.root / "dotnet"), "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1", "TEMP": str(self.root / "tmp"), "TMP": str(self.root / "tmp"),
            "SPK_BOOTSTRAP_ARTIFACTS": str(self.artifacts),
        })
        self.az = shutil.which("az") or "az"
        azure_python = Path(self.az).parent.parent / "python.exe"
        if Path(self.az).suffix.lower() == ".cmd" and azure_python.is_file():
            # Same entrypoint as Microsoft's az.cmd, without CMD interpreting () or & in arguments.
            self.az_prefix = [str(azure_python), "-IBm", "azure.cli"]
            self.environment["AZ_INSTALLER"] = "MSI"
        else:
            self.az_prefix = [self.az]
        self.execute = execute
        self.frozen = {}
        self.mutation_started = False
        self.deployment_name = "spk03-a001-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        self.receipt = {
            "schemaVersion": "1.0.0", "purpose": "approval-specific-sandbox-bootstrap",
            "approvalId": APPROVAL_ID, "status": "running", "startedAt": now(),
            "canonicalProductState": False, "commands": [], "azureMutationAttempted": False,
            "approvalReference": str(APPROVAL_FILE.relative_to(REPOSITORY_ROOT)),
            "scenario": {}, "artifactHashes": {}, "baselineStatus": "not-observed",
            "deploymentName": self.deployment_name, "partialResources": [],
            "driftApproved": False, "cleanupApproved": False,
            "limitations": [
                "Bootstrap and V2 configuration baseline only; no product D10/D12 materialization IDs, architecture/UI approval, M0.5 or full hero completion.",
                "No seed, restoration, data-plane request, key read, container, role, identity or deletion capability.",
                "Public networking and LRS are explicitly approved exceptions to generic private/HA recommendations.",
                "USD 1 monitoring threshold is not an enforced spending cap; no paid monitoring resource is created.",
            ],
        }

    def save(self):
        write_json(self.root / "receipt.json", self.receipt)

    def redact(self, text):
        for value, label in [
            (str(REPOSITORY_ROOT), "[repository]"),
            (str(WORKSPACE), "[workspace]"),
            (str(Path.home()), "[user-home]"),
        ]:
            text = re.sub(re.escape(value), lambda _: label, text, flags=re.IGNORECASE)
        text = re.sub(r"(?i)(Bearer\s+)\S+", r"\1[redacted]", text)
        return re.sub(r'(?i)("?(?:access_token|refresh_token|client_secret|AccountKey)"?\s*[:=]\s*"?)[^"\s,;]+',
                      r"\1[redacted]", text)

    def command(self, key, arguments, *, azure=True, timeout=120, required=True):
        argv = [*self.az_prefix, *arguments] if azure else arguments
        logical = [self.az, *arguments] if azure else arguments
        item = {"id": key, "argv": [self.redact(str(a)) for a in logical],
                "executionArgv": [self.redact(str(a)) for a in argv], "cwd": "[workspace]",
                "startedAt": now(), "timeoutSeconds": timeout, "exitCode": None,
                "timedOut": False, "captureError": None}
        raw = [self.root / f".{key}.{stream}.capture" for stream in ["stdout", "stderr"]]
        try:
            with raw[0].open("wb") as out, raw[1].open("wb") as err:
                process = subprocess.Popen([str(a) for a in argv], cwd=WORKSPACE, env=self.environment,
                                           stdout=out, stderr=err)
                try:
                    item["exitCode"] = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    item["timedOut"] = True
                    # Terminate only this invocation's process tree; never kill by name.
                    stop = (
                        "function Stop-OwnedTree([int]$rootId) { "
                        "Get-CimInstance Win32_Process -Filter \"ParentProcessId=$rootId\" | "
                        "ForEach-Object { Stop-OwnedTree $_.ProcessId }; "
                        "Stop-Process -Id $rootId -Force -ErrorAction SilentlyContinue }; "
                        f"Stop-OwnedTree {process.pid}"
                    )
                    try:
                        subprocess.run(["pwsh", "-NoProfile", "-Command", stop], env=self.environment,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, check=False)
                        process.wait(timeout=5)
                    except (OSError, subprocess.TimeoutExpired):
                        item["captureError"] = "Owned process termination uncertain; do not retry mutation"
        except OSError as error:
            item["captureError"] = self.redact(str(error))
        item["finishedAt"] = now()
        item["succeeded"] = item["exitCode"] == 0 and not item["timedOut"] and not item["captureError"]
        for path, stream in zip(raw, ["stdout", "stderr"]):
            text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
            target = self.root / f"{key}.{stream}.txt"
            target.write_text(self.redact(text), encoding="utf-8")
            item[stream] = {"file": target.name, "sha256": sha(target), "redacted": True}
            if path.exists():
                path.unlink()
        self.receipt["commands"].append(item)
        self.save()
        if required:
            require(item["succeeded"], f"{key} failed/uncertain; exit={item['exitCode']}; inspect captured streams")
        return item

    def data(self, key, arguments, **kwargs):
        item = self.command(key, [*arguments, "--subscription", SUBSCRIPTION, "--output", "json"], **kwargs)
        return load(self.root / item["stdout"]["file"]) if item["succeeded"] else None

    def rest(self, key, resource_id, api="2023-05-01", **kwargs):
        return self.data(key, ["rest", "--method", "get", "--url",
                              f"https://management.azure.com{resource_id}?api-version={api}"], **kwargs)

    def freeze(self):
        self.frozen = {path: sha(path) for path in self.artifacts.iterdir() if path.is_file()}
        self.receipt["artifactHashes"] = {path.name: checksum for path, checksum in self.frozen.items()}
        for path in self.frozen:
            path.chmod(stat.S_IREAD)
        self.save()

    def recheck(self):
        require(all(path.exists() and sha(path) == checksum for path, checksum in self.frozen.items()), "Frozen artifact changed")
        require(sha(APPROVAL_FILE) == self.receipt["approvalFileSha256"], "Approval changed")
        require(sha(SCENARIO_FILE) == self.receipt["scenario"]["fileSha256"], "Scenario changed")
        validate_inputs(load(APPROVAL_FILE), load(SCENARIO_FILE), load(self.artifacts / "main.parameters.json"))
        inspect_template(load(self.artifacts / "main.arm.json"))

    def prepare(self):
        approval, scenario = load(APPROVAL_FILE), load(SCENARIO_FILE)
        validate_inputs(approval, scenario, load(SOURCE / "main.parameters.json"))
        self.receipt["approvalFileSha256"] = sha(APPROVAL_FILE)
        self.receipt["scenario"] = {
            "scenarioId": scenario["scenarioId"], "scenarioVersion": scenario["scenarioVersion"],
            "stateChecksum": scenario["stateChecksum"], "fileSha256": sha(SCENARIO_FILE),
            "desiredStateChecksum": scenario["desiredStateChecksum"],
            "promiseId": next(p["promiseId"] for p in scenario["promises"] if p["verifierIds"] == [scenario["cp01Verifier"]["verifierId"]]),
            "verifierId": scenario["cp01Verifier"]["verifierId"],
            "componentId": scenario["componentId"],
        }
        for source in SOURCE.iterdir():
            if source.is_file():
                shutil.copyfile(source, self.artifacts / source.name)
        shutil.copyfile(APPROVAL_FILE, self.artifacts / "approval.json")
        shutil.copyfile(SCENARIO_FILE, self.artifacts / "scenario.json")
        prior = OWNED.parent / "SPK-04-01" / "20260912T2130019672999Z-805407cd"
        binary = prior / "azure-config" / "bin" / "bicep.exe"
        expected = next(item["sha256"] for item in load(prior / "receipt.json")["files"]
                        if item["role"] == "restored-compiler")
        require(binary.is_file() and sha(binary) == expected, "Accepted local Bicep compiler unavailable/changed")
        (self.auth / "bin").mkdir()
        shutil.copyfile(binary, self.auth / "bin" / "bicep.exe")
        self.receipt["compilerBinarySha256"] = expected
        self.receipt["toolRestore"] = "none; copied hash-verified accepted compiler into owned CLI cache"
        self.command("azure-cli-version", ["version", "--output", "json"])
        self.command("bicep-version", ["bicep", "version"])
        for output in ["main.arm.json", "main.repeat.arm.json"]:
            self.command("compile-" + output.split(".")[1], [
                "bicep", "build", "--file", self.artifacts / "main.bicep",
                "--outfile", self.artifacts / output, "--no-restore",
            ])
        require(sha(self.artifacts / "main.arm.json") == sha(self.artifacts / "main.repeat.arm.json"), "Compilation hashes differ")
        self.receipt["templateInspection"] = inspect_template(load(self.artifacts / "main.arm.json"))
        scan = self.command("checkov-availability", ["checkov", "--version"], azure=False, required=False)
        if scan["succeeded"]:
            self.command("checkov-scan", ["checkov", "--framework", "arm", "--file", self.artifacts / "main.arm.json",
                                         "--skip-download", "--output", "json"], azure=False, timeout=180)
        else:
            self.receipt["securityScanner"] = {
                "status": "unavailable-not-passed",
                "exception": "Generation guidance permits explicit unavailable-tool self-review. Exact allowlist/secure public settings are checked by local tests and target validation; no full Checkov claim.",
                "selfReview": ["TLS1_2", "HTTPS required", "anonymous false", "shared key false", "no secrets or extra resources",
                               "public endpoint and LRS explicitly approved; no identity/PE/monitoring resources authorized"],
            }
        self.command("local-tests", [sys.executable, "-B", str(SOURCE / "test_bootstrap.py")],
                     azure=False, timeout=60)
        self.freeze()

    def copy_auth(self):
        shared = Path.home() / ".azure"
        profile = load(shared / "azureProfile.json")
        selected = [entry for entry in profile.get("subscriptions", [])
                    if entry.get("id") == SUBSCRIPTION and entry.get("tenantId") == TENANT]
        require(len(selected) == 1, "No exact cached subscription/tenant context; do not login or switch")
        selected[0]["isDefault"] = True
        write_json(self.auth / "azureProfile.json", {"subscriptions": selected})
        copied = []
        for name in ["msal_token_cache.bin", "msal_token_cache.json", "msal_http_cache.bin"]:
            if (shared / name).is_file():
                shutil.copyfile(shared / name, self.auth / name)
                copied.append(name)
        require(bool(copied), "No cached authentication; no login authorized")
        self.receipt["authIsolation"] = {
            "directory": "session-auth", "selectedProfileOnly": True,
            "cachedCredentialFilesCopied": copied, "credentialContentsRecorded": False,
            "cleanup": "owned copies removed in finally; original auth/default context unchanged",
        }

    def check_policy_effects(self, assignments):
        """Reject potential auto-creation/mutation effects rather than bypassing policy."""
        self.receipt["policyAssignmentsCount"] = len(assignments)
        examined = []
        cached = {}
        excluded = []
        def definition(identifier, supplied, depth=0):
            require(depth < 4, "Unexpected policy nesting")
            if identifier not in cached:
                cached[identifier] = self.rest(f"policy-definition-{len(examined)}", identifier, "2023-04-01")
                examined.append(identifier)
            body = cached[identifier]
            props = body["properties"]
            values = {k: v.get("defaultValue") for k, v in props.get("parameters", {}).items()}
            values.update({k: v["value"] for k, v in supplied.items()})
            def resolved(value):
                if isinstance(value, str) and value.startswith("[parameters('") and value.endswith("')]"):
                    return values.get(value[13:-3])
                return value
            if "policyDefinitions" in props:
                for member in props["policyDefinitions"]:
                    child = {k: {"value": resolved(v["value"])} for k, v in member.get("parameters", {}).items()}
                    definition(member["policyDefinitionId"], child, depth + 1)
            else:
                effect = resolved(props["policyRule"]["then"]["effect"])
                possible_types = ["Microsoft.Resources/resourceGroups", "Microsoft.Resources/deployments",
                                  "Microsoft.Storage/storageAccounts"]
                if all(policy_type_condition(props["policyRule"]["if"], t) is False for t in possible_types):
                    excluded.append({"definitionId": identifier, "reason": "Type/explicit-approved-property conditions exclude every proposed resource"})
                    return
                require(isinstance(effect, str) and effect.lower() in {"audit", "auditifnotexists", "deny", "denyaction", "disabled", "manual"},
                        f"Potential unapproved Azure Policy side effect: {identifier}, effect={effect}")
        for assignment in assignments:
            props = assignment.get("properties", assignment)
            if props.get("enforcementMode") == "DoNotEnforce":
                continue
            require(not props.get("overrides"), "Policy overrides need explicit review")
            definition(props["policyDefinitionId"], props.get("parameters", {}))
        self.receipt["policyDefinitionsExamined"] = examined
        self.receipt["policiesExcludedByExactType"] = excluded

    def target_preflight(self):
        self.copy_auth()
        context = self.data("selected-context", ["account", "show", "--query",
                            "{id:id,tenantId:tenantId,state:state,environmentName:environmentName}"])
        require(context["id"] == SUBSCRIPTION and context["tenantId"] == TENANT and context["state"] == "Enabled",
                "Authenticated context scope mismatch")
        live = self.rest("authenticated-subscription-read", SUB_SCOPE, "2022-12-01")
        require(live["subscriptionId"] == SUBSCRIPTION and live["state"] == "Enabled", "Live subscription read mismatch")
        provider = self.data("storage-provider", ["provider", "show", "--namespace", "Microsoft.Storage",
            "--query", "{namespace:namespace,registrationState:registrationState,resourceTypes:resourceTypes[?resourceType=='storageAccounts']}"])
        require(provider["registrationState"] == "Registered", "Storage provider unregistered; registration not authorized")
        require(any("East US 2" in t["locations"] and "2023-05-01" in t["apiVersions"] for t in provider["resourceTypes"]),
                "Required storage region/API not supported")
        sku_response = self.rest("storage-sku", SUB_SCOPE + "/providers/Microsoft.Storage/skus")
        require(not sku_response.get("nextLink"), "Storage SKU metadata incomplete")
        skus = [s for s in sku_response["value"] if s.get("name") == "Standard_LRS" and s.get("kind") == "StorageV2"]
        require(any(LOCATION in s.get("locations", []) and not s.get("restrictions") for s in skus),
                "Standard_LRS StorageV2 location/SKU restricted or unknown")
        self.absence("preflight")
        policies = self.data("assigned-policy", ["policy", "assignment", "list", "--scope", SUB_SCOPE,
                                                "--filter", "atScope()"])
        self.check_policy_effects(policies)
        common = ["--location", LOCATION, "--name", self.deployment_name,
                  "--template-file", self.artifacts / "main.arm.json",
                  "--parameters", "@" + str(self.artifacts / "main.parameters.json"),
                  "--validation-level", "Provider"]
        validation = self.data("target-validation", ["deployment", "sub", "validate", *common], timeout=240)
        require(not validation.get("error"), "Provider validation error")
        preview = self.data("target-what-if", ["deployment", "sub", "what-if", *common,
                            "--no-pretty-print", "--result-format", "FullResourcePayloads"], timeout=300)
        inspect_what_if(preview)
        self.receipt["targetValidation"] = "passed"
        self.receipt["whatIf"] = "create-only-approved-resources"

    def absence(self, prefix):
        exists = self.data(prefix + "-rg-exists", ["group", "exists", "--name", GROUP])
        available = self.data(prefix + "-name-check", ["storage", "account", "check-name", "--name", ACCOUNT])
        require_absent(exists, available)

    def create(self):
        require(self.execute and self.receipt.get("targetValidation") == "passed" and
                self.receipt.get("whatIf") == "create-only-approved-resources", "Creation preflight/explicit execution gate missing")
        self.recheck()
        self.absence("immediate-pre-create")
        self.mutation_started = True
        self.receipt["azureMutationAttempted"] = True
        self.receipt["mutationStartedAt"] = now()
        self.save()
        created = self.data("create-approved-subdeployment", [
            "deployment", "sub", "create", "--location", LOCATION, "--name", self.deployment_name,
            "--template-file", self.artifacts / "main.arm.json",
            "--parameters", "@" + str(self.artifacts / "main.parameters.json"),
        ], timeout=600)
        require(created["properties"]["provisioningState"] == "Succeeded", "Deployment not Succeeded")
        self.receipt["actualDeploymentId"] = created["id"]
        self.receipt["deploymentSucceededAt"] = now()
        self.data("subscription-deployment-operations", ["deployment", "operation", "sub", "list", "--name", self.deployment_name])
        self.data("storage-deployment-operations", ["deployment", "operation", "group", "list",
                                                  "--resource-group", GROUP, "--name", NESTED_DEPLOYMENT])
        self.baseline()

    def baseline(self):
        group = self.data("created-resource-group", ["group", "show", "--name", GROUP])
        require(group["id"].lower() == GROUP_ID.lower() and group["location"] == LOCATION, "RG readback mismatch")
        inventory = self.data("created-resource-inventory", ["resource", "list", "--resource-group", GROUP])
        self.receipt["partialResources"] = [resource["id"] for resource in inventory]
        require(len(inventory) == 1 and inventory[0]["id"].lower() == ACCOUNT_ID.lower(), "Unexpected resource inventory")
        cli = self.data("account-cli-readback", ["storage", "account", "show", "--resource-group", GROUP, "--name", ACCOUNT])
        arm = self.rest("account-arm-readback", ACCOUNT_ID)
        require(arm["id"].lower() == ACCOUNT_ID.lower() and arm["location"] == LOCATION, "Account readback scope mismatch")
        require(arm["kind"] == "StorageV2" and arm["sku"]["name"] == "Standard_LRS", "Account kind/SKU mismatch")
        require(arm["properties"]["provisioningState"] == "Succeeded", "Account provisioning not complete")
        for key, value in PROPERTIES.items():
            actual = arm["properties"].get(key)
            if key == "networkAcls":
                require(all(actual.get(k) == v for k, v in value.items()), "Network ACL mismatch")
            else:
                require(type(actual) is type(value) and actual == value, f"Approved property mismatch: {key}")
        cli_normalized, arm_normalized = normalize(cli), normalize(arm)
        require(cli_normalized["properties"] == arm_normalized["properties"] == FOUR, "Actual CLI/ARM baseline mismatch")
        containers = self.rest("empty-container-inventory", ACCOUNT_ID + "/blobServices/default/containers")
        require(containers.get("value") == [] and not containers.get("nextLink"), "Account not conclusively empty")
        baseline = {
            "schemaVersion": "1.0.0", "purpose": "V2-scoped-configuration-baseline",
            "evidenceOrigin": "live-external", "observedAt": now(), "scenario": self.receipt["scenario"],
            "approvalReference": self.receipt["approvalReference"], "approvalId": APPROVAL_ID,
            "subscriptionId": SUBSCRIPTION, "tenantId": TENANT,
            "resourceGroupId": group["id"], "resourceId": arm["id"],
            "deploymentId": self.receipt["actualDeploymentId"],
            "compiledTemplateSha256": self.frozen[self.artifacts / "main.arm.json"],
            "parametersSha256": self.frozen[self.artifacts / "main.parameters.json"],
            "desiredProperties": FOUR, "armObservation": arm_normalized, "cliObservation": cli_normalized,
            "configurationBaseline": "matched", "emptyContainerInventory": True,
            "etag": arm.get("etag"), "rawReadbackFiles": ["account-arm-readback.stdout.txt", "account-cli-readback.stdout.txt"],
            "canonicalProductState": False, "productBindingStatus": "not-created-owner-adapter-must-bind-real-receipts",
            "privateConnectivityClaim": False, "fullAccessControlClaim": False,
            "seedPerformed": False, "cleanupPerformed": False,
            "freshnessLimitSeconds": load(SCENARIO_FILE)["cp01Verifier"]["maxEvidenceAgeSeconds"],
        }
        write_json(self.root / "baseline.json", baseline)
        self.receipt["baseline"] = {"file": "baseline.json", "sha256": sha(self.root / "baseline.json")}
        self.receipt["baselineStatus"] = "V2-four-properties-matched-empty-account"
        self.receipt["actualResourceGroupId"] = group["id"]
        self.receipt["actualStorageAccountId"] = arm["id"]
        self.recheck()

    def inspect_uncertain(self):
        self.receipt["uncertainOutcomeAction"] = "Read exact state only; no mutation retry or cleanup"
        for key, args in [
            ("failure-deployment-read", ["deployment", "sub", "show", "--name", self.deployment_name]),
            ("failure-rg-read", ["group", "show", "--name", GROUP]),
            ("failure-account-read", ["storage", "account", "show", "--resource-group", GROUP, "--name", ACCOUNT]),
            ("failure-resource-inventory", ["resource", "list", "--resource-group", GROUP]),
        ]:
            try:
                value = self.data(key, args, required=False, timeout=90)
                if key.endswith("inventory") and isinstance(value, list):
                    self.receipt["partialResources"] = [item["id"] for item in value]
            except Exception as error:
                self.receipt.setdefault("inspectionErrors", []).append(self.redact(str(error)))

    def cleanup_local_auth(self):
        # Only owned ephemeral credentials, never Azure resources or original user caches.
        for name in ["azureProfile.json", "msal_token_cache.bin", "msal_token_cache.json", "msal_http_cache.bin"]:
            path = self.auth / name
            if path.is_file():
                path.unlink()
        self.receipt["ownedCredentialCopiesRemoved"] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-approved", action="store_true", help="Allow this exact recorded creation after all checks")
    args = parser.parse_args()
    run = Run(args.execute_approved)
    try:
        run.prepare()
        if args.execute_approved:
            run.target_preflight()
            run.create()
            run.receipt["status"] = "created-baseline-recorded"
        else:
            run.receipt["status"] = "prepared-local-only"
    except Exception as error:
        run.receipt["status"] = "blocked" if not run.mutation_started else "creation-or-baseline-incomplete"
        run.receipt["failure"] = run.redact(f"{type(error).__name__}: {error}")
        if run.mutation_started:
            run.inspect_uncertain()
    finally:
        run.cleanup_local_auth()
        run.receipt["finishedAt"] = now()
        run.save()
    print(json.dumps({"status": run.receipt["status"], "baselineStatus": run.receipt["baselineStatus"],
                      "receipt": str((run.root / "receipt.json").relative_to(REPOSITORY_ROOT)),
                      "failure": run.receipt.get("failure")}, indent=2))
    return 0 if run.receipt["status"] in {"prepared-local-only", "created-baseline-recorded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
