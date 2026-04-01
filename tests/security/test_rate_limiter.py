"""Tests for security/rate_limiter.py.

Covers token bucket rate limiting logic.
"""

from __future__ import annotations

import time

from cohezion.security.rate_limiter import RateLimiter, TokenBucket


def test_token_bucket_consume():
    """[P0] Should consume tokens and deny when empty."""
    bucket = TokenBucket(tokens=2.0, last_update=time.time(), max_tokens=2, refill_rate=1.0)
    
    assert bucket.consume(1) is True
    assert bucket.consume(1) is True
    assert bucket.consume(1) is False

def test_rate_limiter_basic():
    """[P0] Should limit requests by key."""
    limiter = RateLimiter()
    limiter.set_limit("test", 2, 60)
    
    # First two allowed
    assert limiter.check("user1", "test").allowed is True
    assert limiter.check("user1", "test").allowed is True
    # Third blocked
    assert limiter.check("user1", "test").allowed is False
    
    # Different user allowed
    assert limiter.check("user2", "test").allowed is True

def test_rate_limiter_refill():
    """[P0] Should refill tokens over time."""
    limiter = RateLimiter()
    # 1 request per 0.1 second
    limiter.set_limit("fast", 10, 1)
    
    assert limiter.check("u1", "fast").allowed is True
    # Consume all
    for _ in range(9):
        limiter.check("u1", "fast")
    
    assert limiter.check("u1", "fast").allowed is False
    
    # Wait for refill (at least 0.1s for 1 token)
    time.sleep(0.15)
    assert limiter.check("u1", "fast").allowed is True
