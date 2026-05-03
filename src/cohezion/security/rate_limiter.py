"""
Rate Limiter - Token bucket algorithm.

Provides:
- Per-IP rate limiting
- Per-API-key rate limiting
- Configurable limits per endpoint
- Retry-After headers
"""

import time
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit."""

    requests: int  # Max requests
    window_seconds: int  # Time window
    burst: int = 0  # Extra burst allowance


# Default limits by endpoint pattern
DEFAULT_LIMITS = {
    "/swarm/debate": RateLimitConfig(10, 60),  # 10/min
    "/knowledge": RateLimitConfig(60, 60),  # 60/min
    "/mcp": RateLimitConfig(100, 60),  # 100/min
    "default": RateLimitConfig(120, 60),  # 120/min
}


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    tokens: float
    last_update: float
    max_tokens: int
    refill_rate: float  # tokens per second

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        now = time.time()

        # Refill tokens based on elapsed time
        elapsed = now - self.last_update
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def time_until_available(self) -> float:
        """Seconds until at least 1 token is available."""
        if self.tokens >= 1:
            return 0.0
        return (1 - self.tokens) / self.refill_rate


@dataclass
class RateLimitResult:
    """Result of rate limit check."""

    allowed: bool
    remaining: int
    reset_after: float
    limit: int


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.

    Supports per-key and per-endpoint limiting.
    """

    def __init__(self):
        self._buckets: dict[str, TokenBucket] = {}
        self._limits = DEFAULT_LIMITS.copy()

    def _get_config(self, endpoint: str) -> RateLimitConfig:
        """Get config for an endpoint."""
        for pattern, config in self._limits.items():
            if pattern in endpoint:
                return config
        return self._limits["default"]

    def _get_bucket(self, key: str, config: RateLimitConfig) -> TokenBucket:
        """Get or create a bucket for a key."""
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(
                tokens=config.requests + config.burst,
                last_update=time.time(),
                max_tokens=config.requests + config.burst,
                refill_rate=config.requests / config.window_seconds,
            )
        return self._buckets[key]

    def check(
        self,
        key: str,
        endpoint: str = "default",
    ) -> RateLimitResult:
        """
        Check if a request is allowed.

        Args:
            key: Rate limit key (e.g., IP address, API key)
            endpoint: Endpoint being accessed

        Returns:
            RateLimitResult with allowed status and metadata
        """
        config = self._get_config(endpoint)
        bucket_key = f"{key}:{endpoint}"
        bucket = self._get_bucket(bucket_key, config)

        allowed = bucket.consume(1)

        return RateLimitResult(
            allowed=allowed,
            remaining=int(bucket.tokens),
            reset_after=bucket.time_until_available(),
            limit=config.requests,
        )

    def set_limit(self, endpoint: str, requests: int, window_seconds: int) -> None:
        """Set custom limit for an endpoint."""
        self._limits[endpoint] = RateLimitConfig(requests, window_seconds)

    def cleanup(self, max_age_seconds: int = 3600) -> int:
        """Remove old buckets to free memory."""
        now = time.time()
        to_remove = [
            key
            for key, bucket in self._buckets.items()
            if now - bucket.last_update > max_age_seconds
        ]
        for key in to_remove:
            del self._buckets[key]
        return len(to_remove)


# Singleton
_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def reset_rate_limiter() -> None:
    """Drop the rate-limiter singleton so the next call creates a fresh one.

    Test-only hook: token buckets accumulate across calls and the singleton
    survives between tests, which lets one test starve a key's bucket and
    cause a downstream guardrail to BLOCK a later test's request. Tests
    invoke this from ``conftest.reset_singletons`` to enforce isolation.
    """
    global _limiter
    _limiter = None
