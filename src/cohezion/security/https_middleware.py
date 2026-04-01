"""HTTPS enforcement and security headers middleware for Starlette/FastAPI."""

import logging
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .tls_config import TLSConfig


logger = logging.getLogger(__name__)


class HTTPSEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces HTTPS and adds security headers.

    - Rejects HTTP requests (except localhost development)
    - Adds HSTS headers
    - Adds security headers (X-Content-Type-Options, X-Frame-Options, etc.)
    - Restricts CORS origins
    """

    def __init__(
        self,
        app,
        tls_config: TLSConfig,
        allow_http_localhost: bool = True,
    ):
        """
        Initialize HTTPS enforcement middleware.

        Args:
            app: Starlette application
            tls_config: TLS configuration instance
            allow_http_localhost: Allow HTTP on localhost for development
        """
        super().__init__(app)
        self.tls_config = tls_config
        self.allow_http_localhost = allow_http_localhost

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through HTTPS enforcement and headers.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response with security headers added
        """
        # Check for HTTP on non-localhost
        if request.url.scheme != "https":
            # Allow HTTP on localhost for development
            if self.allow_http_localhost:
                client_host = request.client.host if request.client else ""
                # Allow localhost, 127.0.0.1, ::1, and testclient
                if client_host not in ("127.0.0.1", "localhost", "::1", "testclient"):
                    logger.warning(
                        "HTTP request rejected from non-localhost: %s",
                        client_host,
                    )
                    return Response(
                        content='{"error": "HTTPS required"}',
                        status_code=426,  # Upgrade Required
                        headers={"Upgrade": "TLS/1.2"},
                    )
            else:
                logger.warning("HTTP request rejected (HTTPS only)")
                return Response(
                    content='{"error": "HTTPS required"}',
                    status_code=426,
                    headers={"Upgrade": "TLS/1.2"},
                )

        # Check CORS origin
        origin = request.headers.get("origin")
        if origin and not self.tls_config.is_origin_allowed(origin):
            logger.warning("Request from disallowed origin: %s", origin)
            return Response(
                content='{"error": "Origin not allowed"}',
                status_code=403,
            )

        # Process request
        response = await call_next(request)

        # Add security headers
        security_headers = self.tls_config.get_security_headers()
        for header_name, header_value in security_headers.items():
            response.headers[header_name] = header_value

        # Add CORS header if origin is allowed
        if origin and self.tls_config.is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin

        return response


class SecureCookieMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces secure cookie flags.

    - Sets Secure flag (HTTPS only)
    - Sets HttpOnly flag (no JavaScript access)
    - Sets SameSite=Strict (CSRF protection)
    """

    def __init__(self, app, tls_config: TLSConfig):
        """
        Initialize secure cookie middleware.

        Args:
            app: Starlette application
            tls_config: TLS configuration instance
        """
        super().__init__(app)
        self.tls_config = tls_config

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through cookie security enforcement.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response with secure cookie flags applied
        """
        response = await call_next(request)

        # Get cookie flags
        flags = self.tls_config.get_cookie_flags()

        # Apply flags to Set-Cookie headers
        set_cookie_headers = response.headers.getlist("set-cookie")

        if set_cookie_headers:
            # Remove all set-cookie headers
            del response.headers["set-cookie"]

            # Add back with modified flags
            for cookie in set_cookie_headers:
                modified_cookie = self._apply_cookie_flags(cookie, flags)
                response.headers.append("set-cookie", modified_cookie)

        return response

    @staticmethod
    def _apply_cookie_flags(cookie: str, flags: dict) -> str:
        """
        Apply security flags to a Set-Cookie header value.

        Args:
            cookie: Original Set-Cookie header value
            flags: Dictionary of flags to apply

        Returns:
            Modified Set-Cookie header value
        """
        # Remove existing Secure, HttpOnly, SameSite flags
        cookie_parts = [
            p.strip()
            for p in cookie.split(";")
            if not any(
                p.strip().lower().startswith(prefix)
                for prefix in ("secure", "httponly", "samesite")
            )
        ]

        # Add new flags
        if flags.get("secure"):
            cookie_parts.append("Secure")

        if flags.get("httponly"):
            cookie_parts.append("HttpOnly")

        if samesite := flags.get("samesite"):
            cookie_parts.append(f"SameSite={samesite}")

        return "; ".join(cookie_parts)


def create_https_app(
    app,
    tls_config: TLSConfig,
    allow_http_localhost: bool = True,
):
    """
    Wrap an application with HTTPS enforcement middleware.

    Args:
        app: Base Starlette application
        tls_config: TLS configuration instance
        allow_http_localhost: Allow HTTP on localhost for development

    Returns:
        Application with HTTPS middleware applied
    """
    # Apply secure cookie middleware first (inner)
    app = SecureCookieMiddleware(app, tls_config)

    # Apply HTTPS enforcement middleware (outer)
    app = HTTPSEnforcementMiddleware(app, tls_config, allow_http_localhost=allow_http_localhost)

    return app
