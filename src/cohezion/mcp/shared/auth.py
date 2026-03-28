"""Authentication middleware for MCP servers."""

import hmac
import logging
import os

from aiohttp import web

from cohezion.security.credentials import get_credentials


logger = logging.getLogger(__name__)

# Global cache for the static API key
_MCP_API_KEY = None

# Ephemeral token provided by MCPServerManager
MCP_AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN")


def get_mcp_api_key():
    """Lazily load the static MCP API key."""
    global _MCP_API_KEY
    if _MCP_API_KEY is None:
        _MCP_API_KEY = get_credentials().get_secret("COHEZION_MCP_API_KEY", env_var="MCP_API_KEY")
    return _MCP_API_KEY


@web.middleware
async def api_key_middleware(request: web.Request, handler):
    """Middleware to validate API keys/tokens on all requests except /health and /."""
    # Allow health checks and index without auth
    if request.path in ["/health", "/"]:
        return await handler(request)

    api_key = get_mcp_api_key()

    if not api_key and not MCP_AUTH_TOKEN:
        logger.warning(
            "Neither MCP_API_KEY nor MCP_AUTH_TOKEN is set. Denying access to secure endpoint."
        )
        return web.json_response({"error": "Server authentication not configured"}, status=500)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return web.json_response(
            {"error": "Missing or invalid Authorization header. Expected 'Bearer <token>'."},
            status=401,
        )

    token = auth_header[7:]

    # Validate against either the static API key or the ephemeral auth token
    valid = False
    if (api_key and hmac.compare_digest(token.encode(), api_key.encode())) or (
        MCP_AUTH_TOKEN and hmac.compare_digest(token.encode(), MCP_AUTH_TOKEN.encode())
    ):
        valid = True

    if not valid:
        return web.json_response({"error": "Invalid API key or token"}, status=403)

    return await handler(request)
