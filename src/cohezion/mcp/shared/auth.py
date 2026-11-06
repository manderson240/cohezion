"""Authentication middleware for MCP servers."""

import logging
from functools import lru_cache

from aiohttp import web

from cohezion.security.credentials import get_credentials


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_api_key() -> str | None:
    """Lazy accessor for MCP_API_KEY.

    Per CLAUDE.md L54-72, secret lookups must NOT run at module import time
    (they trigger Bitwarden vault calls that exceed the stdio MCP handshake
    budget). Cached after first successful lookup. (Ω12 P1 Patch 11)
    """
    return get_credentials().get_secret("COHEZION_MCP_API_KEY", env_var="MCP_API_KEY")


@web.middleware
async def api_key_middleware(request: web.Request, handler):
    """Middleware to validate API keys on all requests except /health and /."""
    # Allow health checks and index without auth
    if request.path in ["/health", "/"]:
        return await handler(request)

    api_key = get_api_key()
    if not api_key:
        logger.warning(
            "MCP_API_KEY is not set in the environment. Denying access to secure endpoint."
        )
        return web.json_response({"error": "Server authentication not configured"}, status=500)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return web.json_response(
            {"error": "Missing or invalid Authorization header. Expected 'Bearer <token>'."},
            status=401,
        )

    token = auth_header[7:]

    # Safe constant-time comparison could be used here in production
    import hmac

    if not hmac.compare_digest(token.encode(), api_key.encode()):
        return web.json_response({"error": "Invalid API key"}, status=403)

    return await handler(request)


def auth_headers() -> dict[str, str]:
    """Headers a client needs to call another Cohezion MCP server."""
    api_key = get_api_key()
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


class BearerAuthASGI:
    """ASGI twin of ``api_key_middleware``, for FastMCP's HTTP transport.

    Same rules: ``/health`` is open, everything else needs ``Bearer <MCP_API_KEY>``,
    and a server with no key configured refuses every request (fails closed).
    Pure ASGI, so streamed MCP responses pass through untouched.
    """

    EXCLUDED_PATHS: frozenset[str] = frozenset({"/health"})

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] not in ("http", "websocket") or scope.get("path") in self.EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return
        import hmac

        from starlette.responses import JSONResponse

        api_key = get_api_key()
        header = dict(scope.get("headers") or []).get(b"authorization", b"")
        if (
            api_key
            and header.startswith(b"Bearer ")
            and hmac.compare_digest(header[7:], api_key.encode())
        ):
            await self.app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if not api_key:
            response = JSONResponse(
                {"error": "Server authentication not configured"}, status_code=500
            )
        else:
            response = JSONResponse({"error": "Missing or invalid API key"}, status_code=401)
        await response(scope, receive, send)


def serve_fastmcp_http(app, port: int, transport: str = "http") -> None:
    """Run a FastMCP server over HTTP behind ``BearerAuthASGI``.

    The one way Cohezion runs FastMCP over HTTP, so no server can be started on the
    network without the key check. stdio transports need no auth and don't use it.
    """
    from starlette.middleware import Middleware

    from cohezion.mcp.shared.bind import bind_host

    app.run(
        transport=transport,
        host=bind_host(authenticated=True),
        port=port,
        middleware=[Middleware(BearerAuthASGI)],
    )
