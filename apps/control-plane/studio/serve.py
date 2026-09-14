"""Run the production frontend and API together on the approved loopback origin."""

import uvicorn
import json
from pathlib import Path

from .app import create_app


def load_history_scope():
    path = Path(__file__).resolve().parents[3] / ".intent-to-impact" / "studio" / "settings.json"
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "session"
    if not isinstance(settings, dict) or set(settings) != {"historyScope"} or settings["historyScope"] not in {"session", "workspace"}:
        raise ValueError("Invalid studio settings; history sharing was not enabled.")
    return settings["historyScope"]


def main():
    uvicorn.run(create_app(history_scope=load_history_scope()), host="127.0.0.1", port=5173, proxy_headers=False,
                access_log=False, log_level="warning", limit_concurrency=32,
                timeout_keep_alive=5)


if __name__ == "__main__":
    main()
