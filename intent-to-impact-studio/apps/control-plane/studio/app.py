"""Single-origin HTTP transport: loopback by default, explicitly gated ACA hosting."""

import hashlib
import hmac
import ipaddress
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException

from .service import StudioService, read_json, write_json
from .validation import StudioFailure, strict_json
from .hosting import authenticated_principal, load_hosted_config, validate_forwarding
from .model_client import FoundryModelClient

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
REPOSITORY_ROOT = WORKSPACE_ROOT.parent if WORKSPACE_ROOT.name == "intent-to-impact-studio" else WORKSPACE_ROOT
ORIGIN = "http://127.0.0.1:5173"
HOST = "127.0.0.1:5173"
COOKIE = "studio_session"
MAX_REQUEST_BYTES = 800 * 1024
SESSION_TTL = 3600
MAX_SESSIONS = 16
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
        "object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    ),
}


class Sessions:
    def __init__(self, root):
        self.path = root / "sessions.json"
        if self.path.is_symlink():
            raise StudioFailure("unsafe_storage", "Session storage cannot be a symlink.", 500)
        try:
            self.items = read_json(self.path)
        except FileNotFoundError:
            self.items = {}
        self.prune()

    def prune(self):
        self.items = {key: value for key, value in self.items.items() if value["expires"] > time.time()}

    def find(self, cookie):
        if not cookie or len(cookie) > 128:
            return None
        owner = hashlib.sha256(cookie.encode()).hexdigest()
        session = self.items.get(owner)
        if session and session["expires"] > time.time():
            return owner, session
        return None

    def issue(self, cookie):
        existing = self.find(cookie)
        if existing:
            return cookie, existing[1]["csrf"], max(0, int(existing[1]["expires"] - time.time()))
        self.prune()
        if len(self.items) >= MAX_SESSIONS:
            raise StudioFailure("session_limit", "Local session limit reached. Existing sessions expire after one hour.", 429, True)
        token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        owner = hashlib.sha256(token.encode()).hexdigest()
        self.items[owner] = {"csrf": csrf, "expires": time.time() + SESSION_TTL}
        write_json(self.path, self.items)
        return token, csrf, SESSION_TTL


class LocalTransport:
    def __init__(self, app, sessions, hosted_config=None, hosted_lock=None):
        self.app, self.sessions = app, sessions
        self.hosted_config, self.hosted_lock = hosted_config, hosted_lock

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secured_send(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend((key.lower().encode(), value.encode()) for key, value in SECURITY_HEADERS.items())
                message["headers"] = headers
            await send(message)

        try:
            config = self.hosted_config
            method, path = scope["method"], scope["path"]
            if config and path == "/healthz" and method in ("GET", "HEAD"):
                ready = bool(self.hosted_lock and self.hosted_lock.ready())
                response = (Response(status_code=200 if ready else 503) if method == "HEAD"
                            else JSONResponse({"ready": ready}, status_code=200 if ready else 503))
                await response(scope, receive, secured_send)
                return
            headers = {}
            for key, value in scope["headers"]:
                name = key.decode("latin-1").lower()
                security_header = name in {"host", "origin", "content-length", "cookie", "x-csrf-token", "x-studio-client"}
                if config:
                    security_header = security_header or name in {"authorization", "content-type", "forwarded"} or name.startswith(
                        ("x-ms-", "x-forwarded-", "x-original-", "x-rewrite-"))
                if name in headers and security_header:
                    raise StudioFailure("invalid_headers", "Duplicate security headers are not permitted.", 400)
                headers[name] = value.decode("latin-1")
            peer = (scope.get("client") or ("", 0))[0]
            try:
                local = ipaddress.ip_address(peer).is_loopback
            except ValueError:
                local = False
            if config:
                if headers.get("host") != config.host:
                    raise StudioFailure("invalid_origin", "Use the configured studio HTTPS origin.", 403)
                validate_forwarding(headers, config)
            elif not local or headers.get("host") != HOST:
                raise StudioFailure("invalid_origin", "Studio accepts only direct requests to 127.0.0.1:5173.", 403)
            if not config and any(name == "forwarded" or name.startswith(("x-forwarded-", "x-original-", "x-rewrite-")) for name in headers):
                raise StudioFailure("forwarded_request", "Forwarded requests are not supported.", 403)
            origin = headers.get("origin")
            expected_origin = config.public_origin if config else ORIGIN
            if origin is not None and origin != expected_origin:
                raise StudioFailure("invalid_origin", "Foreign origins are not permitted.", 403)
            api = path == "/api" or path.startswith("/api/")
            if config and config.auth_mode == "entra":
                principal = authenticated_principal(headers, config)
                if principal is None:
                    if not api and method == "GET" and ("text/html" in headers.get("accept", "") or not Path(path).suffix):
                        await RedirectResponse("/.auth/login/aad", status_code=302)(scope, receive, secured_send)
                        return
                    raise StudioFailure("authentication_required", "Sign in to the studio first.", 401)
                scope.setdefault("state", {})["principal_id"] = principal
            if method == "OPTIONS":
                raise StudioFailure("preflight_rejected", "Cross-origin preflight is not supported.", 405)
            if method not in ("GET", "HEAD", "POST"):
                raise StudioFailure("method_not_allowed", "Method not allowed.", 405)
            if api:
                if headers.get("x-studio-client") != "1":
                    raise StudioFailure("client_header_required", "X-Studio-Client: 1 is required.", 403)
                request = Request(scope)
                if not (method == "GET" and path == "/api/studio/session"):
                    found = self.sessions.find(request.cookies.get(COOKIE))
                    if not found:
                        raise StudioFailure("session_required", "Open a studio session first.", 401)
                    owner, session = found
                    scope.setdefault("state", {})["owner"] = owner
                    if method == "POST":
                        if origin != expected_origin or not hmac.compare_digest(headers.get("x-csrf-token", ""), session["csrf"]):
                            raise StudioFailure("csrf_rejected", "The exact studio Origin and session CSRF token are required.", 403)
            if method == "POST":
                if not api:
                    raise StudioFailure("method_not_allowed", "Static assets are read-only.", 405)
                if headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
                    raise StudioFailure("unsupported_media_type", "Use application/json.", 415)
                length = headers.get("content-length")
                if length is not None:
                    if not length.isdecimal():
                        raise StudioFailure("invalid_content_length", "Invalid content length.", 400)
                    if int(length) > MAX_REQUEST_BYTES:
                        raise StudioFailure("request_too_large", "Request exceeds 800 KiB.", 413)
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > MAX_REQUEST_BYTES:
                        raise StudioFailure("request_too_large", "Request exceeds 800 KiB.", 413)
                    if not message.get("more_body", False):
                        break
                delivered = False

                async def bounded_receive():
                    nonlocal delivered
                    if delivered:
                        return await receive()
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}

                await self.app(scope, bounded_receive, secured_send)
            else:
                await self.app(scope, receive, secured_send)
        except StudioFailure as exc:
            await JSONResponse(exc.public(), status_code=exc.status)(scope, receive, secured_send)


def create_app(data_root=None, static_root=None, model=None, bundle_builder=None, history_scope="session",
               hosted_config=None, hosted_lock=None):
    """Injected hosted_config permits isolated factory tests without a Linux lock.

    Environment-driven production creation requires the lock acquired by serve
    before service recovery. An unlocked test factory never reports ready.
    """
    import os

    model_mode = os.environ.get("STUDIO_MODEL_MODE", "live")
    if model_mode not in {"live", "simulated"}:
        raise ValueError("STUDIO_MODEL_MODE must be live or simulated.")
    if model_mode == "simulated" and os.environ.get("STUDIO_HOSTING") != "aca":
        raise ValueError("Judge simulation requires explicit STUDIO_HOSTING=aca.")
    if model_mode != "simulated" and getattr(model, "origin", None) == "simulated":
        raise ValueError("Judge simulation requires explicit STUDIO_MODEL_MODE=simulated.")
    injected_config = hosted_config is not None
    hosted_config = hosted_config or load_hosted_config()
    if hosted_config:
        if not injected_config and not (hosted_lock and hosted_lock.acquired):
            raise RuntimeError("Acquire the ACA worker lock in studio.serve before creating the app.")
        if hosted_lock is not None and (not hosted_lock.acquired or hosted_lock.config != hosted_config):
            raise RuntimeError("The ACA worker lock must be acquired for this configuration.")
        if data_root is not None and Path(data_root) != hosted_config.data_root:
            raise ValueError("Hosted storage must use STUDIO_DATA_ROOT.")
        data_root = hosted_config.data_root
        history_scope = "session" if hosted_config.auth_mode == "anonymous-demo" else "workspace"
        if model_mode == "simulated":
            if model is not None and getattr(model, "origin", None) != "simulated":
                raise ValueError("A live model cannot be injected into judge simulation.")
            if model is None:
                from .simulator import JudgeSimulator
                model = JudgeSimulator()
        else:
            model = model or FoundryModelClient(hosted_config=hosted_config)
        if bundle_builder is None:
            from functools import partial
            from .bundle import build_bundle
            bundle_builder = partial(build_bundle, compiler_path=hosted_config.bicep_path)
    service = StudioService(
        data_root or REPOSITORY_ROOT / ".intent-to-impact" / "studio" / "runs",
        model,
        bundle_builder,
        history_scope,
    )
    sessions = Sessions(service.root)
    dist = Path(static_root or WORKSPACE_ROOT / "apps" / "experience" / "dist").absolute()

    @asynccontextmanager
    async def lifespan(_):
        yield
        await service.shutdown()

    app = FastAPI(title="Live architecture studio", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.service = service
    app.state.sessions = sessions
    app.add_middleware(LocalTransport, sessions=sessions, hosted_config=hosted_config, hosted_lock=hosted_lock)

    @app.exception_handler(StudioFailure)
    async def failure_handler(_, exc):
        return JSONResponse(exc.public(), status_code=exc.status)

    @app.exception_handler(HTTPException)
    async def http_failure_handler(_, exc):
        return JSONResponse(
            {"code": "method_not_allowed" if exc.status_code == 405 else "not_found",
             "message": "Method not allowed." if exc.status_code == 405 else "Endpoint not found.",
             "retryable": False},
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def internal_handler(_, exc):
        return JSONResponse(
            {"code": "internal_error", "message": "Studio could not complete the request.", "retryable": False},
            status_code=500, headers=SECURITY_HEADERS,
        )

    @app.get("/api/studio/session")
    async def session(request: Request):
        token, csrf, max_age = sessions.issue(request.cookies.get(COOKIE))
        response = JSONResponse({"csrfToken": csrf})
        response.set_cookie(COOKIE, token, httponly=True, samesite="strict", secure=bool(hosted_config),
                            max_age=max_age, path="/api/studio")
        return response

    @app.get("/api/studio/health")
    async def health():
        return service.model.readiness()

    @app.post("/api/studio/analyses", status_code=202)
    async def analyse(request: Request):
        value = strict_json(await request.body())
        return await service.submit(request.state.owner, value)

    @app.get("/api/studio/jobs/{job_id}")
    async def get_job(job_id: str, request: Request):
        return service.get_job(request.state.owner, job_id)

    @app.get("/api/studio/history")
    async def history(request: Request):
        return service.history(request.state.owner)

    @app.get("/api/studio/history/{job_id}")
    async def saved_run(job_id: str, request: Request):
        return service.saved_run(request.state.owner, job_id)

    @app.get("/api/studio/history/{job_id}/builds/{build_id}")
    async def saved_build(job_id: str, build_id: str, request: Request):
        return service.saved_build(request.state.owner, job_id, build_id)

    @app.get("/api/studio/history/{job_id}/download")
    async def download_run(job_id: str, request: Request):
        archive = service.export_run(request.state.owner, job_id)
        return Response(archive, media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="studio-run-{job_id}.zip"'})

    @app.post("/api/studio/builds")
    async def build(request: Request):
        return await service.build(request.state.owner, strict_json(await request.body()))

    @app.get("/api/studio/builds/{build_id}/download")
    async def download(build_id: str, request: Request):
        path = service.download(request.state.owner, build_id)
        return FileResponse(path, media_type="application/zip", filename=f"studio-{build_id}.zip")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"])
    async def assets(path: str, request: Request):
        if path == "api" or path.startswith("api/"):
            raise StudioFailure("not_found", "API endpoint not found.", 404)
        if "\\" in path or any(part.startswith(".") for part in path.split("/") if part):
            raise StudioFailure("not_found", "Asset not found.", 404)
        candidate = dist / path
        if dist.is_symlink() or not candidate.resolve().is_relative_to(dist.resolve()):
            raise StudioFailure("not_found", "Asset not found.", 404)
        if candidate.is_file():
            return FileResponse(candidate)
        if Path(path).suffix:
            raise StudioFailure("not_found", "Asset not found.", 404)
        index = dist / "index.html"
        if index.is_file() and index.resolve().is_relative_to(dist.resolve()):
            return FileResponse(index)
        return Response("Frontend assets are not built. Run the experience production build first.", status_code=503, media_type="text/plain")

    return app
