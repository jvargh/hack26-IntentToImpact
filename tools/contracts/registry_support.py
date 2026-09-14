"""Bounded explicit registry selection; legacy 1.0.0 remains the default."""

import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts"


def registries():
    index = json.loads((CONTRACTS / "registry" / "index.json").read_text(encoding="utf-8"))
    if index["defaultSchemaVersion"] != "1.0.0":
        raise ValueError("The accepted legacy schema default must remain 1.0.0")
    result = {}
    for version, filename in index["versions"].items():
        if version not in {"1.0.0", "2.0.0"} or filename != f"{version}.json":
            raise ValueError("Unsupported schema registry selection")
        value = json.loads((CONTRACTS / "registry" / filename).read_text(encoding="utf-8"))
        if value["schemaVersion"] != version:
            raise ValueError("Registry/schema version mismatch")
        result[version] = value
    return result


def select_registry(version="1.0.0"):
    available = registries()
    if version not in available:
        raise ValueError(f"Unsupported or unpublished schema version: {version}")
    return available[version]


def verify_historical_artifacts(registry):
    name = registry.get("historicalArtifactLock")
    if name is None:
        return
    if name != "registry/2.0.0.history.json":
        raise ValueError("Unexpected historical artifact lock")
    value = json.loads((CONTRACTS / name).read_text(encoding="utf-8"))
    for path, expected in value["files"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Historical artifact changed: {path}")


def verify_local_schema_references(schema: Path):
    """Check local reference paths only; never rewrite or compile a schema."""
    root = (CONTRACTS / "schemas").resolve()
    allowed = {
        (CONTRACTS / bundle["schema"]).resolve()
        for registry in registries().values() for bundle in registry["bundles"]
    }
    seen = set()

    def visit(path):
        path = path.resolve()
        if path not in allowed or not path.is_relative_to(root):
            raise ValueError(f"Unregistered schema reference: {path}")
        if path in seen:
            return
        seen.add(path)

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {"$ref", "$dynamicRef", "$recursiveRef"}:
                        if key != "$ref" or not isinstance(item, str):
                            raise ValueError("Only explicit local $ref values are supported")
                        url = urlsplit(item)
                        if url.scheme or url.netloc or url.query or "\\" in url.path or url.path.startswith("/"):
                            raise ValueError("Network/absolute schema references are prohibited")
                        if url.path:
                            visit(path.parent / url.path)
                    else:
                        walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(json.loads(path.read_text(encoding="utf-8")))

    visit(schema)
