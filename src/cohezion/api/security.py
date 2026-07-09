import functools
import logging
import os
import time
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cohezion.security.auth import AuthError, verify_api_key, verify_token


logger = logging.getLogger(__name__)

# Basic in-memory rate limiter for demo/internal use
# For production, this would use Redis or SurrealDB
_rate_limits: dict[str, tuple[float, int]] = {}

_bearer_scheme = HTTPBearer(auto_error=False)


def _get_api_key_from_env() -> str:
    """Return the configured API key, or raise if none is set."""
    key = os.environ.get("COHEZION_API_KEY")
    if not key:
        raise RuntimeError(
            "COHEZION_API_KEY environment variable is required for API authentication"
        )
    return key


def rate_limit(requests_per_minute: int = 60):
    """
    FastAPI decorator to enforce rate limits on endpoints.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Attempt to find request in kwargs
            request = kwargs.get("request")
            if not request or not isinstance(request, Request):
                # If no request object, we can't easily rate limit by IP
                return await func(*args, **kwargs)

            client_ip = request.client.host if request.client else "unknown"
            endpoint = func.__name__
            key = f"{client_ip}:{endpoint}"

            now = time.time()
            if key in _rate_limits:
                last_request, count = _rate_limits[key]
                if now - last_request < 60:
                    if count >= requests_per_minute:
                        logger.warning(f"Rate limit exceeded for {client_ip} on {endpoint}")
                        raise HTTPException(status_code=429, detail="Rate limit exceeded")
                    _rate_limits[key] = (last_request, count + 1)
                else:
                    _rate_limits[key] = (now, 1)
            else:
                _rate_limits[key] = (now, 1)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def requires_auth(func: Callable):
    """
    FastAPI decorator to enforce authentication.
    Validates the Authorization header as a JWT token or API key.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request or not isinstance(request, Request):
            # For internal calls without Request objects, skip auth
            return await func(*args, **kwargs)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.error(f"Unauthorized access attempt to {func.__name__}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header",
            )

        scheme, _, token = auth_header.partition(" ")
        scheme = scheme.lower()
        token = token.strip() if token else auth_header.strip()

        try:
            if scheme == "bearer":
                verify_token(token)
            elif scheme == "apikey" or not scheme:
                verify_api_key(token)
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Unsupported authorization scheme: {scheme}",
                )
        except AuthError as exc:
            logger.warning(f"Authentication failed for {func.__name__}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=exc.message,
            ) from exc

        return await func(*args, **kwargs)

    return wrapper


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),  # noqa: B008
) -> dict:
    """Dependency version of the auth check, compatible with FastAPI Depends()."""
    try:
        return verify_token(credentials.credentials)
    except AuthError as exc:
        # Fallback: treat as API key
        try:
            return verify_api_key(credentials.credentials)
        except AuthError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=exc.message,
            ) from exc


def verify_a2a_token(token: str) -> dict:
    """Verify an A2A bearer token against the configured API key.

    Mirrors the existing naming in the API module for backward compatibility.
    """
    try:
        return verify_token(token)
    except AuthError:
        return verify_api_key(token)
