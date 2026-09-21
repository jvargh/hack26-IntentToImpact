"""Serve loopback locally, or a single locked ACA worker behind tenant Easy Auth."""

import uvicorn
import json
from pathlib import Path

from .app import REPOSITORY_ROOT, create_app
from .hosting import load_hosted_config
from .hosted_lock import HostedWorkerLock


def load_history_scope():
    path = REPOSITORY_ROOT / ".intent-to-impact" / "studio" / "settings.json"
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "session"
    if not isinstance(settings, dict) or set(settings) != {"historyScope"} or settings["historyScope"] not in {"session", "workspace"}:
        raise ValueError("Invalid studio settings; history sharing was not enabled.")
    return settings["historyScope"]


def main():
    config = load_hosted_config()
    if config:
        with HostedWorkerLock(config) as worker_lock:
            uvicorn.run(create_app(hosted_config=config, hosted_lock=worker_lock),
                        host="0.0.0.0", port=8080, proxy_headers=False,
                        access_log=False, log_level="warning", limit_concurrency=32,
                        timeout_keep_alive=5)
        return
    uvicorn.run(create_app(history_scope=load_history_scope()), host="127.0.0.1", port=5173, proxy_headers=False,
                access_log=False, log_level="warning", limit_concurrency=32,
                timeout_keep_alive=5)


if __name__ == "__main__":
    main()
