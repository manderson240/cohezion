"""Tests for cache/cache_warmer.py.

Covers proactive cache warming from vault.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from cohezion.cache.cache_warmer import CacheWarmer


@pytest.mark.asyncio
async def test_cache_warmer_disabled_without_client():
    """[P0] Should not warm without MCP client."""
    mock_cache = MagicMock()
    warmer = CacheWarmer(semantic_cache=mock_cache, mcp_client=None)
    
    loaded = await warmer.warm_from_vault()
    assert loaded == 0
    mock_cache.put.assert_not_called()

@pytest.mark.asyncio
async def test_cache_warmer_success():
    """[P0] Should load patterns from vault into cache."""
    mock_cache = MagicMock()
    mock_cache.put = AsyncMock()
    
    mock_client = MagicMock()
    mock_client.vault_list.return_value = ["p1.json", "p2.json"]
    mock_client.vault_read.side_effect = [
        json.dumps({"prompt": "p1", "response": "r1"}),
        json.dumps({"prompt": "p2", "response": "r2"}),
    ]
    
    warmer = CacheWarmer(semantic_cache=mock_cache, mcp_client=mock_client)
    
    loaded = await warmer.warm_from_vault()
    
    assert loaded == 2
    assert mock_cache.put.call_count == 2
    mock_cache.put.assert_any_call(prompt="p1", response="r1")

@pytest.mark.asyncio
async def test_analyze_cache_effectiveness():
    """[P0] Should analyze cache performance."""
    mock_cache = MagicMock()
    mock_cache.get_stats.return_value = {
        "overall_hit_rate": 80.0,
        "l1_hit_rate": 50.0,
        "l2_hit_rate": 30.0,
        "l1_size": 10,
        "l2_size": 20,
    }
    
    warmer = CacheWarmer(semantic_cache=mock_cache)
    analysis = await warmer.analyze_cache_effectiveness()
    
    assert analysis["current_hit_rate"] == 80.0
    assert "Cache performance is good" in analysis["recommendation"]
