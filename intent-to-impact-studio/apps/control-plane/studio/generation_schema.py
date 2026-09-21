"""Provider-compatible structured output derived from the canonical contract."""

import copy

from .validation import SCHEMA, StudioFailure, source_ids

_KEYWORDS = {"type", "properties", "required", "additionalProperties", "items",
             "anyOf", "enum", "$ref", "description", "title"}


def response_format(name, request):
    if name not in {"ArchitectureAnalysis", "AssuranceReview"}:
        raise StudioFailure("invalid_output_contract", "Unsupported model output contract.", 500)
    allowed_sources = sorted(source_ids(request))
    definitions = {}

    def convert(value):
        if isinstance(value, list):
            return [convert(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {}
        for key, item in value.items():
            if key == "$ref":
                prefix = "#/definitions/"
                if not item.startswith(prefix):
                    raise StudioFailure("invalid_output_contract", "Model schemas must use local contract references.", 500)
                target = item[len(prefix):]
                if target not in definitions:
                    definitions[target] = {}
                    definitions[target] = convert(copy.deepcopy(SCHEMA["definitions"][target]))
                result[key] = item.replace(prefix, "#/$defs/", 1)
            elif key == "properties":
                result[key] = {prop: convert(definition) for prop, definition in item.items()}
                for prop, definition in result[key].items():
                    if prop == "sourceIds":
                        definition["items"] = {"type": "string", "enum": allowed_sources}
                    elif prop == "sourceId":
                        definition["enum"] = allowed_sources
            elif key in _KEYWORDS:
                result[key] = convert(item)
            elif key == "const":
                result["enum"] = [item]
        if result.get("type") == "object":
            result["required"] = list(result.get("properties", {}))
            result["additionalProperties"] = False
        return result

    model_schema = convert(copy.deepcopy(SCHEMA["definitions"][name]))
    if definitions:
        model_schema["$defs"] = definitions
    return {"type": "json_schema", "json_schema": {
        "name": name, "strict": True, "schema": model_schema,
    }}


def responses_text_format(format_value):
    """Expected wire shape after the installed Agent Framework adapter conversion."""
    return {"type": "json_schema", **format_value["json_schema"]}
