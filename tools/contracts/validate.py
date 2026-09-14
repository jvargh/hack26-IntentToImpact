"""Authoritative base shape validation and old/new immutable run-context comparison."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.contracts.registry_support import registries

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "contracts" / "schemas" / "1.0.0" / "core.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
Draft202012Validator.check_schema(SCHEMA)
CONTRACT_NAMES = {
    definition["x-contract-id"]: name
    for name, definition in SCHEMA["definitions"].items()
    if "x-contract-id" in definition
}
CONTRACTS = SCHEMA_PATH.parents[2]
VERSION_REGISTRIES = registries()
REGISTRY_MANIFEST = VERSION_REGISTRIES["1.0.0"]
VERSION_BUNDLES = {
    version: {
        item["name"]: json.loads((CONTRACTS / item["schema"]).read_text(encoding="utf-8"))
        for item in manifest["bundles"]
    }
    for version, manifest in VERSION_REGISTRIES.items()
}
BUNDLES = VERSION_BUNDLES["1.0.0"]
VERSION_CONTRACTS = {
    version: {
        contract_id: (item["name"], name)
        for item in manifest["bundles"] for contract_id, name in item["contracts"].items()
    }
    for version, manifest in VERSION_REGISTRIES.items()
}
REGISTERED_CONTRACTS = VERSION_CONTRACTS["1.0.0"]
_resources = []
for _version, _manifest in VERSION_REGISTRIES.items():
    for _item in _manifest["bundles"]:
        _schema = VERSION_BUNDLES[_version][_item["name"]]
        Draft202012Validator.check_schema(_schema)
        _resource = Resource.from_contents(_schema)
        _resources.extend([
            (_schema["$id"], _resource),
            (f"https://intent-to-impact.invalid/contracts/{_version}/" + Path(_item["schema"]).name, _resource),
        ])
SCHEMA_REGISTRY = Registry().with_resources(_resources)


def _selected(version):
    if version not in VERSION_CONTRACTS:
        raise ValueError(f"Unsupported or unpublished schema version: {version}")
    return VERSION_CONTRACTS[version]


def validator(contract_id: str | None = None, *, schema_version="1.0.0") -> Draft202012Validator:
    selected = _selected(schema_version)
    if schema_version != "1.0.0":
        if contract_id not in selected:
            raise ValueError(f"Contract {contract_id} is not published at schema version {schema_version}")
        bundle, name = selected[contract_id]
        return fragment_validator(bundle, name, schema_version=schema_version)
    if contract_id is not None and contract_id not in CONTRACT_NAMES:
        bundle, name = REGISTERED_CONTRACTS[contract_id]
        return fragment_validator(bundle, name)
    if contract_id is None:
        schema = SCHEMA
    else:
        name = CONTRACT_NAMES[contract_id]
        schema = {
            "$schema": SCHEMA["$schema"],
            "$ref": f"#/definitions/{name}",
            "definitions": SCHEMA["definitions"],
        }
    return Draft202012Validator(schema, format_checker=FormatChecker())


def fragment_validator(bundle: str, name: str, *, schema_version="1.0.0") -> Draft202012Validator:
    """Resolve only the explicitly registered local schemas; no network retrieval."""
    _selected(schema_version)
    return Draft202012Validator(
        {"$ref": VERSION_BUNDLES[schema_version][bundle]["$id"] + f"#/definitions/{name}"},
        registry=SCHEMA_REGISTRY, format_checker=FormatChecker(),
    )


def identify_contract(value: dict[str, Any], *, schema_version="1.0.0") -> str:
    selected = _selected(schema_version)
    if value.get("schemaVersion") != schema_version:
        raise ValueError("Payload schemaVersion does not match explicit selection")
    for contract_id, (bundle, name) in selected.items():
        properties = VERSION_BUNDLES[schema_version][bundle]["definitions"][name].get("properties", {})
        if properties.get("artifactType", {}).get("const") == value.get("artifactType"):
            return contract_id
    raise ValueError(f"Unregistered artifactType: {value.get('artifactType')}")


def validate_contract(value: Any, contract_id: str | None = None, *, schema_version="1.0.0") -> None:
    """Raise jsonschema.ValidationError for invalid JSON shape (including formats)."""
    validator(contract_id, schema_version=schema_version).validate(value)


def assert_run_context_unchanged(old: dict[str, Any], new: dict[str, Any]) -> None:
    """Compare validated D22 contexts; JSON Schema alone cannot detect a mutation."""
    validate_contract(old, "D22")
    validate_contract(new, "D22")
    properties = {
        **SCHEMA["definitions"]["CommonEnvelope"]["properties"],
        **SCHEMA["definitions"]["LocalRunManifest"]["properties"],
    }
    missing = object()
    changed = [
        field
        for field, definition in properties.items()
        if definition.get("x-immutable") and old.get(field, missing) != new.get(field, missing)
    ]
    if changed:
        raise ValueError("Immutable run context changed: " + ", ".join(sorted(changed)))
