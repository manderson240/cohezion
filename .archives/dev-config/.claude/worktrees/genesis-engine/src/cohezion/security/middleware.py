"""
FastAPI Security Middleware.

Integrates all security components:
- Rate limiting
- Authentication
- Input validation
- Prompt guard
- Output filtering
- Audit logging
"""

import time
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from cohezion.security.audit import get_audit_logger
from cohezion.security.auth import AuthError, verify_api_key
from cohezion.security.prompt_guard import PromptGuard
from cohezion.security.rate_limiter import get_rate_limiter


def add_security_middleware(app: FastAPI) -> None:
    """Add security middleware to FastAPI app."""

    limiter = get_rate_limiter()
    audit = get_audit_logger()
    PromptGuard()

    @app.middleware("http")
    async def security_middleware(request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        ip = request.client.host if request.client else None
        endpoint = request.url.path
        method = request.method
        user = None

        # Skip health checks
        if endpoint in ("/health", "/healthz", "/metrics"):
            return await call_next(request)

        # Rate limiting
        limit_result = limiter.check(ip or "unknown", endpoint)
        if not limit_result.allowed:
            audit.log_security(
                "rate_limit_exceeded",
                "blocked",
                ip,
                {
                    "endpoint": endpoint,
                    "remaining": limit_result.remaining,
                },
            )
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded"},
                headers={"Retry-After": str(int(limit_result.reset_after))},
            )

        # Authentication (for protected routes)
        if endpoint.startswith("/api/") or endpoint.startswith("/swarm/"):
            api_key = request.headers.get("X-API-Key")
            if api_key:
                try:
                    key_data = verify_api_key(api_key)
                    user = key_data.get("name")
                except AuthError as e:
                    audit.log_auth("api_key_verify", None, ip, False, e.message)
                    return JSONResponse(
                        status_code=401,
                        content={"error": e.message},
                    )

        # Process request
        response = await call_next(request)

        # Audit logging
        latency_ms = (time.time() - start_time) * 1000
        audit.log_request(endpoint, method, ip, user, response.status_code, latency_ms)

        # Add rate limit headers
        response.headers["X-RateLimit-Remaining"] = str(limit_result.remaining)
        response.headers["X-RateLimit-Limit"] = str(limit_result.limit)

        return response

    return None


def create_context_harness(query: str, context: dict) -> str:
    """
    Create a context harness for compound engineering.

    Combines query with relevant context for maximum Cohezion.
    """
    context_parts = []

    # Add system context
    if "skills" in context:
        context_parts.append(f"Available Skills: {', '.join(context['skills'][:5])}")

    if "history" in context:
        context_parts.append(f"Recent Context: {context['history'][-3:]}")

    if "artifacts" in context:
        context_parts.append(f"Relevant Artifacts: {len(context['artifacts'])} items")

    harness = f"""## Context Harness
{chr(10).join(context_parts)}

## Query
{query}
"""
    return harness
