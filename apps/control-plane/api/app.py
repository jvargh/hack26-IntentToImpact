"""Minimum authenticated-demo loopback API; no provider or worker execution."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import re
import secrets
import time
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from starlette.exceptions import HTTPException

from policy import Policy, PolicyConfigurationError
from state.case_store import CaseStore, StoreError, seal
from tools.contracts.integrity import (
    ReferenceIntegrityError, scenario_identity, semantic_checksum, validate_scenario,
)
from tools.contracts.validate import SCHEMA_REGISTRY, fragment_validator, validate_contract
from .projection import initial_overview, issue_context_action

ROOT = Path(__file__).resolve().parents[3]
EFFECTS = ROOT / ".intent-to-impact" / "spikes" / "INT-01-01"
SCENARIO_PATH = ROOT / "fixtures" / "scenarios" / "DEMO-CASE-CLAIMS-V2.json"
POLICY_REGISTRY = Path(__file__).parents[1] / "policy" / "capabilities.v1.json"
TRANSPORT = json.loads(Path(__file__).with_name("transport.schema.json").read_text(encoding="utf-8"))
IDENTITY = {"actorId": "demo-human", "identityAssurance": "local-demo",
            "disclosure": "Local demo approver - identity not independently verified"}
SCOPE = {"scopeId": "SCOPE-LOCAL-API", "subscriptionId": None, "resourceGroup": None, "resourceIds": []}


class ApiFault(Exception):
    def __init__(self, status, code, message, run=None):
        self.status, self.code, self.message, self.run = status, code, message, run


@dataclass(frozen=True)
class Config:
    access_token: str = field(repr=False)
    data_root: Path = EFFECTS / "runs"
    origin: str = "http://127.0.0.1:8765"
    run_mode: str = "live"
    purpose: str = "test"

    def __post_init__(self):
        parsed = urlsplit(self.origin)
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port
                or parsed.netloc != f"127.0.0.1:{parsed.port}" or parsed.path or parsed.query or parsed.fragment):
            raise ValueError("Only an exact http://127.0.0.1:<port> origin is supported.")
        if type(self.access_token) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", self.access_token):
            raise ValueError("Supply a 32-256 character process-local ASCII access token.")
        if not self.data_root.resolve().is_relative_to(EFFECTS.resolve()):
            raise ValueError("API storage must remain inside the INT-01-01 evidence root.")
        fragment_validator("core", "RunMode").validate(self.run_mode)
        fragment_validator("core", "RunPurpose").validate(self.purpose)
        if self.run_mode == "replay" or (self.purpose == "ux-mock" and self.run_mode != "fixture"):
            raise ValueError("Replay creation is unavailable; ux-mock requires fixture mode.")


def now():
    return datetime.now(timezone.utc).isoformat()


def transport_validate(value, definition):
    Draft202012Validator(
        {"$ref": f"#/definitions/{definition}", "definitions": TRANSPORT["definitions"]},
        registry=SCHEMA_REGISTRY, format_checker=FormatChecker(),
    ).validate(value)


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate-json-key")
        value[key] = item
    return value


async def body(request, definition):
    if request.headers.get("content-type", "").split(";")[0] != "application/json":
        raise ApiFault(415, "invalid-artifact", "Use application/json for the documented request body.")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 16384:
            raise ApiFault(413, "invalid-artifact", "Request exceeds the 16 KiB transport limit.")
    try:
        value = json.loads(data, object_pairs_hook=unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite-json")))
        transport_validate(value, definition)
        return value
    except (UnicodeError, ValueError, ValidationError, RecursionError) as exc:
        raise ApiFault(400, "invalid-artifact",
                       "Request must match the documented transport schema; caller, mode, scope and paths are server-owned.") from exc


class Service:
    def __init__(self, config):
        self.config = config
        self.store = CaseStore(config.data_root)
        self.scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        validate_scenario(self.scenario)
        self.identity = scenario_identity(self.scenario)

    @staticmethod
    def capability_available(capability):
        try:
            registry = json.loads(POLICY_REGISTRY.read_text(encoding="utf-8"))
            return registry["capabilities"].get(capability) == {
                "profile": "human", "activityClass": "product-workflow",
            }
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ApiFault(503, "invalid-artifact", "The trusted policy registry is unavailable or malformed.") from exc

    def policy(self, run, capability=None):
        grants = ["read-case"]
        if capability:
            if not self.capability_available(capability):
                raise ApiFault(503, "not-authorized",
                               f"Policy capability {capability} requires an owner-approved registry entry.", run)
            grants.append(capability)
        policy = Policy(run, scope=SCOPE, root_id="ROOT-LOOPBACK-API", config_id="CONFIG-LOOPBACK-API",
                        enabled_capabilities=grants)
        entry = policy.human_entry("browser", capabilities=grants)
        return policy, entry

    def authorize(self, run, case, capability, action_id):
        policy, entry = self.policy(run, capability)
        checksums = {"run-context": run["stateChecksum"], "scenario": self.identity["scenarioHash"]}
        revision = case["logicalRevision"]
        facts = policy.engine_facts(
            current_revision=revision, capability=capability, action_id=action_id,
            subject_id=run["caseId"], checksums=checksums,
            gate_id="known-run-context-ready", gate_passed=True,
        )
        result = policy.authorize(entry, {
            "capability": capability, "actionId": action_id, "subjectId": run["caseId"],
            "expectedRevision": revision, "boundChecksums": checksums,
        }, current_run=run, facts=facts)
        if not result.allowed:
            raise ApiFault(403, result.error["code"], result.error["message"], run)
        return result.authorization_context

    def load(self, case_id):
        match = re.fullmatch(r"CASE-([0-9a-f]{32})", case_id)
        if not match:
            raise ApiFault(404, "invalid-artifact", "Unknown API case ID.")
        run_id = "RUN-" + match.group(1)
        try:
            run = self.store.read_run(run_id)
        except FileNotFoundError as exc:
            raise ApiFault(404, "invalid-artifact", "Case was not found in this configured local root.") from exc
        try:
            case = self.store.read_case(run_id)
        except FileNotFoundError as exc:
            raise ApiFault(503, "recovery-required", "Run creation is incomplete; no automatic repair was performed.", run) from exc
        if (run["caseId"] != case_id or run["scope"] != SCOPE or run["rootId"] != "ROOT-LOOPBACK-API"
                or run["configId"] != "CONFIG-LOOPBACK-API"
                or run["runMode"] != self.config.run_mode or run["purpose"] != self.config.purpose
                or {k: run[k] for k in self.identity} != self.identity):
            raise ApiFault(409, "not-authorized", "Stored run differs from the immutable server configuration.", run)
        if run["artifactId"] == f"ART-RUN-{match.group(1)}" and "api-create" not in case["sections"]:
            raise ApiFault(503, "recovery-required", "API case creation has no committed receipt; no success was inferred.", run)
        if set(case["sections"]) - {"api-create", "api-context-ack"}:
            raise ApiFault(409, "invalid-artifact",
                           "This minimal API cannot project additional producer sections; it will not replace them with unknown defaults.", run)
        policy, entry = self.policy(run)
        allowed = policy.authorize(entry, {"capability": "read-case"}, current_run=run)
        if not allowed.allowed:
            raise ApiFault(403, allowed.error["code"], allowed.error["message"], run)
        for reference in case["sections"].values():
            self.store.read_artifact(run_id, reference)
        if "api-context-ack" in case["sections"]:
            reference = case["sections"]["api-context-ack"]
            metadata = self.store.read_artifact(run_id, reference)
            expected = {
                "artifactType": "local-context-acknowledgement", "scenario": self.identity,
                "runManifestChecksum": run["stateChecksum"], "acknowledgement": "known-scenario-context-only",
                "promisesConfirmed": False, "architectureApproved": False, "runtimeVerified": False,
            }
            matches = [event for event in case["events"] if event["eventType"] == "run-context-acknowledged"
                       and reference in event["payloadRefs"]]
            if (any(metadata.get(k) != v for k, v in expected.items()) or len(matches) != 1
                    or matches[0]["actor"] != {"kind": "human", "actorId": "demo-human", "identityAssurance": "local-demo"}):
                raise ApiFault(409, "invalid-artifact", "Context acknowledgement metadata/event linkage is invalid.", run)
        return run, case

    def receipt_event(self, run, case, record, event_type, capability):
        event = self.store.read_artifact(run["runId"], record["result"])
        validate_contract(event, "E04")
        if record["commandId"] != capability or event["eventType"] != event_type or event not in case["events"]:
            raise ApiFault(409, "invalid-artifact", "Stored idempotency receipt does not match its canonical event.", run)
        return event

    @staticmethod
    def envelope(run, artifact_type, revision):
        at = now()
        return {
            "schemaVersion": "1.0.0", "artifactType": artifact_type, "artifactId": f"ART-{uuid4().hex}",
            "runId": run["runId"], "caseId": run["caseId"], "scope": deepcopy(run["scope"]),
            "caseRevisionAtWrite": revision, "createdAt": at, "updatedAt": at,
            "derivedFrom": {"runManifest": run["stateChecksum"]},
        }

    def event(self, run, case, event_type, auth, metadata_ref):
        auth_ref = self.store.put_artifact(run["runId"], auth)
        event = seal({
            **self.envelope(run, "domain-event", case["logicalRevision"] + 1),
            "eventId": f"EVENT-{uuid4().hex}", "sequence": len(case["events"]) + 1,
            "eventType": event_type, "correlationId": auth["correlationId"], "workId": None,
            "actor": auth["caller"]["actor"], "payloadRefs": [metadata_ref, auth_ref],
        })
        validate_contract(event, "E04")
        reference = self.store.put_artifact(run["runId"], event)
        return event, reference

    def create(self, data):
        self.policy_candidate_capability("create-case")
        suffix = semantic_checksum({"idempotencyKey": data["idempotencyKey"], "namespace": "INT-01-01"})[7:39]
        run_id, case_id = "RUN-" + suffix, "CASE-" + suffix
        checksum = semantic_checksum({k: v for k, v in data.items() if k != "idempotencyKey"})
        try:
            existing = self.store.read_run(run_id)
        except FileNotFoundError:
            existing = None
        if existing is not None:
            run, case = self.load(case_id)
            if "api-create" not in case["sections"]:
                raise ApiFault(503, "recovery-required", "Create receipt is missing; no automatic replay was performed.", run)
            metadata = self.store.read_artifact(run_id, case["sections"]["api-create"])
            if metadata.get("requestChecksum") != checksum:
                raise ApiFault(409, "idempotency-conflict", "Create idempotency key was already used with different input.", run)
            record = next((r for r in case["idempotencyRecords"] if r["idempotencyKey"] == "api-create"), None)
            if record is None:
                raise ApiFault(503, "recovery-required", "Create idempotency receipt is incomplete.", run)
            return self.receipt_event(run, case, record, "case-created", "create-case"), True
        if data["scenario"] != self.identity:
            raise ApiFault(400, "invalid-artifact", "Select the exact accepted V2 scenario ID, version and content hash.")
        at = now()
        run = seal({
            "schemaVersion": "1.0.0", "artifactType": "local-run-manifest",
            "artifactId": f"ART-RUN-{suffix}", "runId": run_id, "caseId": case_id, "scope": deepcopy(SCOPE),
            "caseRevisionAtWrite": 0, "createdAt": at, "updatedAt": at, "derivedFrom": {},
            "runMode": self.config.run_mode, "purpose": self.config.purpose, **self.identity,
            "rootId": "ROOT-LOOPBACK-API", "configId": "CONFIG-LOOPBACK-API",
        })
        validate_contract(run, "D22")
        auth = self.authorize(run, {"logicalRevision": 0}, "create-case", "create-known-scenario-case")
        run = self.store.create_run(run)
        case = self.store.create_case(run_id)
        metadata_ref = self.store.put_artifact(run_id, {
            **self.envelope(run, "local-api-create", 1), "requestChecksum": checksum,
            "scenario": self.identity, "contextOnly": True,
        })
        event, event_ref = self.event(run, case, "case-created", auth, metadata_ref)
        case["sections"]["api-create"] = metadata_ref
        case["events"].append(event)
        case["idempotencyRecords"].append({
            "idempotencyKey": "api-create", "commandId": "create-case",
            "inputChecksum": checksum, "result": event_ref,
        })
        self.store.commit(run_id, 0, case)
        return event, False

    def policy_candidate_capability(self, capability):
        if not self.capability_available(capability):
            raise ApiFault(503, "not-authorized", f"Policy owner must register {capability}; mutation is unavailable.")

    def acknowledge(self, case_id, action_id, data):
        run, case = self.load(case_id)
        if not action_id.startswith("acknowledge-context-r"):
            raise ApiFault(403, "not-authorized", "Only an issued context acknowledgement action is supported.", run)
        self.policy_candidate_capability("acknowledge-run-context")
        checksum = semantic_checksum({k: v for k, v in data.items() if k not in {"idempotencyKey", "expectedRevision"}} |
                                     {"actionId": action_id})
        key = "context-ack:" + semantic_checksum({"key": data["idempotencyKey"]})[7:]
        record = next((r for r in case["idempotencyRecords"] if r["idempotencyKey"] == key), None)
        if record:
            if record["inputChecksum"] != checksum:
                raise ApiFault(409, "idempotency-conflict", "Acknowledgement key was used with different input.", run)
            return self.receipt_event(run, case, record, "run-context-acknowledged", "acknowledge-run-context"), True
        if data["expectedRevision"] != case["logicalRevision"]:
            raise ApiFault(409, "stale-revision", "Reload the case and its currently issued action.", run)
        if "api-context-ack" in case["sections"]:
            raise ApiFault(409, "stale-input", "This context was already acknowledged; no second mutation is needed.", run)
        if (action_id != issue_context_action(case, self.scenario) or data["scenario"] != self.identity
                or data["runManifestChecksum"] != run["stateChecksum"]):
            raise ApiFault(409, "stale-input", "Action, scenario or immutable run checksum does not match.", run)
        auth = self.authorize(run, case, "acknowledge-run-context", action_id)
        metadata_ref = self.store.put_artifact(run["runId"], {
            **self.envelope(run, "local-context-acknowledgement", case["logicalRevision"] + 1),
            "scenario": self.identity, "runManifestChecksum": run["stateChecksum"],
            "acknowledgement": "known-scenario-context-only", "promisesConfirmed": False,
            "architectureApproved": False, "runtimeVerified": False,
        })
        event, event_ref = self.event(run, case, "run-context-acknowledged", auth, metadata_ref)
        case["sections"]["api-context-ack"] = metadata_ref
        case["events"].append(event)
        case["idempotencyRecords"].append({
            "idempotencyKey": key, "commandId": "acknowledge-run-context",
            "inputChecksum": checksum, "result": event_ref,
        })
        self.store.commit(run["runId"], case["logicalRevision"], case)
        return event, False

    def artifact(self, case_id, artifact_id, checksum):
        try:
            fragment_validator("core", "ArtifactReference").validate({"artifactId": artifact_id, "checksum": checksum})
        except ValidationError as exc:
            raise ApiFault(400, "invalid-artifact", "Artifact ID and checksum must match the core reference format.") from exc
        run, case = self.load(case_id)
        allowed = []
        def walk(value):
            if isinstance(value, dict):
                if set(value) == {"artifactId", "checksum"}:
                    allowed.append(value)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(case)
        target = {"artifactId": artifact_id, "checksum": checksum}
        if target not in allowed:
            raise ApiFault(404, "invalid-artifact", "Artifact ID/checksum is not referenced by this case.", run)
        return self.store.read_artifact(run["runId"], target)


def create_app(config: Config):
    service = Service(config)
    app = FastAPI(title="Intent to Impact local API", version="1.0.0",
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.service = service
    app.state.sessions = {}
    netloc = urlsplit(config.origin).netloc

    def error(request, fault):
        value = {
            "schemaVersion": "1.0.0", "artifactType": "error-envelope", "createdAt": now(),
            "code": fault.code, "message": fault.message,
            "correlationId": getattr(request.state, "correlation_id", f"CORRELATION-{uuid4().hex}"),
            "diagnosticId": f"DIAGNOSTIC-{uuid4().hex}", "retryable": False, "allowedRecoveryActions": [],
        }
        if fault.run:
            value.update({k: fault.run[k] for k in ("runId", "caseId", "scope")})
        validate_contract(value, "E07")
        return JSONResponse(value, status_code=fault.status, headers={"Cache-Control": "no-store"})

    @app.middleware("http")
    async def boundary(request, call_next):
        request.state.correlation_id = f"CORRELATION-{uuid4().hex}"
        try:
            peer = request.client.host if request.client else ""
            try:
                loopback = ipaddress.ip_address(peer).is_loopback
            except ValueError:
                loopback = False
            if not loopback:
                raise ApiFault(403, "not-authorized", "Only a loopback peer is permitted.")
            if len(request.headers.getlist("host")) != 1 or request.headers["host"] != netloc:
                raise ApiFault(403, "not-authorized", "Host must exactly match the configured loopback origin.")
            if any(name in request.headers for name in ("forwarded", "x-forwarded-host", "x-forwarded-for", "x-forwarded-proto")):
                raise ApiFault(403, "not-authorized", "Proxy/forwarded headers are unsupported.")
            origins = request.headers.getlist("origin")
            if len(origins) > 1 or (origins and origins[0] != config.origin):
                raise ApiFault(403, "not-authorized", "Origin must exactly match the configured loopback origin.")
            unsafe = request.method not in {"GET", "HEAD"}
            if unsafe and origins != [config.origin]:
                raise ApiFault(403, "not-authorized", "State-changing requests require the exact Origin.")
            if request.url.path != "/session":
                cookies = request.headers.getlist("cookie")
                cookie_count = sum(part.strip().split("=", 1)[0] == "iti_session"
                                   for header in cookies for part in header.split(";"))
                if len(cookies) != 1 or cookie_count != 1:
                    raise ApiFault(401, "not-authorized", "Exactly one local session cookie is required.")
                cookie = request.cookies.get("iti_session")
                session = app.state.sessions.get(cookie)
                if session is None or session["expires"] <= time.monotonic():
                    raise ApiFault(401, "not-authorized", "A current local demo session is required.")
                if unsafe and (len(request.headers.getlist("x-csrf-token")) != 1 or
                               not secrets.compare_digest(request.headers["x-csrf-token"].encode(), session["csrf"].encode())):
                    raise ApiFault(403, "not-authorized", "A matching session CSRF token is required.")
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Demo-Actor"] = "demo-human"
            response.headers["X-Identity-Assurance"] = "local-demo"
            return response
        except ApiFault as fault:
            return error(request, fault)

    @app.exception_handler(ApiFault)
    async def api_error(request, fault):
        return error(request, fault)

    @app.exception_handler(StoreError)
    async def store_error(request, exc):
        status = 403 if exc.code == "not-authorized" else 409
        return error(request, ApiFault(status, exc.code, "Local state rejected the operation; reload or inspect the scoped case."))

    @app.exception_handler(PolicyConfigurationError)
    async def policy_error(request, exc):
        return error(request, ApiFault(503, "not-authorized", "The trusted server policy context is unavailable."))

    @app.exception_handler(ValidationError)
    @app.exception_handler(ReferenceIntegrityError)
    async def integrity_error(request, exc):
        return error(request, ApiFault(409, "invalid-artifact", "Stored or projected data failed contract/integrity validation."))

    @app.exception_handler(RequestValidationError)
    async def request_error(request, exc):
        return error(request, ApiFault(400, "invalid-artifact", "Required route/query fields are missing or malformed."))

    @app.exception_handler(HTTPException)
    async def route_error(request, exc):
        return error(request, ApiFault(exc.status_code, "invalid-artifact", "This local API route or method is unavailable."))

    @app.exception_handler(OSError)
    async def io_error(request, exc):
        return error(request, ApiFault(503, "recovery-required", "Local capture/commit is incomplete; do not assume success or re-execute work."))

    @app.post("/session")
    async def session(request: Request):
        tokens = request.headers.getlist("x-local-access-token")
        if len(tokens) != 1 or not secrets.compare_digest(tokens[0].encode(), config.access_token.encode()):
            raise ApiFault(401, "not-authorized", "The operator-supplied local access token is required.")
        app.state.sessions = {k: v for k, v in app.state.sessions.items() if v["expires"] > time.monotonic()}
        if len(app.state.sessions) >= 32:
            raise ApiFault(429, "not-authorized", "Local session capacity reached; reuse an existing session.")
        session_id, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        app.state.sessions[session_id] = {"csrf": csrf, "expires": time.monotonic() + 3600}
        response = JSONResponse({"schemaVersion": "1.0.0", "csrfToken": csrf, "identity": IDENTITY})
        response.set_cookie("iti_session", session_id, httponly=True, secure=False, samesite="strict", max_age=3600)
        return response

    @app.post("/cases")
    async def create_case(request: Request):
        if request.query_params:
            raise ApiFault(400, "invalid-artifact", "Create does not accept query fields.")
        data = await body(request, "CreateRequest")
        event, reused = service.create(data)
        validate_contract(event, "E04")
        return JSONResponse(event, status_code=200 if reused else 201,
                            headers={"Location": f"/cases/{event['caseId']}/experience"})

    @app.get("/cases/{case_id}/experience")
    async def experience(case_id: str, request: Request):
        if request.query_params:
            raise ApiFault(400, "invalid-artifact", "Experience does not accept query fields.")
        run, case = service.load(case_id)
        return initial_overview(case, run, service.scenario,
                                can_acknowledge=service.capability_available("acknowledge-run-context"))

    @app.post("/cases/{case_id}/actions/{action_id}")
    async def action(case_id: str, action_id: str, request: Request):
        if request.query_params:
            raise ApiFault(400, "invalid-artifact", "Action does not accept query fields.")
        data = await body(request, "ContextAcknowledgement")
        event, reused = service.acknowledge(case_id, action_id, data)
        validate_contract(event, "E04")
        return JSONResponse(event, headers={"X-Idempotent-Replay": str(reused).lower()})

    @app.get("/cases/{case_id}/artifacts/{artifact_id}")
    async def artifact(case_id: str, artifact_id: str, checksum: str, request: Request):
        if set(request.query_params) != {"checksum"} or len(request.query_params.getlist("checksum")) != 1:
            raise ApiFault(400, "invalid-artifact", "Artifact read requires only one checksum query field.")
        return JSONResponse(service.artifact(case_id, artifact_id, checksum),
                            headers={"Content-Disposition": "attachment; filename=artifact.json"})

    return app
