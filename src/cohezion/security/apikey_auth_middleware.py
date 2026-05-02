"""FastAPI middleware for per-agent API key authentication.

Validates X-Agent-Token header on all requests, replacing shared API key
authentication with per-agent credential system.

Features:
- Per-request token validation
- Permission-based access control
- Request context enrichment with agent info
- Configurable protected endpoints
- Non-blocking error handling
"""

import logging
from collections.abc import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from cohezion.security.agent_auth import AgentAuthManager


logger = logging.getLogger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for per-agent API key validation.

    Intercepts all requests and validates X-Agent-Token header against
    registered agent credentials.

    Example usage::

        from fastapi import FastAPI
        from cohezion.security.apikey_auth_middleware import APIKeyAuthMiddleware
        from cohezion.security.agent_auth import AgentAuthManager

        app = FastAPI()
        auth_manager = AgentAuthManager()
        app.add_middleware(APIKeyAuthMiddleware, auth_manager=auth_manager)

        # Requests must include X-Agent-Token header:
        # curl -H "X-Agent-Token: <token>" http://localhost:8001/api/tool
    """

    def __init__(
        self,
        app,
        auth_manager: AgentAuthManager,
        protected_paths: list[str] | None = None,
        skip_paths: list[str] | None = None,
    ):
        """Initialize middleware.

        Args:
            app: FastAPI application instance
            auth_manager: AgentAuthManager for token validation
            protected_paths: URL patterns requiring authentication (default: all /api/*)
            skip_paths: URL patterns to skip authentication (default: /health, /docs)
        """
        super().__init__(app)
        self.auth_manager = auth_manager

        # Default to protecting all /api/* endpoints
        self.protected_paths = protected_paths or ["/api/"]

        # Default skip paths for health checks and documentation
        self.skip_paths = skip_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/metrics",
        ]

    async def dispatch(self, request: Request, call_next: Callable):
        """Middleware dispatch to validate authentication.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response (either error or from handler)
        """
        # Check if path should be protected
        path = request.url.path
        should_protect = any(path.startswith(p) for p in self.protected_paths)
        should_skip = any(path.startswith(p) for p in self.skip_paths)

        if not should_protect or should_skip:
            return await call_next(request)

        # Extract token from header
        token = request.headers.get("X-Agent-Token")

        if not token:
            logger.warning(
                "Request to %s missing X-Agent-Token header (remote: %s)",
                path,
                request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing X-Agent-Token header"},
            )

        # Validate token
        credential = self.auth_manager.validate_token(token)

        if not credential:
            logger.warning(
                "Request to %s with invalid token %s (remote: %s)",
                path,
                token[:8] + "...",
                request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired X-Agent-Token"},
            )

        # Attach credential info to request state for handlers
        request.state.agent_id = credential.agent_id
        request.state.agent_token = token
        request.state.agent_permissions = credential.permissions
        request.state.agent_credential = credential

        logger.debug(
            "Authenticated request to %s from agent %s",
            path,
            credential.agent_id,
        )

        # Continue with next middleware/handler
        return await call_next(request)

    def require_permission(self, permission: str):
        """Decorator for endpoints requiring specific permission.

        Example usage::

            auth_middleware = APIKeyAuthMiddleware(app, auth_manager)

            @app.post("/api/vault/write")
            @auth_middleware.require_permission("write")
            async def vault_write(request: Request, path: str, data: str):
                # Only agents with "write" permission can call this
                return {"status": "ok"}
        """

        def decorator(func: Callable):
            async def wrapper(request: Request, *args, **kwargs):
                if not hasattr(request.state, "agent_permissions"):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Authentication required"},
                    )

                if permission not in request.state.agent_permissions:
                    logger.warning(
                        "Agent %s attempted %s without %s permission",
                        request.state.agent_id,
                        request.url.path,
                        permission,
                    )
                    return JSONResponse(
                        status_code=403,
                        content={"detail": f"Permission '{permission}' required"},
                    )

                return await func(request, *args, **kwargs)

            return wrapper

        return decorator
