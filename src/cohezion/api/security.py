import functools
import logging
import time
from collections.abc import Callable

from fastapi import HTTPException, Request


logger = logging.getLogger(__name__)

# Basic in-memory rate limiter for demo/internal use
# For production, this would use Redis or SurrealDB
_rate_limits = {}


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

            client_ip = request.client.host
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
    Currently a placeholder that checks for an 'Authorization' header.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request or not isinstance(request, Request):
            # For internal calls without Request objects, we skip for now
            return await func(*args, **kwargs)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.error(f"Unauthorized access attempt to {func.__name__}")
            raise HTTPException(status_code=401, detail="Missing authorization header")

        # Actual token validation logic would go here
        return await func(*args, **kwargs)

    return wrapper
