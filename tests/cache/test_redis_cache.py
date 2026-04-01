"""Tests for cache/redis_cache.py.

Covers 4-tier distributed semantic cache with Redis L0.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cohezion.cache.redis_cache import RedisSemanticCache


@pytest.fixture
def mock_redis():
    with patch("redis.Redis") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.mark.asyncio
async def test_redis_cache_l0_hit(mock_redis):
    """[P0] Should hit L0 (Redis) first."""
    cache = RedisSemanticCache(enable_redis=True)
    
    # Setup Redis mock to return data
    cached_data = json.dumps({"response": "redis response"})
    mock_redis.get.return_value = cached_data.encode()
    
    result = await cache.get("test prompt")
    assert result == "redis response"
    assert cache.hits_l0 == 1
    mock_redis.get.assert_called_once()

@pytest.mark.asyncio
async def test_redis_cache_fallback_on_miss(mock_redis):
    """[P0] Should fallback to L1/L2 when L0 misses."""
    cache = RedisSemanticCache(enable_redis=True)
    mock_redis.get.return_value = None
    
    # L1 fallback (manually put into L1)
    await cache.put("test", "l1 response")
    # Reset mock after put
    mock_redis.get.reset_mock()
    mock_redis.get.return_value = None
    
    result = await cache.get("test")
    assert result == "l1 response"
    assert cache.hits_l0 == 0
    assert cache.misses_l0 == 1

@pytest.mark.asyncio
async def test_redis_cache_put(mock_redis):
    """[P0] Should put to both L1 and L0."""
    cache = RedisSemanticCache(enable_redis=True)
    await cache.put("prompt", "response")
    
    # Check Redis setex called
    mock_redis.setex.assert_called_once()
    args, kwargs = mock_redis.setex.call_args
    data = json.loads(args[2])
    assert data["response"] == "response"

def test_redis_cache_health_check(mock_redis):
    """[P0] Should return Redis health status."""
    cache = RedisSemanticCache(enable_redis=True)
    mock_redis.info.return_value = {"used_memory_human": "10MB", "connected_clients": 5}
    
    health = cache.health_check()
    assert health["redis_available"] is True
    assert health["memory_used"] == "10MB"
