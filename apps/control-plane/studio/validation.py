"""Canonical JSON Schema validation plus graph/source invariants."""

import hashlib
import copy
import json
import re
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker

SCHEMA = json.loads(Path(__file__).with_name("studio.schema.json").read_text(encoding="utf-8"))
DIMENSIONS = {
    "business", "security", "reliability", "performance", "cost",
    "integration", "compliance", "operations", "delivery",
}
SERVICES = {
    "appservice": "AppService", "functions": "Functions", "storage": "Storage",
    "servicebus": "ServiceBus", "keyvault": "KeyVault", "client": "Client",
}
TOKEN = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")
SOURCE_TOKEN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
SECRET = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    r"|\b(?:AccountKey|SharedAccessKey|client_secret)\s*[=:]\s*[A-Za-z0-9+/=_-]{16,}"
    r"|\b(?:password|api[_-]?key|access[_-]?token)\s*[=:]\s*[A-Za-z0-9+/=_-]{16,}"
    r"|\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})"
    r"|\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    r"|[?&]sig=[A-Za-z0-9%+/=_-]{20,}",
    re.IGNORECASE,
)


class StudioFailure(Exception):
    def __init__(self, code, message, status=422, retryable=False):
        super().__init__(message)
        self.code, self.message, self.status, self.retryable = code, message, status, retryable

    def public(self):
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


def digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode()).hexdigest()


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(_):
        raise ValueError("Non-finite JSON number")

    try:
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise StudioFailure("invalid_json", "Expected UTF-8 JSON without duplicate keys or non-finite values.", 400) from None


def schema_for(name):
    return {**SCHEMA["definitions"][name], "definitions": SCHEMA["definitions"]}


def validate(name, value):
    error = next(Draft7Validator(schema_for(name), format_checker=FormatChecker()).iter_errors(value), None)
    if error:
        # Validation error text can include untrusted document contents.
        raise StudioFailure("invalid_schema", f"{name} does not match the studio contract.") from None


def safe_token(value):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise StudioFailure("invalid_id", "Identifier must be an exact token, not a path.", 400)
    return value


def unique(values, label):
    if len(values) != len(set(values)):
        raise StudioFailure("invalid_references", f"Duplicate {label} identifiers.")


def no_secrets(value):
    if SECRET.search(json.dumps(value, ensure_ascii=False)):
        raise StudioFailure("sensitive_content", "Credential-like content is not accepted or returned.", 422)


def validate_request(value):
    validate("AnalysisRequest", value)
    if not value["prompt"].strip() or len(value["prompt"].strip()) < 10:
        raise StudioFailure("empty_input", "Describe the business process using at least 10 non-padding characters.")
    documents = value["documents"]
    unique([doc["id"] for doc in documents], "source")
    if any(not doc["text"].strip() or not doc["name"].strip() for doc in documents):
        raise StudioFailure("empty_input", "Document names and text cannot be empty.")
    if any(doc["id"] in {"prompt", "refinement"} or not SOURCE_TOKEN.fullmatch(doc["id"]) for doc in documents):
        raise StudioFailure("invalid_source", "Document IDs must be safe tokens and cannot use the reserved prompt or refinement IDs.")
    if sum(len(doc["text"]) for doc in documents) > 150000:
        raise StudioFailure("input_too_large", "Documents exceed the total 150,000-character limit.", 413)
    if value["previousResultId"] is not None:
        safe_token(value["previousResultId"])
        if not value["refinement"].strip():
            raise StudioFailure("empty_refinement", "A revision requires a non-empty refinement.")
    elif value["refinement"].strip():
        raise StudioFailure("missing_previous_result", "A refinement requires an owned previous result.")
    no_secrets(value)


def source_ids(request):
    sources = {"prompt", *(doc["id"] for doc in request["documents"])}
    if request["refinement"].strip():
        sources.add("refinement")
    return sources


def _normalized(text):
    return " ".join(text.split()).casefold()


def _existing_clause(name, text):
    named = rf"(?<!\w){re.escape(_normalized(name))}(?!\w)"
    for raw in re.split(r"[.!?;\n]+", text):
        clause = _normalized(raw)
        match = re.search(named, clause)
        if not match:
            continue
        context = clause[:match.start()] + " " + clause[match.end():]
        if re.search(r"\b(?:no existing|not (?:an? )?existing|do not have|don't have|not yet|proposed|planned|consider|new)\b", context):
            continue
        if re.search(
            rf"\b(?:existing|user-owned|already (?:use|using|have)|currently (?:use|using)|keep|retain)\b.{{0,160}}{named}"
            rf"|{named}.{{0,160}}\b(?:existing|user-owned|already|will remain|in use)\b",
            clause,
        ):
            return raw.strip()
    return None


def _source_texts(request):
    texts = {"prompt": request["prompt"], **{doc["id"]: doc["text"] for doc in request["documents"]}}
    if request["refinement"].strip():
        texts["refinement"] = request["refinement"]
    return texts


def ground_external_dependencies(analysis, request):
    """Bind declared names/IDs to literal source excerpts, never model-authored quotations."""
    validate("ArchitectureAnalysis", analysis)
    grounded = copy.deepcopy(analysis)
    texts = _source_texts(request)
    for option in grounded["options"]:
        for node in option["components"]:
            if node["kind"] != "external":
                continue
            binding = node.get("externalDependency")
            if node["service"] != "External HTTPS API" or not isinstance(binding, dict):
                raise StudioFailure("unsupported_dependency", f"External component {node['id']} needs its exact source name and source ID.")
            source = texts.get(binding["sourceId"])
            excerpt = _existing_clause(binding["name"], source) if source is not None else None
            if not excerpt or len(excerpt) > 2000:
                raise StudioFailure("unsupported_dependency", f"External component {node['id']} has no affirmative existing-integration declaration in the named source.")
            binding["quote"] = excerpt
    return grounded


def validate_external_dependency(node, request):
    binding = node.get("externalDependency")
    if node["service"] != "External HTTPS API" or not isinstance(binding, dict):
        raise StudioFailure("unsupported_dependency",
                            f"External component {node['id']} needs a named existing integration and a literal source citation.")
    texts = _source_texts(request)
    source = texts.get(binding["sourceId"])
    quote = _normalized(binding["quote"])
    if source is None or quote not in _normalized(source):
        raise StudioFailure("invalid_external_source", f"External component {node['id']} cites text that is not in its source.")
    if _existing_clause(binding["name"], binding["quote"]):
        return
    raise StudioFailure("unsupported_dependency",
                        f"External component {node['id']} is not affirmatively identified as existing in its cited source. Clarify that dependency rather than inventing it.")


def validate_review(review, sources):
    if {item["dimension"] for item in review} != DIMENSIONS or len(review) != 9:
        raise StudioFailure("invalid_dimensions", "Every assurance dimension must appear exactly once.")
    for item in review:
        if not set(item["sourceIds"]) <= sources:
            raise StudioFailure("invalid_references", "Review references an unknown source.")


def validate_analysis(analysis, request):
    validate("ArchitectureAnalysis", analysis)
    no_secrets(analysis)
    sources = source_ids(request)
    requirements = analysis["requirements"]
    req_ids = {req["id"] for req in requirements}
    unique([req["id"] for req in requirements], "requirement")
    unique([item["id"] for item in analysis["questions"]], "question")
    for req in requirements:
        if not set(req["sourceIds"]) <= sources:
            raise StudioFailure("invalid_references", "Requirement references an unknown source.")
    options = analysis["options"]
    unique([option["id"] for option in options], "option")
    if analysis["recommendedOptionId"] not in {option["id"] for option in options}:
        raise StudioFailure("invalid_references", "Recommended option does not exist.")
    all_nodes, all_edges = [], []
    for option in options:
        node_ids = {node["id"] for node in option["components"]}
        all_nodes.extend(node["id"] for node in option["components"])
        all_edges.extend(edge["id"] for edge in option["connections"])
        for node in option["components"]:
            if not set(node["requirementIds"]) <= req_ids:
                raise StudioFailure("invalid_references", "Component references an unknown requirement.")
            if node["kind"] in SERVICES and node["service"] != SERVICES[node["kind"]]:
                raise StudioFailure("invalid_service", "Component service does not match its supported kind.")
            if node["kind"] == "external":
                validate_external_dependency(node, request)
            elif node.get("externalDependency") is not None:
                raise StudioFailure("invalid_external_source", "Only external components may carry an existing-integration citation.")
        for edge in option["connections"]:
            if edge["source"] not in node_ids or edge["target"] not in node_ids:
                raise StudioFailure("invalid_references", "Connection endpoint does not exist in its option.")
    unique(all_nodes, "component")
    unique(all_edges, "connection")
    validate_review(analysis["review"], sources)
