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
    return get_credentials().get_secret(
        "COHEZION_MCP_API_KEY", env_var="MCP_API_KEY"
    )


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
