"""API key authentication for the MCP server."""

import hashlib
import hmac
import os
from typing import ClassVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class APIKeyAuth(BaseHTTPMiddleware):
    """Bearer token authentication middleware.

    Validates the Authorization header against the configured API key.
    The /health endpoint is excluded from auth for monitoring.
    """

    EXCLUDED_PATHS: ClassVar[set[str]] = {"/health", "/"}

    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header"},
                status_code=401,
            )

        token = auth_header[7:]
        if not hmac.compare_digest(token, self.api_key):
            return JSONResponse(
                {"error": "Invalid API key"},
                status_code=403,
            )

        return await call_next(request)


def generate_api_key() -> str:
    """Generate a cryptographically secure API key."""
    return hashlib.sha256(os.urandom(32)).hexdigest()


_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class AuthConfigError(RuntimeError):
    """Raised when the server would start without authentication."""


def check_auth_config(api_key: str, host: str, allow_no_auth: bool) -> None:
    """Refuse to start without an API key.

    Loopback alone is not a safe signal for this server: it is published through a
    tunnel (cloudflared or ngrok) that connects to loopback, so a loopback bind can
    still be reachable from the internet. The only way to run without a key is an
    explicit ``MCP_ALLOW_NO_AUTH=true`` on a loopback host, for local development.
    """
    if api_key:
        return
    if allow_no_auth and host in _LOOPBACK_HOSTS:
        return
    raise AuthConfigError(
        "MCP_API_KEY is not set, so the server refuses to start. Set MCP_API_KEY, "
        "or for local development only set MCP_ALLOW_NO_AUTH=true with a loopback "
        "MCP_HOST."
    )


def require_bearer(
    app, api_key: str, excluded_paths: frozenset[str] = frozenset({"/health"})
):
    """Wrap an ASGI app so every HTTP and WebSocket request needs ``Bearer <api_key>``.

    Pure ASGI rather than ``BaseHTTPMiddleware`` so streaming (SSE, streamable HTTP)
    responses pass through untouched. Lifespan events are not requests and pass
    through. An empty ``api_key`` passes everything; ``check_auth_config`` decides
    whether that is allowed before the server starts.
    """
    if not api_key:
        return app
    expected = api_key.encode()

    async def guarded(scope, receive, send):
        if (
            scope["type"] not in ("http", "websocket")
            or scope.get("path") in excluded_paths
        ):
            await app(scope, receive, send)
            return
        header = dict(scope.get("headers") or []).get(b"authorization", b"")
        if header.startswith(b"Bearer ") and hmac.compare_digest(header[7:], expected):
            await app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        response = JSONResponse(
            {"error": "Missing or invalid API key"}, status_code=401
        )
        await response(scope, receive, send)

    return guarded
