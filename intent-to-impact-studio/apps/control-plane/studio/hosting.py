"""Explicit ACA runtime configuration and Easy Auth principal validation.

This mode REQUIRES ACA Easy Auth to be enabled for the configured Entra tenant,
with ingress authenticating requests and replacing client-supplied principal
headers. These headers are not independently signed credentials. Never expose
this backend through an ingress that bypasses Easy Auth. Only STUDIO_HOSTING=aca
enables this trust boundary; local mode never trusts forwarded identity.
Entra operators share workspace history. Explicit anonymous-demo mode skips
sign-in but keeps each browser session's history isolated.
"""

import base64
import binascii
import ipaddress
import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from .validation import StudioFailure, strict_json

OID_CLAIMS = {"oid", "http://schemas.microsoft.com/identity/claims/objectidentifier"}
TENANT_CLAIMS = {"tid", "http://schemas.microsoft.com/identity/claims/tenantid"}
FORWARD_HEADERS = {"x-forwarded-for", "x-forwarded-proto", "x-forwarded-host",
                   "x-forwarded-port", "x-forwarded-client-cert", "x-forwarded-path"}


def _uuid(value, name):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError(f"{name} must contain canonical UUIDs.") from None
    return value


@dataclass(frozen=True)
class HostedConfig:
    public_origin: str
    allowed_object_ids: frozenset[str]
    tenant_id: str
    managed_identity_client_id: str
    data_root: Path
    bicep_path: Path
    auth_mode: str = "entra"

    def __post_init__(self):
        if self.auth_mode not in {"entra", "anonymous-demo"}:
            raise ValueError("STUDIO_AUTH_MODE must be entra or anonymous-demo.")
        origin = self.public_origin
        if not isinstance(origin, str) or not origin.startswith("https://"):
            raise ValueError("STUDIO_PUBLIC_ORIGIN must be an exact HTTPS origin.")
        host = origin[len("https://"):]
        labels = host.split(".")
        if (
            len(host) > 253 or len(labels) < 2
            or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)
            or any(word in host for word in ("placeholder", "replace-me", "your-app", "example"))
            or labels[-1] in {"invalid", "localhost", "test"}
        ):
            raise ValueError("STUDIO_PUBLIC_ORIGIN must be the actual app FQDN, without path, port or placeholders.")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("STUDIO_PUBLIC_ORIGIN must use an app FQDN, not an IP address.")
        _uuid(self.tenant_id, "STUDIO_TENANT_ID")
        _uuid(self.managed_identity_client_id, "STUDIO_MANAGED_IDENTITY_CLIENT_ID")
        if not isinstance(self.allowed_object_ids, frozenset) or not self.allowed_object_ids:
            raise ValueError("STUDIO_ALLOWED_OBJECT_IDS must be a nonempty set of UUIDs.")
        for oid in self.allowed_object_ids:
            _uuid(oid, "STUDIO_ALLOWED_OBJECT_IDS")
        object.__setattr__(self, "data_root", Path(self.data_root))
        object.__setattr__(self, "bicep_path", Path(self.bicep_path))
        if not self.storage_ready():
            raise ValueError("STUDIO_DATA_ROOT must be an absolute, existing writable directory without symlinks.")
        compiler = self.bicep_path
        if not compiler.is_absolute() or compiler.resolve() != compiler or not compiler.is_file() or not os.access(compiler, os.X_OK):
            raise ValueError("STUDIO_BICEP_PATH must be an absolute, existing executable file without symlinks.")

    @property
    def host(self):
        return self.public_origin[len("https://"):]

    def storage_ready(self):
        try:
            root = self.data_root
            return (root.is_absolute() and root.resolve() == root and not root.is_symlink()
                    and root.is_dir() and os.access(root, os.W_OK | os.X_OK))
        except OSError:
            return False


def load_hosted_config(environ=None):
    env = os.environ if environ is None else environ
    mode = env.get("STUDIO_HOSTING", "")
    if mode in {"", "local"}:
        return None
    if mode != "aca":
        raise ValueError("STUDIO_HOSTING must be aca, local, or unset.")
    names = ("STUDIO_PUBLIC_ORIGIN", "STUDIO_ALLOWED_OBJECT_IDS", "STUDIO_TENANT_ID",
             "STUDIO_MANAGED_IDENTITY_CLIENT_ID", "STUDIO_DATA_ROOT", "STUDIO_BICEP_PATH")
    if any(not env.get(name) for name in names):
        raise ValueError("ACA hosting requires all STUDIO_PUBLIC_ORIGIN, STUDIO_ALLOWED_OBJECT_IDS, "
                         "STUDIO_TENANT_ID, STUDIO_MANAGED_IDENTITY_CLIENT_ID, STUDIO_DATA_ROOT and STUDIO_BICEP_PATH settings.")
    object_ids = env["STUDIO_ALLOWED_OBJECT_IDS"].split(",")
    if len(set(object_ids)) != len(object_ids):
        raise ValueError("STUDIO_ALLOWED_OBJECT_IDS must not contain duplicate UUIDs.")
    return HostedConfig(
        env["STUDIO_PUBLIC_ORIGIN"], frozenset(object_ids), env["STUDIO_TENANT_ID"],
        env["STUDIO_MANAGED_IDENTITY_CLIENT_ID"], Path(env["STUDIO_DATA_ROOT"]), Path(env["STUDIO_BICEP_PATH"]),
        env.get("STUDIO_AUTH_MODE", "entra"),
    )


def validate_forwarding(headers, config):
    unsupported = [name for name in headers
                   if (name == "forwarded" or name.startswith(("x-forwarded-", "x-original-", "x-rewrite-")))
                   and name not in FORWARD_HEADERS]
    if unsupported:
        raise StudioFailure("forwarded_request", "Unsupported forwarding headers: " + ", ".join(sorted(unsupported)[:8]), 403)
    # ACA/Envoy includes port, path and client-certificate metadata. None is used
    # for identity, routing or origin; the configured HTTPS Host stays authoritative.
    if headers.get("x-forwarded-proto", "https") != "https" or headers.get("x-forwarded-host", config.host) != config.host:
        raise StudioFailure("invalid_origin", "Forwarded origin does not match the configured HTTPS origin.", 403)
    if "x-forwarded-for" in headers:
        addresses = headers["x-forwarded-for"].split(",")
        try:
            if len(addresses) > 16:
                raise ValueError
            for address in addresses:
                ipaddress.ip_address(address.strip())
        except ValueError:
            raise StudioFailure("forwarded_request", "Invalid forwarded client addresses.", 403) from None


def authenticated_principal(headers, config):
    """Return the allowed OID, None for anonymous, or reject malformed/foreign identity."""
    encoded = headers.get("x-ms-client-principal")
    principal_id = headers.get("x-ms-client-principal-id")
    if encoded is None and principal_id is None:
        return None
    try:
        if not encoded or not principal_id or len(encoded) > 32768:
            raise ValueError
        _uuid(principal_id, "Principal ID")
        principal = strict_json(base64.b64decode(encoded, validate=True))
        if not isinstance(principal, dict) or principal.get("auth_typ") != "aad":
            raise ValueError
        if headers.get("x-ms-client-principal-idp", "aad") != "aad":
            raise ValueError
        claims = principal.get("claims")
        if not isinstance(claims, list) or any(not isinstance(claim, dict) for claim in claims):
            raise ValueError
        oids = [claim.get("val") for claim in claims if claim.get("typ") in OID_CLAIMS]
        tenants = [claim.get("val") for claim in claims if claim.get("typ") in TENANT_CLAIMS]
        if (not oids or not tenants or any(oid != principal_id for oid in oids)
                or any(tenant != config.tenant_id for tenant in tenants)
                or principal_id not in config.allowed_object_ids):
            raise ValueError
    except (ValueError, TypeError, binascii.Error, StudioFailure):
        raise StudioFailure("principal_forbidden", "The authenticated principal is not an allowed studio operator.", 403) from None
    return principal_id
