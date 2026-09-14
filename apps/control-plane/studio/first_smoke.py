"""Synthetic, bounded live check using the previously verified Foundry spike."""

import asyncio
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root / "tests" / "spikes" / "foundry"))
    import discover
    import spike

    output = root / ".intent-to-impact" / "spikes" / "STUDIO-LIVE-API"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    discover.OUTPUT = output / stamp
    try:
        account = subprocess.run(
            [shutil.which("az") or "az", "account", "show", "--query",
             "{id:id,tenantId:tenantId,state:state}", "-o", "json", "--only-show-errors"],
            capture_output=True, text=True, timeout=20, check=True,
        )
        scope = json.loads(account.stdout)
        if scope != {"id": discover.SUBSCRIPTION, "tenantId": discover.TENANT, "state": "Enabled"}:
            raise ValueError("Current Azure CLI identity is outside the approved scope.")
        discovery = {"rows": {"scope": {"data": scope}, "deployments": {
            "data": [{"name": "gpt-5.2", "note": "Existing deployment; not mutated."}]
        }}}
        return asyncio.run(asyncio.wait_for(
            spike.execute("model", spike.EXPECTED, discovery), timeout=90
        ))
    except Exception as exc:
        path = discover.save("model-receipt.json", {
            "origin": "live-local", "status": "blocked", "errorType": type(exc).__name__,
            "message": "Approved-scope preflight or bounded live request failed; no retry.",
        })
        print(json.dumps({"status": "blocked", "path": path}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
