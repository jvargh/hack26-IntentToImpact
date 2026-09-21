"""Narrow candidate/observation guards; not canonical V3 contracts or live proof."""

import json
from decimal import Decimal, InvalidOperation

from evidence import (
    ACCOUNT, ASSOCIATION, ASSOCIATION_ID, GROUP, LOCATION, NSP, NSP_ID, PLANNED_IDS,
    PROFILE, PROFILE_ID, RG_ID, STORAGE_ID, SUB, TENANT, require,
)


PARAMETERS = {"location": LOCATION, "resourceGroupName": GROUP, "storageAccountName": ACCOUNT,
              "perimeterName": NSP, "profileName": PROFILE, "associationName": ASSOCIATION}
STORAGE_TYPE = "Microsoft.Storage/storageAccounts"
NSP_TYPE = "Microsoft.Network/networkSecurityPerimeters"
PROFILE_TYPE = NSP_TYPE + "/profiles"
ASSOCIATION_TYPE = NSP_TYPE + "/resourceAssociations"
RESOURCE_TYPES = ["Microsoft.Resources/resourceGroups", STORAGE_TYPE, NSP_TYPE, PROFILE_TYPE,
                  ASSOCIATION_TYPE, "Microsoft.Resources/deployments"]
STORAGE_PROPERTIES = {
    "accessTier": "Hot", "publicNetworkAccess": "SecuredByPerimeter", "supportsHttpsTrafficOnly": True,
    "allowBlobPublicAccess": False, "allowSharedKeyAccess": False, "minimumTlsVersion": "TLS1_2",
    "isHnsEnabled": False,
    "networkAcls": {"defaultAction": "Deny", "bypass": "None", "ipRules": [], "virtualNetworkRules": []},
}
TAGS = {"local-decision-id": "LOCAL-09"}


def decision_guard(decision, parameters):
    require(decision.get("decisionId") == "LOCAL-09", "LOCAL-09 decision required; old approval is not authorization")
    require(decision.get("status") == "topology-and-access-mode-confirmed-deployment-pending", "Unexpected decision state")
    target = decision["target"]
    expected = {"subscriptionId": SUB, "tenantId": TENANT, "resourceGroupName": GROUP,
                "storageAccountName": ACCOUNT, "location": LOCATION,
                "desiredPublicNetworkAccess": "SecuredByPerimeter", "associationAccessMode": "Enforced",
                "inboundAccessRules": [], "outboundAccessRules": [], "supportsHttpsTrafficOnly": True,
                "allowBlobPublicAccess": False, "allowSharedKeyAccess": False, "minimumTlsVersion": "TLS1_2",
                "fallbackNetworkDefaultAction": "Deny", "fallbackNetworkBypass": "None"}
    require(all(key in target and type(target[key]) is type(value) and target[key] == value
                for key, value in expected.items()), "Decision scope/settings changed")
    require(decision["deploymentAuthorization"]["priorApprovalMayBeReusedForNsp"] is False, "Old approval cannot authorize NSP")
    require(decision["deploymentAuthorization"]["finalRiskAcknowledgedConfirmation"] == "pending", "Re-review changed authorization")
    require(parameters["parameters"] == {key: {"value": value} for key, value in PARAMETERS.items()}, "Changed parameter/scope")


def final_confirmation_guard(confirmation, compiled_hash, parameter_hash, decision_hash):
    require(confirmation.get("decisionId") == "LOCAL-09", "Old creation approval rejected")
    require(confirmation.get("recordType") == "explicit-risk-acknowledged-deployment-consent", "Final risk acknowledgement missing")
    require(confirmation.get("acknowledgedRisks") is True, "Risks not acknowledged")
    require(confirmation.get("compiledSha256") == compiled_hash and
            confirmation.get("parametersSha256") == parameter_hash and
            confirmation.get("decisionSha256") == decision_hash, "Changed immutable candidate/input")
    require(confirmation.get("plannedResourceIds") == PLANNED_IDS, "Approval resource/scope mismatch")
    require(confirmation.get("seedApproved") is False and confirmation.get("cleanupApproved") is False,
            "Unexpected seed/cleanup authority")


def plan_guard(plan):
    require(plan["meta"]["status"] == "draft" and plan["meta"]["deploymentReady"] is False, "Plan must not claim deployment approval")
    require(plan["meta"]["actualDeploymentId"] is None and plan["meta"]["actualResourceIds"] == [], "No actual deployment IDs exist")
    require(plan["authorization"]["priorApprovalMayBeReused"] is False and
            plan["authorization"]["finalDeploymentConfirmation"] == "pending", "Wrong approval boundary")
    require(plan["contractSeam"]["canonicalScenarioId"] is None and plan["contractSeam"]["canonicalScenarioHash"] is None,
            "Canonical V3 binding must remain pending")
    resources = plan["plan"]["resources"]
    require(len(resources) == 5, "Plan must contain exactly five resources")
    by_name = {resource["name"]: resource for resource in resources}
    expected = {
        GROUP: ("Microsoft.Resources/resourceGroups", []),
        NSP: (NSP_TYPE, [GROUP]),
        PROFILE: (PROFILE_TYPE, [NSP]),
        ACCOUNT: (STORAGE_TYPE, [PROFILE]),
        ASSOCIATION: (ASSOCIATION_TYPE, [NSP, PROFILE, ACCOUNT]),
    }
    require(set(by_name) == set(expected), "Plan resource names changed")
    for name, (kind, dependencies) in expected.items():
        resource = by_name[name]
        require(resource["type"] == kind and resource["location"] == LOCATION and resource["actualResourceId"] is None,
                "Plan type/location/actual ID mismatch")
        require(set(resource["dependencies"]) == set(dependencies), "Plan dependency/order mismatch")
    require(by_name[PROFILE]["properties"] == {} and by_name[PROFILE]["accessRuleResources"] == [], "Plan profile must be empty")
    require(by_name[NSP]["properties"] == {}, "Unexpected NSP plan properties")
    require(by_name[ACCOUNT]["properties"] == STORAGE_PROPERTIES and by_name[ACCOUNT]["sku"] == "Standard_LRS" and
            by_name[ACCOUNT]["subtype"] == "StorageV2", "Plan storage settings mismatch")
    require(by_name[ASSOCIATION]["properties"] == {"accessMode": "Enforced",
            "privateLinkResource": {"id": STORAGE_ID}, "profile": {"id": PROFILE_ID}}, "Plan association mismatch")


def template_guard(template):
    require("subscriptionDeploymentTemplate" in template.get("$schema", ""), "Wrong deployment scope")
    require(set(template["parameters"]) == set(PARAMETERS), "Unexpected root parameters")
    for key, value in PARAMETERS.items():
        require(template["parameters"][key].get("allowedValues") == [value], f"Unpinned parameter {key}")
    require(len(template["resources"]) == 2, "Only new RG plus local deployment metadata allowed")
    group, module = template["resources"]
    require(group == {"type": "Microsoft.Resources/resourceGroups", "apiVersion": "2024-03-01",
                      "name": "[parameters('resourceGroupName')]", "location": "[parameters('location')]", "tags": TAGS},
            "Unauthorized RG resource/fields/tags")
    require(module["type"] == "Microsoft.Resources/deployments" and module["name"] == "local09-sandbox" and
            module["resourceGroup"] == "[parameters('resourceGroupName')]", "Wrong nested scope")
    require(set(module) == {"type", "apiVersion", "name", "resourceGroup", "properties", "dependsOn"}, "Unexpected deployment fields")
    p = module["properties"]
    require(p["mode"] == "Incremental" and set(p) == {"mode", "expressionEvaluationOptions", "parameters", "template"},
            "Remote or destructive deployment is forbidden")
    require(p["parameters"] == {key: {"value": f"[parameters('{key}')]"}
                               for key in PARAMETERS if key != "resourceGroupName"}, "Wrong nested parameter binding")
    children = p["template"]["resources"]
    require(len(children) == 4, "Exactly storage, NSP, profile and association required; no extra rules/resources")
    by_type = {r["type"]: r for r in children}
    require(set(by_type) == {STORAGE_TYPE, NSP_TYPE, PROFILE_TYPE, ASSOCIATION_TYPE}, "Unexpected or duplicate child resource type")
    nsp, profile, account, association = (by_type[t] for t in [NSP_TYPE, PROFILE_TYPE, STORAGE_TYPE, ASSOCIATION_TYPE])
    require(nsp == {"type": NSP_TYPE, "apiVersion": "2025-01-01", "name": "[parameters('perimeterName')]",
                    "location": "[parameters('location')]", "tags": TAGS, "properties": {}}, "NSP fields mismatch")
    require(profile["apiVersion"] == "2025-01-01" and profile["properties"] == {}, "Profile must have zero rules")
    require(profile["name"] == "[format('{0}/{1}', parameters('perimeterName'), parameters('profileName'))]", "Profile binding mismatch")
    require(set(profile) == {"type", "apiVersion", "name", "properties", "dependsOn"}, "Unexpected profile fields")
    require(account["apiVersion"] == "2025-06-01" and account["kind"] == "StorageV2" and
            account["sku"] == {"name": "Standard_LRS"}, "Storage API/kind/SKU mismatch")
    require(account["name"] == "[parameters('storageAccountName')]" and account["location"] == "[parameters('location')]",
            "Storage name/region mismatch")
    require(account["properties"] == STORAGE_PROPERTIES, "Unsafe or changed storage controls")
    require(all(type(account["properties"][key]) is type(value) for key, value in STORAGE_PROPERTIES.items()),
            "Wrong compiled storage property types")
    require(account["tags"] == {**TAGS, "architecture-component-id": "CMP-CLAIMS-STORE"}, "Storage tags/exclusion mismatch")
    require(set(account) == {"type", "apiVersion", "name", "location", "kind", "sku", "properties", "tags", "dependsOn"},
            "Extra storage identity/child/field")
    profile_ref = "[resourceId('Microsoft.Network/networkSecurityPerimeters/profiles', parameters('perimeterName'), parameters('profileName'))]"
    storage_ref = "[resourceId('Microsoft.Storage/storageAccounts', parameters('storageAccountName'))]"
    require(profile_ref in account["dependsOn"], "Storage must wait for the profile")
    require(association["apiVersion"] == "2025-01-01" and association["name"] ==
            "[format('{0}/{1}', parameters('perimeterName'), parameters('associationName'))]", "Association name/API mismatch")
    require(association["properties"] == {"accessMode": "Enforced", "privateLinkResource": {"id": storage_ref},
                                          "profile": {"id": profile_ref}}, "Real Enforced storage/profile association required")
    require({storage_ref, profile_ref} <= set(association["dependsOn"]), "Unsafe association dependency order")
    require(set(association) == {"type", "apiVersion", "name", "properties", "dependsOn"}, "Unexpected association fields")
    for forbidden in ["listkeys(", "listaccountsas(", "listservicesas(", "securitycontrol", "roleassignments"]:
        require(forbidden not in json.dumps(template).lower(), f"Forbidden operation/exclusion: {forbidden}")
    return by_type


def absence_guard(group_exists, account_name):
    require(group_exists is False and account_name.get("nameAvailable") is True, "Existing/unknown target; no adoption or update")


def preview_guard(result):
    require(result.get("error") is None, "Failed what-if")
    expected = {identifier.lower() for identifier in PLANNED_IDS}
    seen = set()
    kinds = {RG_ID.lower(): "Microsoft.Resources/resourceGroups", STORAGE_ID.lower(): STORAGE_TYPE,
             NSP_ID.lower(): NSP_TYPE, PROFILE_ID.lower(): PROFILE_TYPE, ASSOCIATION_ID.lower(): ASSOCIATION_TYPE}
    for change in result.get("changes", []):
        require(change.get("changeType") == "Create", "Existing target, update, partial or unknown what-if outcome")
        identifier = change["resourceId"].lower()
        require(identifier in expected and identifier not in seen, "Unexpected or duplicate what-if resource")
        seen.add(identifier)
        after = change["after"]
        require(after["id"].lower() == identifier and after["type"] == kinds[identifier], "Incomplete/wrong preview binding")
        allowed_fields = {"apiVersion", "id", "name", "type", "resourceGroup"}
        if identifier in {RG_ID.lower(), NSP_ID.lower(), STORAGE_ID.lower()}:
            allowed_fields |= {"location", "tags"}
        if identifier != RG_ID.lower():
            allowed_fields.add("properties")
        if identifier == STORAGE_ID.lower():
            allowed_fields |= {"kind", "sku"}
        require(set(after) <= allowed_fields and after["name"].lower() == identifier.rsplit("/", 1)[1],
                "Unexpected preview fields/name")
        version = "2025-06-01" if identifier == STORAGE_ID.lower() else "2024-03-01" if identifier == RG_ID.lower() else "2025-01-01"
        require(after["apiVersion"] == version, "Preview API changed")
        require(after.get("resourceGroup", GROUP) == GROUP, "Preview scope changed")
        if identifier in {RG_ID.lower(), NSP_ID.lower(), STORAGE_ID.lower()}:
            require(after["location"] == LOCATION, "Preview region changed")
            require(after["tags"] == ({**TAGS, "architecture-component-id": "CMP-CLAIMS-STORE"}
                                      if identifier == STORAGE_ID.lower() else TAGS), "Preview tags/exclusion changed")
        if identifier in {NSP_ID.lower(), PROFILE_ID.lower()}:
            # What-if elides empty objects/arrays; future deployed observation guards remain stricter.
            require(after.get("properties", {}) == {}, "NSP/profile is not empty")
        if identifier == STORAGE_ID.lower():
            require(after["kind"] == "StorageV2" and after["sku"] == {"name": "Standard_LRS"}, "Preview storage kind/SKU changed")
            properties = after["properties"]
            require(set(properties) == set(STORAGE_PROPERTIES), "Preview omitted or added storage properties")
            for key, value in STORAGE_PROPERTIES.items():
                if key == "networkAcls":
                    acl = properties[key]
                    require(set(acl) <= set(value), "Unexpected preview ACL property")
                    require(acl["defaultAction"] == "Deny" and acl["bypass"] == "None", "Preview fallback changed")
                    require(acl.get("ipRules", []) == [] and acl.get("virtualNetworkRules", []) == [],
                            "Preview contains network rules")
                else:
                    require(type(properties[key]) is type(value) and properties[key] == value, f"Preview property changed: {key}")
        if identifier == ASSOCIATION_ID.lower():
            properties = after["properties"]
            require(set(properties) == {"accessMode", "privateLinkResource", "profile"} and
                    properties["accessMode"] == "Enforced" and
                    properties["privateLinkResource"]["id"].lower() == STORAGE_ID.lower() and
                    properties["profile"]["id"].lower() == PROFILE_ID.lower(), "Preview association/mode changed")
            for key in ["privateLinkResource", "profile"]:
                require(set(properties[key]) <= {"id", "resourceGroup"} and
                        properties[key].get("resourceGroup", GROUP) == GROUP, "Unexpected association reference scope")
    require(seen == expected, "What-if does not establish all five exact creates")


def _version(value):
    require(type(value) in [str, int, float] and str(value) != "", "Missing configuration version")
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return str(value)


def observation_guard(observation):
    """Future adapter seam only. Unit examples are fixtures, never live baseline evidence."""
    storage = observation["storage"]
    require(storage["id"].lower() == STORAGE_ID.lower(), "Wrong actual storage binding")
    for key, expected in STORAGE_PROPERTIES.items():
        actual = storage["properties"][key]
        if key == "networkAcls":
            require(all(actual.get(k) == value for k, value in expected.items()), "Fallback network mismatch")
        else:
            require(type(actual) is type(expected) and actual == expected, f"Observed storage mismatch: {key}")
    objects = [("nsp", NSP_ID), ("profile", PROFILE_ID), ("association", ASSOCIATION_ID)]
    for name, identifier in objects:
        require(observation[name]["id"].lower() == identifier.lower(), f"Wrong {name} binding")
        if name != "profile":
            require(observation[name]["properties"]["provisioningState"] == "Succeeded", f"{name} not provisioned")
    association = observation["association"]["properties"]
    require(association["accessMode"] == "Enforced" and association["profile"]["id"].lower() == PROFILE_ID.lower() and
            association["privateLinkResource"]["id"].lower() == STORAGE_ID.lower(), "Missing real Enforced association/profile")
    require(association["hasProvisioningIssues"] == "no", "Association has provisioning issues")
    rules = observation["profileRules"]
    require(rules["value"] == [] and not rules.get("nextLink"), "External rules or incomplete inventory")
    configs = observation["storageConfigurations"]
    require(len(configs["value"]) == 1 and not configs.get("nextLink"), "Missing/multiple/incomplete provider configuration")
    config = configs["value"][0]["properties"]
    require(config["provisioningState"] == "Succeeded" and config["provisioningIssues"] == [], "Provider configuration not synchronized")
    require(config["networkSecurityPerimeter"]["id"].lower() == NSP_ID.lower(), "Wrong synchronized perimeter")
    require(bool(observation["nsp"]["properties"]["perimeterGuid"]) and
            config["networkSecurityPerimeter"]["perimeterGuid"] == observation["nsp"]["properties"]["perimeterGuid"],
            "Perimeter generation mismatch")
    require(config["resourceAssociation"]["name"] == ASSOCIATION and config["resourceAssociation"]["accessMode"] == "Enforced",
            "Wrong synchronized association")
    require(config["profile"]["name"] == PROFILE and config["profile"]["accessRules"] == [], "Wrong/stale effective profile rules")
    require(_version(config["profile"]["accessRulesVersion"]) ==
            _version(observation["profile"]["properties"]["accessRulesVersion"]), "Profile version not synchronized")
    require(storage["properties"]["provisioningState"] == "Succeeded", "Storage not provisioned")
    return {"technicalConfigurationComplete": True, "dataPlaneBlockingTestPerformed": False,
            "canonicalScenarioBinding": None}
