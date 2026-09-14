"""Start the bounded API on IPv4 loopback only; access token never logged."""

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "control-plane"))

from api.app import Config, EFFECTS, create_app
import uvicorn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-root", type=Path, default=EFFECTS / "runs")
    parser.add_argument("--run-mode", choices=["live", "fixture"], default="live")
    parser.add_argument("--purpose", choices=["test", "hero", "magic-moment-proof", "rehearsal", "ux-mock"], default="test")
    args = parser.parse_args()
    try:
        config = Config(
            access_token=os.environ.get("INTENT_API_ACCESS_TOKEN", ""),
            data_root=args.data_root, origin=f"http://127.0.0.1:{args.port}",
            run_mode=args.run_mode, purpose=args.purpose,
        )
    except ValueError:
        parser.error("Use a valid loopback port/task-owned root/mode and set INTENT_API_ACCESS_TOKEN to a 32-256 character ASCII token.")
    uvicorn.run(create_app(config), host="127.0.0.1", port=args.port,
                proxy_headers=False, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
