"""Authentication middleware for MCP servers."""

import logging

from aiohttp import web

from cohezion.security.credentials import get_credentials


logger = logging.getLogger(__name__)

# Lazy accessor for MCP_API_KEY to prevent startup latency
_mcp_api_key: str | None = None


def get_mcp_api_key() -> str | None:
    """Get MCP API key with lazy initialization."""
    global _mcp_api_key
    if _mcp_api_key is None:
        _mcp_api_key = get_credentials().get_secret("COHEZION_MCP_API_KEY", env_var="MCP_API_KEY")
    return _mcp_api_key


@web.middleware
async def api_key_middleware(request: web.Request, handler):
    """Middleware to validate API keys on all requests except /health and /."""
    # Allow health checks and index without auth
    if request.path in ["/health", "/"]:
        return await handler(request)

    mcp_api_key = get_mcp_api_key()
    if not mcp_api_key:
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

    if not hmac.compare_digest(token.encode(), mcp_api_key.encode()):
        return web.json_response({"error": "Invalid API key"}, status=403)

    return await handler(request)
