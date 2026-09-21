"""Read-only, exact-scope SPK-01-01 metadata discovery. No credential bodies."""

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SUBSCRIPTION = "463a82d4-1896-4332-aeeb-618ee5a5aa93"
TENANT = "5bb5fa45-2dcc-4310-bbc5-883021e9d84b"
RESOURCE_GROUP = "az-foundry-rg"
ACCOUNT = "jv-eastus2-proj-resource"
PROJECT = "jv-eastus2-proj"
ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / ".intent-to-impact" / "spikes" / "SPK-01-01"
ACCOUNT_ID = (
    f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{RESOURCE_GROUP}"
    f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT}"
)
PROJECT_ID = f"{ACCOUNT_ID}/projects/{PROJECT}"


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def save(name, value):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return str(path.relative_to(ROOT))


def cli(args):
    command = ["az", *args, "--subscription", SUBSCRIPTION, "--only-show-errors", "-o", "json"]
    start = now()
    result = subprocess.run(
        [shutil.which("az") or "az", *command[1:]],
        capture_output=True, text=True, timeout=90, check=False,
    )
    row = {
        "origin": "live-external", "command": command, "startedAt": start,
        "completedAt": now(), "exitCode": result.returncode,
    }
    if result.returncode:
        row["status"] = "blocked"
        row["diagnostic"] = "Scoped Azure CLI metadata read failed; no raw stderr retained."
    else:
        row.update(status="passed", data=json.loads(result.stdout))
        row["dataSha256"] = digest(row["data"])
    return row


def main():
    rows = {}
    rows["scope"] = cli([
        "account", "show", "--query", "{id:id,tenantId:tenantId,state:state}",
    ])
    expected = {"id": SUBSCRIPTION, "tenantId": TENANT, "state": "Enabled"}
    if rows["scope"].get("data") != expected:
        save("discovery.json", {"version": "1.0.0", "status": "blocked", "rows": rows})
        raise SystemExit("Scope mismatch: use the approved subscription/tenant; no discovery performed.")
    rows["resources"] = cli([
        "resource", "list", "--resource-group", RESOURCE_GROUP,
        "--query", "[].{id:id,name:name,type:type,kind:kind,location:location}",
    ])
    prefix = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{RESOURCE_GROUP}/"
    if any(not item["id"].lower().startswith(prefix.lower())
           for item in rows["resources"].get("data", [])):
        raise SystemExit("Resource scope mismatch: discovery stopped.")
    rows["account"] = cli([
        "cognitiveservices", "account", "show", "-g", RESOURCE_GROUP, "-n", ACCOUNT,
        "--query", "{id:id,name:name,kind:kind,location:location,"
        "endpoint:properties.endpoint,publicNetworkAccess:properties.publicNetworkAccess,"
        "networkDefaultAction:properties.networkAcls.defaultAction,"
        "ipRuleCount:length(properties.networkAcls.ipRules || `[]`),"
        "vnetRuleCount:length(properties.networkAcls.virtualNetworkRules || `[]`)}",
    ])
    rows["project"] = cli([
        "resource", "show", "--ids", PROJECT_ID, "--api-version", "2025-06-01",
        "--query", "{id:id,name:name,location:location,endpoints:properties.endpoints}",
    ])
    rows["deployments"] = cli([
        "cognitiveservices", "account", "deployment", "list",
        "-g", RESOURCE_GROUP, "-n", ACCOUNT,
        "--query", "[].{id:id,name:name,model:properties.model,state:properties.provisioningState}",
    ])
    receipt = {"version": "1.0.0", "task": "SPK-01-01", "createdAt": now(),
               "status": "passed" if all(row["status"] == "passed" for row in rows.values())
               else "partial", "rows": rows, "azureMutationCount": 0}
    path = save("discovery.json", receipt)
    print(json.dumps({"status": receipt["status"], "path": path,
                      "rows": {key: row["status"] for key, row in rows.items()}}))


if __name__ == "__main__":
    main()
