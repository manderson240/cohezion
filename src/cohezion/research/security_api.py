"""Production hardening for ResearchAgent API.

Security, rate limiting, and production-ready features.
"""

from __future__ import annotations

import functools
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPBearer

logger = logging.getLogger(__name__)


# ============================================================================
# Rate Limiting
# ============================================================================


@dataclass
class RateLimitEntry:
    """Rate limit tracking for a client."""

    client_id: str
    requests: int
    window_start: float
    last_request: float


class RateLimiter:
    """Token bucket rate limiter for API endpoints.

    Tracks requests per client and enforces limits.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            burst_size: Max burst of requests allowed
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        self._clients: dict[str, RateLimitEntry] = {}
        self._cleanup_interval = 3600  # 1 hour
        self._last_cleanup = time.time()

    def _cleanup_old_entries(self) -> None:
        """Remove old entries to prevent memory leaks."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = now - 3600  # 1 hour ago
        expired = [
            client_id for client_id, entry in self._clients.items() if entry.last_request < cutoff
        ]
        for client_id in expired:
            del self._clients[client_id]

        self._last_cleanup = now
        logger.debug(f"Rate limiter cleaned up {len(expired)} old entries")

    def is_allowed(self, client_id: str) -> tuple[bool, dict[str, Any]]:
        """Check if request is allowed under rate limit.

        Args:
            client_id: Unique client identifier

        Returns:
            (allowed, rate_limit_info)
        """
        self._cleanup_old_entries()

        now = time.time()
        minute_ago = now - 60
        _hour_ago = now - 3600

        entry = self._clients.get(client_id)

        if not entry:
            # First request from this client
            self._clients[client_id] = RateLimitEntry(
                client_id=client_id,
                requests=1,
                window_start=now,
                last_request=now,
            )
            return True, {
                "limit": self.requests_per_minute,
                "remaining": self.requests_per_minute - 1,
                "reset": int(now + 60),
            }

        # Check if we need to reset windows
        if entry.window_start < minute_ago:
            entry.requests = 0
            entry.window_start = now

        # Check limits
        if entry.requests >= self.requests_per_hour:
            # Hourly limit exceeded
            reset_time = int(entry.window_start + 3600)
            return False, {
                "limit": self.requests_per_hour,
                "remaining": 0,
                "reset": reset_time,
                "retry_after": max(0, reset_time - int(now)),
            }

        if entry.requests >= self.requests_per_minute and entry.window_start > minute_ago:
            # Minute limit exceeded
            reset_time = int(entry.window_start + 60)
            return False, {
                "limit": self.requests_per_minute,
                "remaining": 0,
                "reset": reset_time,
                "retry_after": max(0, reset_time - int(now)),
            }

        # Allow request
        entry.requests += 1
        entry.last_request = now

        remaining = min(
            self.requests_per_minute - entry.requests,
            self.requests_per_hour - entry.requests,
        )

        return True, {
            "limit": self.requests_per_minute,
            "remaining": max(0, remaining),
            "reset": int(entry.window_start + 60),
        }

    def get_limit_headers(self, client_id: str) -> dict[str, str]:
        """Get rate limit headers for response.

        Args:
            client_id: Client identifier

        Returns:
            HTTP headers dict
        """
        allowed, info = self.is_allowed(client_id)

        headers = {
            "X-RateLimit-Limit": str(info["limit"]),
            "X-RateLimit-Remaining": str(info["remaining"]),
            "X-RateLimit-Reset": str(info["reset"]),
        }

        if not allowed and "retry_after" in info:
            headers["Retry-After"] = str(info["retry_after"])

        return headers


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_id(request: Request) -> str:
    """Extract client ID from request.

    Uses X-Forwarded-For if behind proxy, otherwise REMOTE_ADDR.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
) -> Callable:
    """Decorator to apply rate limiting to endpoints.

    Args:
        requests_per_minute: Max requests per minute
        requests_per_hour: Max requests per hour

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = kwargs.get("request")
            if not request and args:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                raise HTTPException(status_code=500, detail="Request not found")

            client_id = get_client_id(request)

            # Check rate limit
            allowed, info = rate_limiter.is_allowed(client_id)

            if not allowed:
                retry_after = info.get("retry_after", 60)
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(info["reset"]),
                    },
                )

            # Store rate limit info for response headers
            request.state.rate_limit_info = info

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Authentication
# ============================================================================

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


class APIKeyManager:
    """Simple API key management for research endpoints.

    In production: Use proper vault storage (MCP vault or similar).
    """

    def __init__(self, keys_file: Path | None = None):
        """Initialize API key manager.

        Args:
            keys_file: Path to keys file (default: data/api_keys.json)
        """
        self.keys_file = keys_file or Path("data/api_keys.json")
        self.keys_file.parent.mkdir(parents=True, exist_ok=True)
        self._keys: dict[str, dict[str, Any]] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """Load keys from file."""
        try:
            import json

            if self.keys_file.exists():
                with open(self.keys_file) as f:
                    self._keys = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load API keys: {e}")
            self._keys = {}

    def _save_keys(self) -> None:
        """Save keys to file."""
        try:
            import json

            with open(self.keys_file, "w") as f:
                json.dump(self._keys, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")

    def create_key(
        self,
        name: str,
        scopes: list[str] | None = None,
    ) -> str:
        """Create new API key.

        Args:
            name: Key name/description
            scopes: List of allowed scopes

        Returns:
            API key (store securely!)
        """
        key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        self._keys[key_hash] = {
            "name": name,
            "scopes": scopes or ["research:read", "research:write"],
            "created": datetime.now().isoformat(),
            "last_used": None,
            "usage_count": 0,
            "active": True,
        }

        self._save_keys()
        logger.info(f"Created API key: {name}")

        return key

    def validate_key(self, key: str) -> tuple[bool, dict[str, Any] | None]:
        """Validate API key.

        Args:
            key: API key to validate

        Returns:
            (is_valid, key_info)
        """
        if not key:
            return False, None

        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_info = self._keys.get(key_hash)

        if not key_info:
            return False, None

        if not key_info.get("active", True):
            return False, None

        # Update usage
        key_info["last_used"] = datetime.now().isoformat()
        key_info["usage_count"] = key_info.get("usage_count", 0) + 1
        self._save_keys()

        return True, key_info

    def revoke_key(self, key_hash: str) -> bool:
        """Revoke an API key.

        Args:
            key_hash: Hash of key to revoke

        Returns:
            True if revoked
        """
        if key_hash in self._keys:
            self._keys[key_hash]["active"] = False
            self._save_keys()
            logger.info(f"Revoked API key: {key_hash[:8]}...")
            return True
        return False


# Global API key manager
api_key_manager = APIKeyManager()


async def verify_api_key(
    api_key: str = Security(api_key_header),
    request: Request = None,
) -> dict[str, Any]:
    """Verify API key from request.

    Args:
        api_key: API key from header
        request: FastAPI request

    Returns:
        Key info dict

    Raises:
        HTTPException: If key is invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    is_valid, key_info = api_key_manager.validate_key(api_key)

    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid or revoked API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Store key info on request for later use
    if request:
        request.state.api_key_info = key_info

    return key_info


def require_scope(required_scope: str) -> Callable:
    """Decorator to require specific scope.

    Args:
        required_scope: Required scope (e.g., "research:write")

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request in args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                raise HTTPException(status_code=500, detail="Request not found")

            key_info = getattr(request.state, "api_key_info", None)
            if not key_info:
                raise HTTPException(status_code=401, detail="API key not verified")

            scopes = key_info.get("scopes", [])
            if required_scope not in scopes:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient scope. Required: {required_scope}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Security Utilities
# ============================================================================


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent injection attacks.

    Args:
        value: Input string
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""

    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length]

    # Remove null bytes
    value = value.replace("\x00", "")

    return value


def validate_session_id(session_id: str) -> bool:
    """Validate session ID format.

    Args:
        session_id: Session ID to validate

    Returns:
        True if valid
    """
    if not session_id:
        return False

    # Should be ISO timestamp format or UUID-like
    # Allow alphanumeric, hyphens, colons, dots
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:")
    return all(c in allowed for c in session_id) and len(session_id) < 100


# ============================================================================
# Health Checks
# ============================================================================


class HealthChecker:
    """Health check system for research endpoints."""

    def __init__(self):
        """Initialize health checker."""
        self.checks: dict[str, Callable[[], tuple[bool, str]]] = {}
        self.start_time = time.time()

    def register_check(
        self,
        name: str,
        check_func: Callable[[], tuple[bool, str]],
    ) -> None:
        """Register a health check.

        Args:
            name: Check name
            check_func: Function returning (healthy, message)
        """
        self.checks[name] = check_func

    def check_all(self) -> dict[str, Any]:
        """Run all health checks.

        Returns:
            Health status dict
        """
        results = {}
        healthy_count = 0

        for name, check_func in self.checks.items():
            try:
                is_healthy, message = check_func()
                results[name] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "message": message,
                }
                if is_healthy:
                    healthy_count += 1
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "message": str(e),
                }

        uptime = time.time() - self.start_time

        return {
            "status": "healthy" if healthy_count == len(self.checks) else "degraded",
            "uptime_seconds": int(uptime),
            "checks": results,
            "timestamp": datetime.now().isoformat(),
        }


# Global health checker
health_checker = HealthChecker()


# Register default checks
def _check_disk_space() -> tuple[bool, str]:
    """Check available disk space."""
    import shutil

    total, used, free = shutil.disk_usage("/")
    free_gb = free / (1024**3)
    if free_gb < 1:
        return False, f"Low disk space: {free_gb:.1f}GB free"
    return True, f"Disk OK: {free_gb:.1f}GB free"


def _check_memory() -> tuple[bool, str]:
    """Check available memory."""
    try:
        import psutil

        memory = psutil.virtual_memory()
        if memory.percent > 90:
            return False, f"High memory usage: {memory.percent}%"
        return True, f"Memory OK: {memory.percent}% used"
    except ImportError:
        return True, "Memory check skipped (psutil not installed)"


health_checker.register_check("disk", _check_disk_space)
health_checker.register_check("memory", _check_memory)


# ============================================================================
# Audit Logging
# ============================================================================


class AuditLogger:
    """Audit logging for security events."""

    def __init__(self, log_file: Path | None = None):
        """Initialize audit logger.

        Args:
            log_file: Path to audit log
        """
        self.log_file = log_file or Path("data/audit/research_api.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: str,
        client_id: str,
        details: dict[str, Any],
    ) -> None:
        """Log security event.

        Args:
            event_type: Type of event
            client_id: Client identifier
            details: Event details
        """
        import json

        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "client_id": client_id,
            "details": details,
        }

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def log_api_call(
        self,
        endpoint: str,
        method: str,
        client_id: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """Log API call.

        Args:
            endpoint: API endpoint
            method: HTTP method
            client_id: Client identifier
            status_code: HTTP status code
            duration_ms: Request duration
        """
        self.log_event(
            "api_call",
            client_id,
            {
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )


# Global audit logger
audit_logger = AuditLogger()
