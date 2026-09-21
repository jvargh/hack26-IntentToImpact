"""Retrieve public Microsoft references only; no Azure authentication or mutations."""

from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request


WORKSPACE = Path(__file__).resolve().parents[3]
ROOT = WORKSPACE.parent if WORKSPACE.name == "intent-to-impact-studio" else WORKSPACE
OWNED = ROOT / ".intent-to-impact" / "spikes" / "SPK-03-01"
DOCUMENTS = {
    "secure-transfer": "https://learn.microsoft.com/en-us/azure/storage/common/storage-require-secure-transfer",
    "anonymous-blob-access": "https://learn.microsoft.com/en-us/azure/storage/blobs/anonymous-read-access-configure",
    "minimum-tls": "https://learn.microsoft.com/en-us/azure/storage/common/transport-layer-security-configure-minimum-version",
    "public-storage-network": "https://learn.microsoft.com/en-us/azure/storage/common/storage-network-security",
    "storage-properties": "https://learn.microsoft.com/en-us/rest/api/storagerp/storage-accounts/get-properties",
    "blob-pricing": "https://azure.microsoft.com/en-us/pricing/details/storage/blobs/",
}
FILTERS = {
    "blob": "serviceName eq 'Storage' and armRegionName eq 'eastus2' and skuName eq 'Hot LRS' and priceType eq 'Consumption'",
}


def utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", choices=list(DOCUMENTS) + ["prices-" + key for key in FILTERS])
    args = parser.parse_args()
    for parent in [ROOT / ".intent-to-impact", OWNED.parent, OWNED]:
        if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
            raise SystemExit("Refusing reparse evidence paths")
    run = OWNED / ("public-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run.mkdir(parents=True, exist_ok=False)
    evidence = {"schemaVersion": "1.0.0", "evidenceOrigin": "live-external", "readOnly": True,
                "azureOperations": [], "startedAt": utc(), "sources": []}
    requests = list(DOCUMENTS.items())
    for key, value in FILTERS.items():
        query = urllib.parse.urlencode({"api-version": "2023-01-01-preview", "$filter": value})
        requests.append(("prices-" + key, "https://prices.azure.com/api/retail/prices?" + query))
    for key, url in requests:
        if args.only and key not in args.only:
            continue
        entry = {"id": key, "url": url, "requestedAt": utc(), "method": "GET"}
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "SPK-03-01-proposal/1.0"})
            with urllib.request.urlopen(request, timeout=45) as response:
                body = response.read(3_000_001)
                if len(body) > 3_000_000:
                    raise ValueError("Public response exceeded bounded evidence size")
                entry.update({"httpStatus": response.status, "retrievedAt": utc(),
                              "finalUrl": response.url})
            suffix = ".json" if key.startswith("prices-") else ".html"
            target = run / (key + suffix)
            target.write_bytes(body)
            entry.update({"file": target.name, "sha256": hashlib.sha256(body).hexdigest(),
                          "bytes": len(body), "status": "retrieved"})
            if key.startswith("prices-"):
                result = json.loads(body)
                entry["itemCount"] = len(result.get("Items", []))
                entry["nextPageLink"] = result.get("NextPageLink")
                entry["paginationComplete"] = not bool(result.get("NextPageLink"))
                print(key, "items=", entry["itemCount"], "paginationComplete=", entry["paginationComplete"])
        except Exception as error:
            entry.update({"status": "unavailable", "error": f"{type(error).__name__}: {error}",
                          "finishedAt": utc()})
        evidence["sources"].append(entry)
        (run / "public-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    evidence["finishedAt"] = utc()
    (run / "public-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print("EVIDENCE_DIRECTORY", str(run.relative_to(ROOT)))


if __name__ == "__main__":
    main()
