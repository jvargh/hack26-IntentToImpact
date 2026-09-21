"""Fail-closed local dispatch policy; no execution, persistence or network operations."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
from weakref import WeakKeyDictionary

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from tools.contracts.validate import SCHEMA, assert_run_context_unchanged, validate_contract

VERSION = "1.0.0"
REGISTRY_PATH = Path(__file__).with_name("capabilities.v1.json")
PROFILES = {"read", "propose", "human", "materialize", "provider", "operator", "proof"}
LIVE_PROFILES = {"provider", "operator", "proof"}
HUMAN_PROFILES = {"human", "materialize", "operator", "proof"}
AUTHORITY_FIELDS = {
    "caller", "callerClass", "actor", "actorId", "humanInitiator", "transport", "channel",
    "permittedCapabilities", "authorizationContext", "runMode", "purpose", "scope",
    "runId", "caseId", "rootId", "configId", "scenarioId", "scenarioVersion", "scenarioHash",
    "activityClass", "approval", "gate", "currentRevision",
}
REQUEST_FIELDS = {"capability", "actionId", "subjectId", "expectedRevision", "boundChecksums"}
MESSAGES = {
    "untrusted-entry": ("not-authorized", "Use an entry handle issued to the trusted adapter."),
    "client-authority-forbidden": ("not-authorized", "Caller, scope and authority cannot come from request data."),
    "malformed-request": ("invalid-artifact", "Supply a valid bounded policy request."),
    "unknown-capability": ("not-authorized", "The capability is not registered."),
    "capability-not-granted": ("not-authorized", "The server entry is not granted this capability."),
    "caller-not-allowed": ("not-authorized", "This caller class or channel cannot request that capability."),
    "run-context-changed": ("not-authorized", "Stored run mode, purpose, scenario and scope are immutable."),
    "invalid-run-context": ("invalid-artifact", "The current run must validate against D22."),
    "live-mode-required": ("not-authorized", "Fixture and replay runs cannot use live providers or proof collectors."),
    "engine-facts-required": ("not-authorized", "The owning engine must provide current facts."),
    "stale-revision": ("stale-revision", "Expected revision does not match the current engine revision."),
    "action-binding-mismatch": ("stale-input", "The issued action, subject and checksums must match current engine facts."),
    "gate-required": ("approval-required", "The applicable current gate has not passed."),
    "approval-required": ("approval-required", "A matching current explicit demo-human approval is required."),
    "operator-consent-required": ("approval-required", "This operator action requires explicit current operator consent."),
    "engine-execution-required": ("not-authorized", "Live provider work requires engine authorization."),
    "invalid-policy": ("invalid-artifact", "The server policy configuration is invalid."),
}


def _error(reason, run=None, *, expected=None, actual=None):
    code, message = MESSAGES[reason]
    value = {
        "schemaVersion": VERSION, "artifactType": "error-envelope",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "code": code, "message": message, "correlationId": f"CORRELATION-{uuid4().hex}",
        "diagnosticId": f"DIAGNOSTIC-{uuid4().hex}", "retryable": False,
        "allowedRecoveryActions": [],
    }
    if run is not None:
        value.update({key: copy.deepcopy(run[key]) for key in ("runId", "caseId", "scope")})
    if expected is not None:
        value.update(expectedRevision=expected, actualRevision=actual)
    validate_contract(value, "E07")
    return value


class PolicyConfigurationError(ValueError):
    """Fail-closed server-configuration failure with a valid pre-context E07."""

    def __init__(self, reason="invalid-policy"):
        self.reason = reason
        self.error = _error(reason)
        super().__init__(self.error["message"])


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: str
    activity_class: str | None
    authorization_context: dict | None
    error: dict | None
    version: str = VERSION


@dataclass(frozen=True)
class ApprovalBinding:
    """Engine projection only, NOT a D07 approval schema or an approval factory."""

    approval_id: str
    actor_id: str
    capability: str
    action_id: str
    subject_id: str
    revision: int
    checksums: dict
    gate_id: str
    current: bool


class _Entry:
    __slots__ = ("__weakref__",)


class _Facts:
    __slots__ = ("__weakref__",)


def _definition(value, name):
    Draft202012Validator(
        {"$ref": f"#/definitions/{name}", "definitions": SCHEMA["definitions"]},
        format_checker=FormatChecker(),
    ).validate(value)


def _json(value):
    return json.loads(json.dumps(value, allow_nan=False))


def _registry():
    try:
        value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if type(value) is not dict or set(value) != {"version", "capabilities"} or value["version"] != VERSION:
            raise PolicyConfigurationError()
        if type(value["capabilities"]) is not dict or not value["capabilities"]:
            raise PolicyConfigurationError()
        for name, row in value["capabilities"].items():
            _definition(name, "ActionId")
            if (type(row) is not dict or set(row) != {"profile", "activityClass"}
                    or row["profile"] not in PROFILES
                    or row["activityClass"] not in {"product-workflow", "demo-operator"}):
                raise PolicyConfigurationError()
        return value["capabilities"]
    except (OSError, ValueError, TypeError, ValidationError) as exc:
        raise PolicyConfigurationError() from exc


class Policy:
    """Construct ONLY from server configuration and a trusted stored D22."""

    def __init__(self, stored_run, *, scope, root_id, config_id, enabled_capabilities=()):
        try:
            validate_contract(stored_run, "D22")
            self._run = _json(stored_run)
            if (scope != self._run["scope"] or root_id != self._run["rootId"]
                    or config_id != self._run["configId"]):
                raise PolicyConfigurationError()
            self._registry = _registry()
            if not isinstance(enabled_capabilities, (list, tuple, set, frozenset)):
                raise PolicyConfigurationError()
            if any(type(c) is not str or c not in self._registry for c in enabled_capabilities):
                raise PolicyConfigurationError()
            self._enabled = frozenset(enabled_capabilities)
        except (ValidationError, TypeError, ValueError, RecursionError) as exc:
            raise PolicyConfigurationError() from exc
        self._entries = WeakKeyDictionary()
        self._facts = WeakKeyDictionary()

    def human_entry(self, channel, *, capabilities=()):
        """Trusted browser/CLI/harness adapter calls this at composition time."""
        caller = {"callerClass": "human", "channel": channel, "actor": {
            "kind": "human", "actorId": "demo-human", "identityAssurance": "local-demo",
        }}
        return self._entry(caller, capabilities, False)

    def agent_entry(self, executor_id, *, capabilities=(), human_initiated=False):
        caller = {"callerClass": "agent", "channel": "model",
                  "actor": {"kind": "agent", "actorId": executor_id}}
        return self._entry(caller, capabilities, human_initiated)

    def system_entry(self, channel, executor_id, *, capabilities=(), human_initiated=False):
        caller = {"callerClass": "system", "channel": channel,
                  "actor": {"kind": "system", "actorId": executor_id}}
        return self._entry(caller, capabilities, human_initiated)

    def _entry(self, caller, capabilities, human_initiated):
        try:
            _definition(caller, "TrustedCaller")
            if (not isinstance(capabilities, (list, tuple, set, frozenset))
                    or any(type(c) is not str or c not in self._enabled for c in capabilities)
                    or type(human_initiated) is not bool):
                raise PolicyConfigurationError()
        except (ValidationError, TypeError, ValueError) as exc:
            raise PolicyConfigurationError() from exc
        handle = _Entry()
        self._entries[handle] = (_json(caller), frozenset(capabilities), human_initiated)
        return handle

    def engine_facts(self, *, current_revision, capability=None, action_id=None, subject_id=None,
                     checksums=None, gate_id=None, gate_passed=False, approval=None,
                     operator_consent=False, execution_authorized=False):
        """Owning engine supplies facts; never call with a client/model facts object."""
        try:
            if type(current_revision) is not int or current_revision < 0:
                raise PolicyConfigurationError()
            for value, definition in (
                (capability, "ActionId"), (action_id, "ActionId"),
                (subject_id, "Identifier"), (gate_id, "ActionId"),
            ):
                if value is not None:
                    _definition(value, definition)
            if capability is not None and capability not in self._registry:
                raise PolicyConfigurationError()
            checksums = {} if checksums is None else checksums
            _definition(checksums, "ChecksumMap")
            if any(type(v) is not bool for v in (gate_passed, operator_consent, execution_authorized)):
                raise PolicyConfigurationError()
            if approval is not None:
                if type(approval) is not ApprovalBinding:
                    raise PolicyConfigurationError()
                _definition(approval.approval_id, "Identifier")
                _definition(approval.capability, "ActionId")
                _definition(approval.action_id, "ActionId")
                _definition(approval.subject_id, "Identifier")
                _definition(approval.gate_id, "ActionId")
                _definition(approval.checksums, "ChecksumMap")
                if (approval.actor_id != "demo-human" or type(approval.current) is not bool
                        or type(approval.revision) is not int or approval.revision < 0):
                    raise PolicyConfigurationError()
        except (ValidationError, ValueError, TypeError) as exc:
            raise PolicyConfigurationError() from exc
        handle = _Facts()
        self._facts[handle] = {
            "revision": current_revision, "capability": capability, "action": action_id,
            "subject": subject_id, "checksums": copy.deepcopy(checksums), "gate": gate_id,
            "gate_passed": gate_passed, "approval": copy.deepcopy(approval),
            "operator_consent": operator_consent, "execution_authorized": execution_authorized,
        }
        return handle

    @staticmethod
    def _caller_allowed(caller, profile):
        kind, channel = caller["callerClass"], caller["channel"]
        if profile in HUMAN_PROFILES:
            return kind == "human" and (profile not in {"operator", "proof"} or channel == "harness")
        if profile == "provider":
            return kind == "system" and channel == "worker"
        return True

    def _authorization(self, caller, grants, human_initiated, revision):
        at = datetime.now(timezone.utc).isoformat()
        value = {
            "schemaVersion": VERSION, "artifactType": "authorization-context",
            "artifactId": f"AUTH-{uuid4().hex}", "runId": self._run["runId"],
            "caseId": self._run["caseId"], "scope": copy.deepcopy(self._run["scope"]),
            "caseRevisionAtWrite": revision, "createdAt": at, "updatedAt": at,
            "derivedFrom": {"run-manifest": self._run["stateChecksum"]},
            "caller": copy.deepcopy(caller), "permittedCapabilities": sorted(grants),
            "correlationId": f"CORRELATION-{uuid4().hex}",
        }
        if human_initiated:
            value["humanInitiator"] = {"actorId": "demo-human", "identityAssurance": "local-demo"}
        value["stateChecksum"] = "sha256:" + hashlib.sha256(
            (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        ).hexdigest()
        validate_contract(value, "E08")
        return value

    def authorize(self, entry, request, *, current_run, facts=None):
        """Only request is untrusted input. An allowed result does not perform an action."""
        activity = None
        authorization = None

        def deny(reason, expected=None, actual=None):
            error = _error(reason, self._run, expected=expected, actual=actual)
            if authorization is not None:
                error["correlationId"] = authorization["correlationId"]
            return GuardResult(False, reason, activity, authorization, error)

        if type(entry) is not _Entry or entry not in self._entries:
            return deny("untrusted-entry")
        caller, configured_grants, human_initiated = self._entries[entry]
        try:
            validate_contract(current_run, "D22")
        except (ValidationError, TypeError, ValueError, RecursionError):
            return deny("invalid-run-context")
        try:
            assert_run_context_unchanged(self._run, current_run)
        except ValueError:
            return deny("run-context-changed")
        if type(request) is not dict:
            return deny("malformed-request")
        if set(request) & AUTHORITY_FIELDS:
            return deny("client-authority-forbidden")
        if set(request) - REQUEST_FIELDS or "capability" not in request:
            return deny("malformed-request")
        capability = request["capability"]
        if type(capability) is not str or capability not in self._registry:
            return deny("unknown-capability")
        try:
            for field, definition in (
                ("actionId", "ActionId"), ("subjectId", "Identifier"), ("boundChecksums", "ChecksumMap"),
            ):
                if field in request:
                    _definition(request[field], definition)
            if ("expectedRevision" in request and (
                type(request["expectedRevision"]) is not int or request["expectedRevision"] < 0
            )):
                return deny("malformed-request")
        except (ValidationError, TypeError, ValueError, RecursionError):
            return deny("malformed-request")
        profile = self._registry[capability]["profile"]
        activity = self._registry[capability]["activityClass"]
        valid_grants = {
            c for c in configured_grants
            if self._caller_allowed(caller, self._registry[c]["profile"])
            and (self._run["runMode"] == "live" or self._registry[c]["profile"] not in LIVE_PROFILES)
        }
        engine = self._facts.get(facts) if type(facts) is _Facts else None
        revision = engine["revision"] if engine else current_run["caseRevisionAtWrite"]
        authorization = self._authorization(caller, valid_grants, human_initiated, revision)
        if capability not in configured_grants:
            return deny("capability-not-granted")
        if not self._caller_allowed(caller, profile):
            return deny("caller-not-allowed")
        if profile in LIVE_PROFILES and self._run["runMode"] != "live":
            return deny("live-mode-required")
        if profile == "read":
            if "expectedRevision" in request and engine is None:
                return deny("engine-facts-required")
            if "expectedRevision" in request and request["expectedRevision"] != revision:
                return deny("stale-revision", request["expectedRevision"], revision)
            return GuardResult(True, "allowed", activity, authorization, None)
        if engine is None:
            return deny("engine-facts-required")
        if "expectedRevision" not in request:
            return deny("malformed-request")
        if request["expectedRevision"] != revision:
            return deny("stale-revision", request["expectedRevision"], revision)
        if (engine["capability"] != capability or not engine["action"] or not engine["subject"]
                or not engine["checksums"] or request.get("actionId") != engine["action"]
                or request.get("subjectId") != engine["subject"]
                or request.get("boundChecksums") != engine["checksums"]):
            return deny("action-binding-mismatch")
        if profile in HUMAN_PROFILES and (not engine["gate"] or not engine["gate_passed"]):
            return deny("gate-required")
        if profile in {"materialize", "operator"}:
            approval = engine["approval"]
            if (approval is None or not approval.current or approval.actor_id != "demo-human"
                    or approval.capability != capability or approval.action_id != engine["action"]
                    or approval.subject_id != engine["subject"] or approval.revision != revision
                    or approval.checksums != engine["checksums"] or approval.gate_id != engine["gate"]):
                return deny("approval-required")
        if profile in {"operator", "proof"} and not engine["operator_consent"]:
            return deny("operator-consent-required")
        if profile == "provider" and not engine["execution_authorized"]:
            return deny("engine-execution-required")
        return GuardResult(True, "allowed", activity, authorization, None)


def same_origin(origin, host, *, expected_origin):
    """Optional exact loopback Origin/Host check; the HTTP adapter must call it."""
    if not all(type(value) is str for value in (origin, host, expected_origin)):
        return False
    try:
        parsed = urlsplit(expected_origin)
        return bool(
            parsed.scheme in {"http", "https"} and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            and parsed.port is not None and not parsed.username and not parsed.password
            and not parsed.path and not parsed.query and not parsed.fragment
            and origin == expected_origin and host == parsed.netloc
        )
    except ValueError:
        return False
