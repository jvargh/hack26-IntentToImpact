"""Read-only LOCAL-09 transport, reusing prior captured-command mechanics only."""

from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import urllib.parse
import urllib.request


SOURCE = Path(__file__).resolve().parent
WORKSPACE = SOURCE.parents[3]
ROOT = WORKSPACE.parent if WORKSPACE.name == "intent-to-impact-studio" else WORKSPACE
OWNED = ROOT / ".intent-to-impact" / "spikes" / "SPK-03-01" / "LOCAL-09"
DECISION = ROOT / ".intent-to-impact" / "execution" / "decisions" / "LOCAL-09.json"
SUB = "463a82d4-1896-4332-aeeb-618ee5a5aa93"
TENANT = "5bb5fa45-2dcc-4310-bbc5-883021e9d84b"
GROUP = "rg-intent-to-impact-demo"
ACCOUNT = "iticlaimsv2a4f726"
LOCATION = "eastus2"
NSP = "nsp-iticlaims-local09"
PROFILE = "profile-closed"
ASSOCIATION = "assoc-iticlaimsv2a4f726"
SUB_ID = f"/subscriptions/{SUB}"
RG_ID = f"{SUB_ID}/resourceGroups/{GROUP}"
STORAGE_ID = f"{RG_ID}/providers/Microsoft.Storage/storageAccounts/{ACCOUNT}"
NSP_ID = f"{RG_ID}/providers/Microsoft.Network/networkSecurityPerimeters/{NSP}"
PROFILE_ID = f"{NSP_ID}/profiles/{PROFILE}"
ASSOCIATION_ID = f"{NSP_ID}/resourceAssociations/{ASSOCIATION}"
PLANNED_IDS = [RG_ID, STORAGE_ID, NSP_ID, PROFILE_ID, ASSOCIATION_ID]

_spec = importlib.util.spec_from_file_location(
    "historical_transport_only", SOURCE.parent / "APPROVAL-SANDBOX-CREATE-001" / "bootstrap.py")
_transport = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_transport)
load, sha, write_json, require, now = (
    _transport.load, _transport.sha, _transport.write_json, _transport.require, _transport.now)


class ReadOnlyRun:
    save = _transport.Run.save
    redact = _transport.Run.redact
    data = _transport.Run.data
    rest = _transport.Run.rest

    def __init__(self, purpose):
        for path in [ROOT / ".intent-to-impact", OWNED.parent, OWNED]:
            require(not path.is_symlink() and not getattr(path, "is_junction", lambda: False)(), "Reparse output root")
        self.root = OWNED / (purpose + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        self.root.mkdir(parents=True, exist_ok=False)
        self.az = shutil.which("az") or "az"
        azure_python = Path(self.az).parent.parent / "python.exe"
        require(azure_python.is_file(), "Expected existing MSI Azure CLI entrypoint unavailable")
        self.az_prefix = [str(azure_python), "-IBm", "azure.cli"]
        self.environment = os.environ.copy()
        self.environment.update({
            "AZ_INSTALLER": "MSI", "AZURE_CORE_COLLECT_TELEMETRY": "false",
            "AZURE_CORE_CHECK_VERSION": "false", "AZURE_BICEP_CHECK_VERSION": "false",
            "AZURE_LOGGING_ENABLE_LOG_FILE": "false", "AZURE_LOGGING_LOG_DIR": str(self.root / "az-logs"),
            "AZURE_EXTENSION_DIR": str(self.root / "extensions"),
            "AZURE_BICEP_USE_BINARY_FROM_PATH": "true", "PYTHONDONTWRITEBYTECODE": "1",
            "TEMP": str(self.root / "tmp"), "TMP": str(self.root / "tmp"),
            "DOTNET_CLI_HOME": str(self.root / "dotnet"),
            "BICEP_CACHE_ROOT_DIRECTORY": str(self.root / "bicep-cache"),
        })
        (self.root / "tmp").mkdir()
        compiler_dir = OWNED.parents[1] / "SPK-04-01" / "20260912T2130019672999Z-805407cd" / "azure-config" / "bin"
        toolchain = SOURCE / "toolchain.json"
        if toolchain.is_file():
            compiler_dir = (OWNED / load(toolchain)["binaryRelativeToLocal09Evidence"]).parent
        self.environment["PATH"] = str(compiler_dir) + os.pathsep + self.environment.get("PATH", "")
        self.receipt = {
            "schemaVersion": "1.0.0", "decisionId": "LOCAL-09", "purpose": purpose,
            "startedAt": now(), "status": "running", "commands": [],
            "azureMutationCommandsExecuted": 0, "actualResourceIds": [],
            "canonicalScenarioId": None, "canonicalScenarioHash": None,
            "finalDeploymentConfirmation": "pending", "baselineStatus": "not-observed",
            "credentialHandling": "Existing Azure CLI login consumed in place; no login, default subscription change or credential copying.",
            "mcpFallback": "Discovery reported No client was connected; official docs and pinned native Azure CLI fallback.",
        }
        defaults = Path.home() / ".azure" / "config"
        self.defaults_path = defaults
        self.defaults_hash = sha(defaults) if defaults.exists() else None

    def command(self, key, arguments, *, azure=True, timeout=120, required=True):
        if azure:
            argv = [str(a) for a in arguments]
            allowed = [
                ["version"], ["bicep", "version"], ["bicep", "build"], ["bicep", "list-versions"],
                ["account", "show"], ["provider", "show"], ["group", "exists"],
                ["storage", "account", "check-name"], ["policy", "assignment", "list"],
                ["policy", "exemption", "list"], ["rest", "--method", "get"],
                ["deployment", "sub", "validate"], ["deployment", "sub", "what-if"],
            ]
            require(any(argv[:len(prefix)] == prefix for prefix in allowed), "Read-only command allowlist rejected operation")
            require(not any(a in ["--debug", "--acquire-policy-token"] for a in argv), "Unexpected auth/debug option")
        return _transport.Run.command(self, key, arguments, azure=azure, timeout=timeout, required=required)

    def finish(self, status):
        self.receipt["status"] = status
        self.receipt["finishedAt"] = now()
        after = sha(self.defaults_path) if self.defaults_path.exists() else None
        self.receipt["globalAzureDefaultsUnchanged"] = after == self.defaults_hash
        require(after == self.defaults_hash, "Global Azure default configuration changed unexpectedly")
        self.save()

    def public_get(self, key, url):
        require(urllib.parse.urlparse(url).hostname in {"learn.microsoft.com", "azure.microsoft.com", "prices.azure.com"},
                "Unapproved public evidence host")
        entry = {"id": key, "method": "GET", "url": url, "requestedAt": now(), "evidenceOrigin": "live-external"}
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "LOCAL-09-readonly/1.0"}), timeout=45) as response:
                body = response.read(3_000_001)
                require(len(body) <= 3_000_000, "Public evidence response too large")
                entry.update({"status": "retrieved", "httpStatus": response.status, "retrievedAt": now()})
            suffix = ".json" if key.startswith("prices-") or key == "learn-search" else ".html"
            path = self.root / (key + suffix)
            path.write_bytes(body)
            entry.update({"file": path.name, "sha256": sha(path), "bytes": len(body)})
        except Exception as error:
            entry.update({"status": "unavailable", "error": f"{type(error).__name__}: {error}"})
        self.receipt.setdefault("publicSources", []).append(entry)
        self.save()
        return entry


DOCS = {
    "quickstart": "https://learn.microsoft.com/en-us/azure/private-link/create-network-security-perimeter-bicep?tabs=CLI",
    "storage-nsp": "https://learn.microsoft.com/en-us/azure/storage/common/storage-network-security-perimeter",
    "transition": "https://learn.microsoft.com/en-us/azure/private-link/network-security-perimeter-transition",
    "concepts": "https://learn.microsoft.com/en-us/azure/private-link/network-security-perimeter-concepts",
    "nsp-schema": "https://learn.microsoft.com/en-us/azure/templates/microsoft.network/2025-01-01/networksecurityperimeters",
    "profile-schema": "https://learn.microsoft.com/en-us/azure/templates/microsoft.network/2025-01-01/networksecurityperimeters/profiles",
    "association-schema": "https://learn.microsoft.com/en-us/azure/templates/microsoft.network/2025-01-01/networksecurityperimeters/resourceassociations",
    "storage-schema": "https://learn.microsoft.com/en-us/azure/templates/microsoft.storage/2025-06-01/storageaccounts",
    "storage-sync": "https://learn.microsoft.com/en-us/rest/api/storagerp/network-security-perimeter-configurations/get?view=rest-storagerp-2025-06-01",
    "naming": "https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-name-rules",
    "waf-storage": "https://learn.microsoft.com/en-us/azure/well-architected/service-guides/storage-accounts",
    "private-link-pricing": "https://azure.microsoft.com/en-us/pricing/details/private-link/",
    "nsp-pricing-attempt": "https://azure.microsoft.com/en-us/pricing/details/network-security-perimeter/",
}


def research():
    run = ReadOnlyRun("research")
    try:
        for key, url in DOCS.items():
            run.public_get(key, url)
        filters = {
            "perimeter": "contains(productName, 'Perimeter') and priceType eq 'Consumption'",
            "storage": "serviceName eq 'Storage' and armRegionName eq 'eastus2' and skuName eq 'Hot LRS' and priceType eq 'Consumption'",
        }
        for key, filter_value in filters.items():
            url = "https://prices.azure.com/api/retail/prices?" + urllib.parse.urlencode({
                "api-version": "2023-01-01-preview", "$filter": filter_value})
            run.public_get("prices-" + key, url)
        run.public_get("learn-search", "https://learn.microsoft.com/api/search?" + urllib.parse.urlencode({
            "search": '"network security perimeter" pricing', "locale": "en-us", "$top": 8}))
        run.command("cli-version", ["version", "--output", "json"])
        run.data("context", ["account", "show", "--query", "{id:id,tenantId:tenantId,state:state}"])
        for namespace in ["Microsoft.Network", "Microsoft.Storage"]:
            run.data(namespace + "-provider", ["provider", "show", "--namespace", namespace, "--query",
                "{namespace:namespace,registrationState:registrationState,resourceTypes:resourceTypes}"])
        run.rest("subscription-permissions", SUB_ID + "/providers/Microsoft.Authorization/permissions", "2022-04-01")
        run.data("rg-exists", ["group", "exists", "--name", GROUP])
        run.data("account-name", ["storage", "account", "check-name", "--name", ACCOUNT])
        run.finish("research-readonly-completed")
    except Exception as error:
        run.receipt["failure"] = run.redact(f"{type(error).__name__}: {error}")
        run.finish("research-incomplete")
    print(str((run.root / "receipt.json").relative_to(ROOT)))


if __name__ == "__main__":
    import argparse
    argparse.ArgumentParser(description=__doc__).parse_args()
    research()
