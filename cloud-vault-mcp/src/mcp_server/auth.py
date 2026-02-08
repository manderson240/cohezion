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
