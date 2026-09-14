"""Closed-catalog infrastructure generation. This module never deploys Azure resources."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import uuid
import zipfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TEMPLATES = HERE / "templates"
SCHEMA_PATH = HERE / "studio.schema.json"
CATALOG = json.loads((TEMPLATES / "catalog.json").read_text(encoding="utf-8"))
COMPILER_PATHS = (
    REPO / ".intent-to-impact" / "spikes" / "SPK-03-01" / "LOCAL-09"
    / "tools" / "bicep-v0.47.16" / "bin" / "bicep.exe",
    REPO / ".azure" / "bin" / "bicep.exe",
    Path.home() / ".azure" / "bin" / "bicep.exe",
)
BUILD_TIMEOUT = 180
APP_KINDS = {"appservice", "functions"}
ROLE_IDS = {
    "blob-contributor": "ba92f5b4-2d11-453d-a403-e96b0029c9fe",
    "blob-owner": "b7e6dc6d-f1e8-4753-8033-0f276bb0955b",
    "queue-contributor": "974c5e8b-45b9-4653-ba55-5f855dd0fb88",
    "bus-sender": "69a216fc-b8fb-44d8-bc22-1f3c2cd27a39",
    "bus-receiver": "4f6b9d9a-7a21-4624-b1d8-3b8feda0e354",
    "secrets-user": "4633458b-17de-408a-b874-0445c86b69e6",
}
LIMITATIONS = [
    "Compiled infrastructure only; deploymentStatus is not-deployed. No Azure mutation was performed.",
    "WARNING: Queue permissions follow direction, never labels: host -> Service Bus queue grants Data Sender; "
    "queue -> host grants Data Receiver. A host that both produces and consumes needs opposite directed edges. "
    "Review queue directions before deployment, even when a label says consume. Compilation does not verify "
    "queue handlers, retries or dead-letter behavior; implement and test them separately.",
    "Bicep compilation checks syntax/types/modules only. Target policy, quota, RBAC, region availability, "
    "resource-name availability, what-if and deployment validation were NOT run.",
    "Choose an approved target resource group and region matching business/data-residency requirements. "
    "Location defaults to resourceGroup().location, not a sandbox region. The model contract has no validated "
    "region field; no regional compliance is inferred or guaranteed.",
    "Public endpoints are Enabled with TLS/authentication restrictions. The user's known policy denying "
    "public network access may block deployment; this package does not claim private-network compliance.",
    "Supply an existing tenant Entra application client ID (bearer-token audience) and any external HTTPS "
    "API URLs as required parameters; no external application registrations or credentials are created.",
    "External callbacks require a supplied existing same-tenant Entra caller client ID and bearer-token "
    "authentication. Provider-native signed webhooks are not implemented; use an authenticated adapter "
    "if the provider cannot obtain an Entra token. Confirm this compatibility before deployment.",
    "No business application binaries, handlers, authentication clients or production tests are fabricated. "
    "Deploy application code separately and implement every endpoint/identity integration in manifest.json.",
    "Catalog supports Linux App Service Node 22, dedicated Linux Functions Python 3.12/v4, Blob Storage, "
    "Service Bus work queues and Key Vault. Other services, triggers, runtimes and private topologies are blocked.",
    "No live cost forecast or production-readiness claim. B1 plans and Standard services are billable if deployed.",
]


class Blocked(ValueError):
    """The stored proposal cannot safely be represented by the server catalog."""


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _hash(content: str | bytes) -> str:
    return hashlib.sha256(content.encode("utf-8") if isinstance(content, str) else content).hexdigest()


def _symbol(identifier: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", identifier):
        raise Blocked("Invalid component or option identifier.")
    # The terminal marker prevents a component "api-plan" colliding with api's plan.
    return "c_" + identifier.replace("-", "_") + "_node"


def _validate(result: dict, option_id: str) -> tuple[dict, dict]:
    try:
        from jsonschema import Draft7Validator
    except ImportError as exc:
        raise Blocked("Server prerequisite missing: install the control-plane jsonschema dependency.") from exc
    if not SCHEMA_PATH.is_file():
        raise Blocked("Shared studio.schema.json is missing; restore the server contract before building.")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft7Validator({"$ref": "#/definitions/StudioResult", **schema, "oneOf": [
        {"$ref": "#/definitions/StudioResult"}
    ]})
    errors = sorted(validator.iter_errors(result), key=lambda e: str(list(e.absolute_path)))
    if errors:
        error = errors[0]
        raise Blocked(f"Stored StudioResult fails shared schema at {list(error.absolute_path)} "
                      f"({error.validator}); re-analyze before building.")
    if not result["resultId"] or len(result["resultId"]) > 80:
        raise Blocked("Stored resultId is missing or exceeds the transport bound.")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", result["inputHash"]):
        raise Blocked("Stored inputHash must be a SHA-256 digest.")
    if {r["role"] for r in result["modelReceipts"]} != {"synthesis", "assurance"}:
        raise Blocked("Stored result needs distinct synthesis and assurance model receipts.")

    def unique(items: list[dict], label: str) -> set[str]:
        ids = [x["id"] for x in items]
        if len(ids) != len(set(ids)) or any(not i for i in ids):
            raise Blocked(f"Duplicate or empty {label} identifiers.")
        return set(ids)

    source_ids = unique(result["sources"], "source")
    analysis = result["analysis"]
    requirement_ids = unique(analysis["requirements"], "requirement")
    unique(analysis["questions"], "question")
    option_ids = unique(analysis["options"], "option")
    if option_id not in option_ids:
        raise Blocked("Selected option does not exist in the stored result.")
    if analysis["recommendedOptionId"] not in option_ids:
        raise Blocked("Recommended option is not a stored architecture option.")
    for requirement in analysis["requirements"]:
        if not set(requirement["sourceIds"]) <= source_ids:
            raise Blocked("Requirement references an unknown source.")
    dimensions = [finding["dimension"] for finding in analysis["review"]]
    if len(set(dimensions)) != 9:
        raise Blocked("Assurance review must contain each of the nine dimensions once.")
    for finding in analysis["review"]:
        if not set(finding["sourceIds"]) <= source_ids:
            raise Blocked("Review finding references an unknown source.")
    for option in analysis["options"]:
        _symbol(option["id"])
        component_ids = unique(option["components"], "component")
        unique(option["connections"], "connection")
        for component in option["components"]:
            _symbol(component["id"])
            if not set(component["requirementIds"]) <= requirement_ids:
                raise Blocked("Component references an unknown requirement.")
        for edge in option["connections"]:
            pair = (edge["source"], edge["target"])
            if not set(pair) <= component_ids:
                raise Blocked("Connection references an unknown component.")
    return next(o for o in analysis["options"] if o["id"] == option_id), schema


def _check_topology(option: dict) -> None:
    nodes = {c["id"]: c for c in option["components"]}
    pairs = {}
    for edge in option["connections"]:
        pair = (edge["source"], edge["target"])
        if edge["source"] == edge["target"]:
            raise Blocked(f"Selected option {option['id']}, connection {edge['id']}: self-connection "
                          f"{edge['source']} -> {edge['target']} is unsupported. Remove the edge or "
                          "connect distinct supported components.")
        if pair in pairs:
            raise Blocked(f"Selected option {option['id']}, connections {pairs[pair]} and {edge['id']}: "
                          f"duplicate directed pair {edge['source']} -> {edge['target']} is unsupported. "
                          "Consolidate parallel logical operations into one edge per directed pair. "
                          "For a host that both produces and consumes, use opposite host/queue edges.")
        pairs[pair] = edge["id"]
    for component in nodes.values():
        aliases = {a.casefold() for a in CATALOG["serviceAliases"][component["kind"]]}
        if component["service"].strip().casefold() not in aliases:
            raise Blocked(f"Component {component['id']} service is not a supported {component['kind']} "
                          "catalog alias. Use its actual supported Azure service, or refine the proposal; "
                          "a different service cannot be disguised as storage or external.")
        # These are essential infrastructure constraints, not executable configuration.
        prose = (component["service"] + " " + component["responsibility"]).casefold()
        if re.search(r"\b(private endpoints?|private networks?|durable functions?|event grid|sql database|"
                     r"cosmos db|postgresql|azure files|storage trigger|blob trigger|windows hosting|"
                     r"consumption plan|flex consumption|container image)\b", prose):
            raise Blocked(f"Component {component['id']} requires an unsupported deployment capability. "
                          "Refine to the documented public-endpoint, blob/queue catalog.")
    if not any(n["kind"] in APP_KINDS for n in nodes.values()):
        raise Blocked("A connected application or function host is required; an unconnected resource pile "
                      "or external-only design is not a complete supported topology.")
    touched = set()
    neighbors = {i: set() for i in nodes}
    dependencies = {i: set() for i in nodes}
    for edge in option["connections"]:
        source, target = nodes[edge["source"]], nodes[edge["target"]]
        sk, tk = source["kind"], target["kind"]
        supported = (
            sk in APP_KINDS and tk in APP_KINDS | {"storage", "servicebus", "keyvault", "external"}
            or sk == "client" and tk in APP_KINDS
            or sk == "servicebus" and tk in APP_KINDS
            or sk == "external" and tk in APP_KINDS
        )
        if not supported:
            raise Blocked(f"Connection {edge['id']}: {sk} -> {tk} has no deterministic integration "
                          "contract. Storage triggers, arbitrary events and implicit dependencies are blocked.")
        touched.update((source["id"], target["id"]))
        neighbors[source["id"]].add(target["id"])
        neighbors[target["id"]].add(source["id"])
        if sk in APP_KINDS and tk in APP_KINDS:
            dependencies[source["id"]].add(target["id"])
    if touched != set(nodes):
        raise Blocked("Every selected component must participate in a supported connection.")
    connected, pending = set(), [next(iter(nodes))]
    while pending:
        node = pending.pop()
        if node not in connected:
            connected.add(node)
            pending.extend(neighbors[node] - connected)
    if connected != set(nodes):
        raise Blocked("Selected components form disconnected deployment graphs; add explicit supported integrations.")
    visiting, visited = set(), set()

    def visit(node: str) -> None:
        if node in visiting:
            raise Blocked("Cyclic app-to-app deployment dependencies are unsupported; refine the topology.")
        if node not in visited:
            visiting.add(node)
            for child in dependencies[node]:
                visit(child)
            visiting.remove(node)
            visited.add(node)

    for node in nodes:
        visit(node)


def _template(name: str, **tokens: str) -> str:
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    for key, value in tokens.items():
        text = text.replace("@@" + key + "@@", value)
    if re.search(r"@@[A-Z_]+@@", text):
        raise RuntimeError("Server template contains an unresolved token.")
    return text


def _render(result: dict, option: dict) -> tuple[str, dict]:
    nodes = {c["id"]: c for c in sorted(option["components"], key=lambda c: c["id"])}
    seed = _hash(_json({"resultId": result["resultId"], "inputHash": result["inputHash"],
                        "optionId": option["id"]}))[:20]
    chunks = [
        "targetScope = 'resourceGroup'\n\n"
        "@description('Use the approved target resource group location, or supply an approved region; no residency validation was performed.')\n"
        "param location string = resourceGroup().location\n\n"
        "@description('Required existing tenant Entra application client ID for bearer-token validation.')\n"
        "@minLength(36)\n@maxLength(36)\nparam entraApplicationClientId string\n"
    ]
    mapping, integrations, roles = [], [], []
    prerequisites = [{"parameter": "entraApplicationClientId",
                      "required": "Existing tenant Entra API registration with api://<clientId> audience, "
                                  "requestedAccessTokenVersion=2, and appropriate browser consent."}]
    settings = {i: [] for i, c in nodes.items() if c["kind"] in APP_KINDS}
    dependencies = {i: [] for i in settings}
    clients = {i: [] for i in settings}
    symbols = {i: _symbol(i) for i in nodes}
    generated_names = {}

    def name(symbol: str, prefix: str) -> str:
        return f"'{prefix}${{uniqueString(resourceGroup().id, '{seed}', '{symbol}')}}'"

    def role(scope: str, app: str, kind: str) -> str:
        symbol = f"r_{len(roles)}"
        identity = symbols[app] + "_identity"
        rid = ROLE_IDS[kind]
        chunks.append(
            f"resource {symbol} 'Microsoft.Authorization/roleAssignments@2022-04-01' = {{\n"
            f"  name: guid({scope}.id, {name(identity, 'mi')}, '{rid}')\n"
            f"  scope: {scope}\n"
            "  properties: {\n"
            f"    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '{rid}')\n"
            f"    principalId: {identity}.outputs.principalId\n"
            "    principalType: 'ServicePrincipal'\n  }\n"
            + (f"  dependsOn: [{scope.removesuffix('_existing')}]\n" if scope.endswith("_existing") else "")
            + "}\n"
        )
        roles.append({"symbol": symbol, "scopeSymbol": scope, "applicationComponentId": app,
                      "role": kind, "roleDefinitionId": rid})
        dependencies[app].append(symbol)
        return symbol

    for identifier, component in nodes.items():
        symbol, kind = symbols[identifier], component["kind"]
        entry = {"componentId": identifier, "kind": kind,
                 "requirementIds": component["requirementIds"], "symbols": [],
                 "disposition": "existing-integration" if kind in {"external", "client"} else "generated"}
        mapping.append(entry)
        if kind in {"external", "client"}:
            prerequisites.append({"componentId": identifier, "kind": kind,
                                  "required": "Existing HTTPS API and application-side authentication"
                                  if kind == "external" else "Existing browser/OAuth client implementation"})
            if kind == "external":
                if any(edge["target"] == identifier for edge in option["connections"]):
                    prerequisites[-1]["parameter"] = symbol + "_url"
                    chunks.append(f"@description('Required existing HTTPS API URL; no credentials in this parameter.')\n"
                                  f"@minLength(9)\nparam {symbol}_url string\n")
                if any(edge["source"] == identifier for edge in option["connections"]):
                    caller = symbol + "_callerClientId"
                    chunks.append(
                        "@description('Required existing same-tenant Entra caller client ID for authenticated callbacks. An adapter is required if the external provider cannot obtain an Entra bearer token.')\n"
                        f"@minLength(36)\n@maxLength(36)\nparam {caller} string\n"
                    )
                    prerequisites.append({"componentId": identifier, "parameter": caller,
                                          "required": "Existing same-tenant Entra OAuth caller or authenticated adapter; provider webhook compatibility is unverified."})
            continue
        generated_names[identifier] = name(symbol, {
            "appservice": "app", "functions": "func", "storage": "st",
            "servicebus": "sb", "keyvault": "kv",
        }[kind])
        if kind in APP_KINDS:
            entry["symbols"] = [symbol, symbol + "_plan", symbol + "_identity",
                                symbol + "_auth", symbol + "_ftp", symbol + "_scm"]
            chunks.append(
                f"module {symbol}_identity '{CATALOG['avm']['identity']}' = {{\n"
                f"  name: '{symbol}_identity'\n  params: {{\n"
                f"    name: {name(symbol + '_identity', 'mi')}\n"
                "    location: location\n    enableTelemetry: false\n  }\n}\n"
                f"module {symbol}_plan '{CATALOG['avm']['plan']}' = {{\n"
                f"  name: '{symbol}_plan'\n  params: {{\n"
                f"    name: {name(symbol + '_plan', 'plan')}\n"
                "    location: location\n    kind: 'linux'\n    reserved: true\n"
                "    skuName: 'B1'\n    skuCapacity: 1\n    enableTelemetry: false\n  }\n}\n"
            )
            settings[identifier].append(("AZURE_CLIENT_ID", f"{symbol}_identity.outputs.clientId"))
            if kind == "functions":
                host = symbol + "_host"
                entry["symbols"] += [host, host + "_blob", host + "_data"]
                entry["hosting"] = "Dedicated Linux B1; Functions v4 Python 3.12; deploy package separately"
                chunks.append(_template("storage.bicep.tmpl", SYMBOL=host, NAME=name(host, "st")))
                role(host, identifier, "blob-owner")
                role(host, identifier, "queue-contributor")
                settings[identifier] += [
                    ("FUNCTIONS_EXTENSION_VERSION", "'~4'"),
                    ("FUNCTIONS_WORKER_RUNTIME", "'python'"),
                    ("WEBSITE_RUN_FROM_PACKAGE", "'1'"),
                    ("AzureWebJobsStorage__accountName", f"{host}.name"),
                    ("AzureWebJobsStorage__credential", "'managedidentity'"),
                    ("AzureWebJobsStorage__clientId", f"{symbol}_identity.outputs.clientId"),
                ]
        elif kind in {"storage", "servicebus"}:
            chunks.append(_template(f"{kind}.bicep.tmpl", SYMBOL=symbol, NAME=generated_names[identifier]))
            entry["symbols"] = [symbol, symbol + "_blob", symbol + "_data"] if kind == "storage" else [
                symbol, symbol + "_queue"]
        elif kind == "keyvault":
            chunks.append(
                f"module {symbol} '{CATALOG['avm']['vault']}' = {{\n"
                f"  name: '{symbol}'\n  params: {{\n    name: {generated_names[identifier]}\n"
                "    location: location\n    sku: 'standard'\n"
                "    enableTelemetry: false\n    enableRbacAuthorization: true\n"
                "    enablePurgeProtection: true\n    enableSoftDelete: true\n"
                "    enableVaultForDeployment: false\n    enableVaultForTemplateDeployment: false\n"
                "    enableVaultForDiskEncryption: false\n    publicNetworkAccess: 'Enabled'\n"
                "    networkAcls: { bypass: 'None', defaultAction: 'Allow' }\n  }\n}\n"
                f"resource {symbol}_existing 'Microsoft.KeyVault/vaults@2024-11-01' existing = {{\n"
                f"  name: {generated_names[identifier]}\n}}\n"
            )
            entry["symbols"] = [symbol]

    for edge in sorted(option["connections"], key=lambda e: e["id"]):
        source, target = nodes[edge["source"]], nodes[edge["target"]]
        sk, tk = source["kind"], target["kind"]
        ss, ts = symbols[source["id"]], symbols[target["id"]]
        integration = dict(edge, settings=[], roleSymbols=[], authentication="Entra managed identity")
        integrations.append(integration)
        if sk == "client":
            integration.update(authentication="Existing Entra OAuth client; bearer token required",
                               endpointOutput=ts + "_endpoint")
            continue
        if sk == "external":
            caller = ss + "_callerClientId"
            clients[target["id"]].append(caller)
            integration.update(
                authentication="Existing same-tenant Entra OAuth caller; bearer token required",
                callerClientIdParameter=caller, endpointOutput=ts + "_endpoint",
                applicationPrerequisite="Implement authenticated callback handler and replay protection. An adapter is required if the provider cannot obtain an Entra token; signed provider-native webhooks are not generated.",
            )
            continue
        if sk == "servicebus":
            app, setting, scope, permission = target["id"], ss, ss + "_queue", "bus-receiver"
            values = [(setting.upper() + "__fullyQualifiedNamespace",
                       f"'${{{ss}.name}}.servicebus.windows.net'"),
                      (setting.upper() + "__credential", "'managedidentity'"),
                      (setting.upper() + "__clientId", f"{ts}_identity.outputs.clientId"),
                      (setting.upper() + "_QUEUE", "'work'")]
            integration["applicationPrerequisite"] = "Implement queue handler using Service Bus extension 5.x+ or SDK."
        else:
            app, setting = source["id"], ts
            if tk == "storage":
                scope, permission = ts + "_data", "blob-contributor"
                values = [(setting.upper() + "_BLOB_ENDPOINT", f"{ts}.properties.primaryEndpoints.blob"),
                          (setting.upper() + "_CONTAINER", "'data'")]
            elif tk == "servicebus":
                scope, permission = ts + "_queue", "bus-sender"
                values = [(setting.upper() + "__fullyQualifiedNamespace",
                           f"'${{{ts}.name}}.servicebus.windows.net'"),
                          (setting.upper() + "__credential", "'managedidentity'"),
                          (setting.upper() + "__clientId", f"{ss}_identity.outputs.clientId"),
                          (setting.upper() + "_QUEUE", "'work'")]
            elif tk == "keyvault":
                scope, permission = ts + "_existing", "secrets-user"
                values = [(setting.upper() + "_VAULT_URI", f"{ts}.outputs.uri")]
                integration["applicationPrerequisite"] = "Provision required secret values separately; package contains none."
            elif tk in APP_KINDS:
                scope = permission = None
                values = [(setting.upper() + "_ENDPOINT", f"'https://${{{ts}.properties.defaultHostName}}'"),
                          (setting.upper() + "_SCOPE", "'api://${entraApplicationClientId}/.default'")]
                dependencies[app].append(ts)
                clients[target["id"]].append(f"{ss}_identity.outputs.clientId")
                integration["applicationPrerequisite"] = "Acquire a managed-identity bearer token for the supplied scope."
            else:
                scope = permission = None
                values = [(setting.upper() + "_ENDPOINT", ts + "_url")]
                integration["authentication"] = "Existing external API authentication implemented by application"
                integration["endpointParameter"] = ts + "_url"
        settings[app].extend(values)
        integration["settings"] = [key for key, _ in values]
        if permission:
            integration["roleSymbols"].append(role(scope, app, permission))

    for identifier, component in nodes.items():
        symbol, kind = symbols[identifier], component["kind"]
        if kind in APP_KINDS:
            # Multiple send/receive edges can share a namespace: emit each setting once.
            app_settings = dict(settings[identifier])
            chunks.append(_template(
                "site.bicep.tmpl", SYMBOL=symbol, NAME=generated_names[identifier],
                IDENTITY_NAME=name(symbol + "_identity", "mi"),
                KIND="functionapp,linux" if kind == "functions" else "app,linux",
                RUNTIME="PYTHON|3.12" if kind == "functions" else "NODE|22-lts",
                SETTINGS="\n".join(f"        {{ name: '{key}', value: {value} }}" for key, value in app_settings.items()),
                DEPENDENCIES="\n".join("    " + d for d in sorted(set(dependencies[identifier]))),
                ALLOWED_CLIENTS="\n".join("                    " + c for c in sorted(set(clients[identifier]))),
            ))
            chunks.append(f"output {symbol}_endpoint string = 'https://${{{symbol}.properties.defaultHostName}}'\n"
                          f"output {symbol}_identityClientId string = {symbol}_identity.outputs.clientId\n"
                          f"output {symbol}_resourceId string = {symbol}.id\n")
        elif kind == "storage":
            chunks.append(f"output {symbol}_endpoint string = {symbol}.properties.primaryEndpoints.blob\n"
                          f"output {symbol}_resourceId string = {symbol}.id\n")
        elif kind == "servicebus":
            chunks.append(f"output {symbol}_endpoint string = '${{{symbol}.name}}.servicebus.windows.net'\n"
                          f"output {symbol}_resourceId string = {symbol}.id\n")
        elif kind == "keyvault":
            chunks.append(f"output {symbol}_endpoint string = {symbol}.outputs.uri\n"
                          f"output {symbol}_resourceId string = {symbol}.outputs.resourceId\n")
    return "\n".join(chunks), {"components": mapping, "connections": integrations,
                               "roleAssignments": roles, "externalPrerequisites": prerequisites}


def _compiler() -> tuple[Path, str, dict]:
    errors = []
    for path in COMPILER_PATHS:
        if not path.is_file():
            continue
        try:
            command = [str(path), "--version"]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=15,
                                       shell=False, check=False)
            version = (completed.stdout + completed.stderr).strip()
            match = re.search(r"Bicep CLI version (\d+)\.(\d+)\.(\d+)", version)
            if completed.returncode != 0 or not match:
                errors.append("Approved compiler version verification failed.")
                continue
            minimum = tuple(int(p) for p in CATALOG["compilerMinimum"].split("."))
            if tuple(map(int, match.groups())) < minimum:
                errors.append(f"Approved compiler is below supported minimum {CATALOG['compilerMinimum']}.")
                continue
            return path, version, {"command": command, "exitCode": completed.returncode}
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"Approved compiler version verification failed: {type(exc).__name__}.")
    raise Blocked("Bicep compiler unavailable or unsupported. Restore an approved local compiler; "
                  "no automatic installation or deployment attempted. " + " ".join(errors))


def _build_dir(output_root: Path, build_id: str) -> Path:
    root = Path(output_root).absolute()
    approved = [REPO / ".intent-to-impact" / "studio" / "builds",
                REPO / ".intent-to-impact" / "studio" / "runs" / "builds",
                REPO / ".intent-to-impact" / "spikes" / "STUDIO-BUNDLE"]
    if any(part.is_symlink() for part in [root, *root.parents]):
        raise Blocked("Server output root must not traverse symbolic links.")
    root = root.resolve()
    if not any(root == parent.resolve() or parent.resolve() in root.parents for parent in approved):
        raise Blocked("Server output root is outside the approved studio build/evidence directories.")
    directory = root / build_id
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def build_bundle(result: dict, option_id: str, output_root: Path) -> dict:
    """Return the exact shared BuildResult; a download exists only after a real successful compile."""
    build_id = uuid.uuid4().hex
    receipt = {
        "buildId": build_id,
        "resultId": result.get("resultId", "") if isinstance(result, dict) and isinstance(result.get("resultId"), str) else "",
        "optionId": option_id if isinstance(option_id, str) else "",
        "status": "blocked", "compilerVersion": None, "exitCode": None,
        "diagnostics": "", "files": [], "downloadUrl": None,
        "limitations": list(LIMITATIONS), "deploymentStatus": "not-deployed",
    }
    directory = None
    contents = {}
    validation = {"status": "blocked", "deploymentStatus": "not-deployed",
                  "azureOperations": [], "targetPreflight": "not-run", "commands": []}
    try:
        directory = _build_dir(output_root, build_id)
        option, _ = _validate(result, option_id)
        _check_topology(option)
        source, mapping = _render(result, option)
        contents = {
            "main.bicep": source,
            "main.parameters.json": _json({
                "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
                "contentVersion": "1.0.0.0", "parameters": {},
            }),
            "README.md": (TEMPLATES / "README.md").read_text(encoding="utf-8"),
            "catalog.json": _json(CATALOG),
            "bicepconfig.json": _json({
                "cloud": {"currentProfile": "AzureCloud"},
                "moduleAliases": {"br": {"public": {"registry": "mcr.microsoft.com", "modulePath": "bicep"}}},
            }),
        }
        manifest = {
            "schemaVersion": "1.0.0", "buildId": build_id, "resultId": result["resultId"],
            "inputHash": result["inputHash"], "optionId": option_id,
            "resultSha256": _hash(_json(result)), "selectedOptionSha256": _hash(_json(option)),
            "schemaSha256": _hash(SCHEMA_PATH.read_bytes()),
            "catalog": CATALOG,
            "templateHashes": {p.name: _hash(p.read_bytes()) for p in sorted(TEMPLATES.iterdir()) if p.is_file()},
            "origin": result["origin"], "createdAt": result["createdAt"],
            "sources": result["sources"], "requirements": result["analysis"]["requirements"],
            "selectedOption": option,
            "modelReceipts": [{"receipt": r, "sha256": _hash(_json(r))} for r in result["modelReceipts"]],
            "mapping": mapping, "limitations": receipt["limitations"],
            "deploymentStatus": "not-deployed",
        }
        for filename, text in contents.items():
            (directory / filename).write_text(text, encoding="utf-8", newline="\n")
        # Bicep 0.47 requires an absolute cache path. Only the local compile uses it;
        # the downloadable configuration stays portable and uses normal CLI defaults.
        compile_configuration = dict(json.loads(contents["bicepconfig.json"]),
                                     cacheRootDirectory=str(directory / ".bicep-cache"))
        (directory / "bicepconfig.json").write_text(_json(compile_configuration), encoding="utf-8", newline="\n")
        validation["compilationConfiguration"] = compile_configuration
        compiler, version, version_check = _compiler()
        receipt["compilerVersion"] = version
        validation["commands"].append(version_check)
        command = [str(compiler), "build", str(directory / "main.bicep"),
                   "--outfile", str(directory / "main.json")]
        env = dict(os.environ)
        validation["commands"].append({"command": command, "timeoutSeconds": BUILD_TIMEOUT,
                                       "shell": False, "cacheRoot": str(directory / ".bicep-cache")})
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=BUILD_TIMEOUT,
                                       shell=False, check=False, cwd=str(directory), env=env)
        except subprocess.TimeoutExpired as exc:
            validation["commands"][-1]["exitCode"] = None
            validation["commands"][-1]["timedOut"] = True
            raise RuntimeError(f"Bicep compilation timed out after {BUILD_TIMEOUT} seconds.") from exc
        receipt["exitCode"] = completed.returncode
        validation["commands"][-1]["exitCode"] = completed.returncode
        receipt["diagnostics"] = (completed.stdout + completed.stderr).strip()
        if completed.returncode != 0:
            receipt["status"] = "failed"
        else:
            arm_path = directory / "main.json"
            if not arm_path.is_file():
                raise RuntimeError("Compiler exited 0 without producing main.json.")
            arm_text = arm_path.read_text(encoding="utf-8-sig")
            arm = json.loads(arm_text)
            if not isinstance(arm.get("resources"), (list, dict)) or not arm["resources"]:
                raise RuntimeError("Compiler output is not a nonempty ARM resource template.")
            if re.search(r"\blistkeys\s*\(", arm_text, re.IGNORECASE):
                raise Blocked("Restored module contains forbidden key retrieval. Update the pinned key-free catalog.")
            contents["main.json"] = arm_text
            receipt["status"] = "compiled"
            receipt["diagnostics"] = receipt["diagnostics"] or "Bicep compilation succeeded (exit 0). Target preflight not run."
        manifest["fileHashes"] = {name: _hash(text) for name, text in contents.items()}
        manifest["restoredModuleHashes"] = {
            p.relative_to(directory / ".bicep-cache").as_posix(): _hash(p.read_bytes())
            for p in sorted((directory / ".bicep-cache").rglob("*.json")) if p.is_file()
        }
        contents["manifest.json"] = _json(manifest)
    except Blocked as exc:
        receipt["status"], receipt["diagnostics"] = "blocked", str(exc)
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        receipt["status"], receipt["diagnostics"] = "failed", f"{type(exc).__name__}: {exc}"
    validation.update(status=receipt["status"], compilerVersion=receipt["compilerVersion"],
                      exitCode=receipt["exitCode"], diagnostics=receipt["diagnostics"],
                      limitations=receipt["limitations"])
    contents["validation.json"] = _json(validation)
    if directory is not None:
        try:
            for filename, text in sorted(contents.items()):
                (directory / filename).write_text(text, encoding="utf-8", newline="\n")
                receipt["files"].append({"path": filename, "content": text, "sha256": _hash(text)})
            if receipt["status"] == "compiled":
                package = directory / "package.zip"
                with zipfile.ZipFile(package, "x", compression=zipfile.ZIP_DEFLATED) as archive:
                    for filename, text in sorted(contents.items()):
                        entry = zipfile.ZipInfo(filename, date_time=(1980, 1, 1, 0, 0, 0))
                        entry.compress_type = zipfile.ZIP_DEFLATED
                        entry.external_attr = 0o100644 << 16
                        archive.writestr(entry, text.encode("utf-8"))
                receipt["downloadUrl"] = f"/api/studio/builds/{build_id}/download"
            (directory / "receipt.json").write_text(_json(receipt), encoding="utf-8", newline="\n")
        except OSError as exc:
            receipt.update(status="failed", downloadUrl=None, diagnostics=f"Package persistence failed: {exc}")
    return receipt
