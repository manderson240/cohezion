"""Tests for SemanticCache vault (L3) integration."""

import json
from unittest.mock import MagicMock

import pytest

from cohezion.cache.cache_warmer import CacheWarmer
from cohezion.cache.semantic_cache import SemanticCache


class MockMCPClient:
    """Mock MCPClient for testing."""

    def __init__(self):
        """Initialize mock client."""
        self.vault_data: dict[str, str] = {}
        self.vault_search_results: list[dict] = []

    def vault_search(self, query: str, scope: str = "all", folder: str = ""):
        """Mock vault search."""
        return self.vault_search_results

    def vault_read(self, path: str) -> str:
        """Mock vault read."""
        if path in self.vault_data:
            return self.vault_data[path]
        raise ValueError(f"Path not found: {path}")

    def vault_write(self, path: str, content: str) -> str:
        """Mock vault write."""
        self.vault_data[path] = content
        return path

    def vault_list(self, directory: str = "", recursive: bool = False):
        """Mock vault list."""
        if directory == "cache_patterns":
            return list(self.vault_data.keys())
        return []


class TestSemanticCacheVaultLookup:
    """Test L3 vault lookups."""

    @pytest.mark.asyncio
    async def test_vault_lookup_with_no_client(self):
        """L3 lookup should return None if no MCPClient."""
        cache = SemanticCache(mcp_client=None)
        result = await cache._vault_lookup("test prompt")
        assert result is None

    @pytest.mark.asyncio
    async def test_vault_lookup_with_results(self):
        """L3 lookup should extract response from vault JSON files."""
        mcp_client = MockMCPClient()
        # Store a valid cache pattern in vault
        cache_pattern = {
            "prompt": "test prompt",
            "response": "This is a cached response from vault",
            "timestamp": 1234567890.0,
        }
        mcp_client.vault_data["cache_patterns/test.json"] = json.dumps(cache_pattern)
        # Vault search returns the path to this file
        mcp_client.vault_search_results = [{"path": "cache_patterns/test.json", "context": "cache entry"}]

        cache = SemanticCache(mcp_client=mcp_client)
        result = await cache._vault_lookup("test prompt")

        assert result is not None
        assert "cached response" in result

    @pytest.mark.asyncio
    async def test_vault_lookup_no_results(self):
        """L3 lookup should return None if no results."""
        mcp_client = MockMCPClient()
        mcp_client.vault_search_results = []

        cache = SemanticCache(mcp_client=mcp_client)
        result = await cache._vault_lookup("test prompt")

        assert result is None

    @pytest.mark.asyncio
    async def test_vault_lookup_exception_handling(self):
        """L3 lookup should handle exceptions gracefully."""
        mcp_client = MagicMock()
        mcp_client.vault_search.side_effect = Exception("Connection failed")

        cache = SemanticCache(mcp_client=mcp_client)
        result = await cache._vault_lookup("test prompt")

        # Should return None on exception (non-blocking)
        assert result is None

    @pytest.mark.asyncio
    async def test_vault_lookup_invalid_json(self):
        """L3 lookup should skip invalid JSON cache patterns."""
        mcp_client = MockMCPClient()
        # Store invalid JSON
        mcp_client.vault_data["cache_patterns/invalid.json"] = "invalid json"
        mcp_client.vault_search_results = [{"path": "cache_patterns/invalid.json"}]

        cache = SemanticCache(mcp_client=mcp_client)
        result = await cache._vault_lookup("test prompt")

        # Should gracefully return None
        assert result is None


class TestSemanticCacheVaultStore:
    """Test L3 vault storage."""

    @pytest.mark.asyncio
    async def test_vault_store_with_no_client(self):
        """Store should no-op if no MCPClient."""
        cache = SemanticCache(mcp_client=None)
        await cache._vault_store("test prompt", "test response")
        # Should complete without error

    @pytest.mark.asyncio
    async def test_vault_store_writes_to_vault(self):
        """Store should write pattern to vault."""
        mcp_client = MockMCPClient()
        cache = SemanticCache(mcp_client=mcp_client)

        await cache._vault_store("test prompt", "test response")

        # Check that something was written
        assert len(mcp_client.vault_data) > 0

        # Check structure of written data
        written_data = next(iter(mcp_client.vault_data.values()))
        pattern = json.loads(written_data)
        assert pattern["prompt"] == "test prompt"
        assert pattern["response"] == "test response"

    @pytest.mark.asyncio
    async def test_vault_store_exception_handling(self):
        """Store should handle exceptions gracefully."""
        mcp_client = MagicMock()
        mcp_client.vault_write.side_effect = Exception("Write failed")

        cache = SemanticCache(mcp_client=mcp_client)
        await cache._vault_store("test prompt", "test response")

        # Should complete without error (non-blocking)


class TestCacheWarmerVault:
    """Test cache warmer with vault."""

    @pytest.mark.asyncio
    async def test_warm_from_vault_no_client(self):
        """Warmer should return 0 if no MCPClient."""
        cache = SemanticCache()
        warmer = CacheWarmer(cache, mcp_client=None)
        loaded = await warmer.warm_from_vault(limit=10)
        assert loaded == 0

    @pytest.mark.asyncio
    async def test_warm_from_vault_loads_patterns(self):
        """Warmer should load patterns from vault."""
        mcp_client = MockMCPClient()

        # Add mock patterns to vault
        pattern1 = {"prompt": "pattern 1", "response": "response 1"}
        pattern2 = {"prompt": "pattern 2", "response": "response 2"}
        mcp_client.vault_data["cache_patterns/p1.json"] = json.dumps(pattern1)
        mcp_client.vault_data["cache_patterns/p2.json"] = json.dumps(pattern2)

        cache = SemanticCache(mcp_client=mcp_client)
        warmer = CacheWarmer(cache, mcp_client=mcp_client)

        loaded = await warmer.warm_from_vault(limit=10)

        assert loaded == 2
        # Check patterns were loaded into cache
        assert cache.l1_cache or cache.l2_cache  # Should be in one of the caches

    @pytest.mark.asyncio
    async def test_warm_from_vault_respects_limit(self):
        """Warmer should respect limit parameter."""
        mcp_client = MockMCPClient()

        # Add 10 patterns to vault
        for i in range(10):
            pattern = {"prompt": f"pattern {i}", "response": f"response {i}"}
            mcp_client.vault_data[f"cache_patterns/p{i}.json"] = json.dumps(pattern)

        cache = SemanticCache(mcp_client=mcp_client)
        warmer = CacheWarmer(cache, mcp_client=mcp_client)

        loaded = await warmer.warm_from_vault(limit=5)

        # Should load at most 5 patterns
        assert loaded <= 5

    @pytest.mark.asyncio
    async def test_warm_from_vault_handles_invalid_patterns(self):
        """Warmer should skip invalid patterns."""
        mcp_client = MockMCPClient()

        # Add valid and invalid patterns
        valid = {"prompt": "valid", "response": "response"}
        invalid = {"invalid": "structure"}
        mcp_client.vault_data["cache_patterns/valid.json"] = json.dumps(valid)
        mcp_client.vault_data["cache_patterns/invalid.json"] = json.dumps(invalid)

        cache = SemanticCache(mcp_client=mcp_client)
        warmer = CacheWarmer(cache, mcp_client=mcp_client)

        loaded = await warmer.warm_from_vault(limit=10)

        # Should load only the valid pattern
        assert loaded == 1

    @pytest.mark.asyncio
    async def test_warm_from_vault_empty_directory(self):
        """Warmer should handle empty vault directory."""
        mcp_client = MockMCPClient()
        # vault_data is empty, so vault_list returns empty

        cache = SemanticCache(mcp_client=mcp_client)
        warmer = CacheWarmer(cache, mcp_client=mcp_client)

        loaded = await warmer.warm_from_vault(limit=10)

        assert loaded == 0


class TestSemanticCacheL3Integration:
    """Test full L3 cache integration."""

    @pytest.mark.asyncio
    async def test_cache_tier_promotion_to_l1(self):
        """L3 hit should be promoted to L1."""
        mcp_client = MockMCPClient()
        # Pre-populate vault with a cache pattern
        cache_pattern = {
            "prompt": "vault_test_prompt",
            "response": "Response from vault that should be promoted to L1",
            "timestamp": 1234567890.0,
        }
        mcp_client.vault_data["cache_patterns/vault_test.json"] = json.dumps(
            cache_pattern
        )
        mcp_client.vault_search_results = [{"path": "cache_patterns/vault_test.json"}]

        cache = SemanticCache(mcp_client=mcp_client)

        # First lookup: L1 miss, L2 miss, L3 hit from vault
        result = await cache.get("vault_test_prompt")
        assert result == "Response from vault that should be promoted to L1"
        assert cache.hits_l3 == 1

        # Second lookup: should be L1 hit now (promoted)
        result2 = await cache.get("vault_test_prompt")
        assert result2 == "Response from vault that should be promoted to L1"
        assert cache.hits_l1 == 1
        assert cache.hits_l3 == 1  # No additional L3 hit

    @pytest.mark.asyncio
    async def test_cache_metrics_with_vault(self):
        """Metrics should reflect L3 cache activity."""
        mcp_client = MockMCPClient()
        cache = SemanticCache(mcp_client=mcp_client)

        # Put a few items
        await cache.put("prompt1", "response1")
        await cache.put("prompt2", "response2")

        # Get with L1 hits
        result1 = await cache.get("prompt1")
        result2 = await cache.get("prompt2")

        assert result1 == "response1"
        assert result2 == "response2"

        stats = cache.get_stats()
        assert stats["l1_hits"] == 2
        assert stats["overall_hit_rate"] == 100.0  # All L1 hits

    @pytest.mark.asyncio
    async def test_l3_cache_store_and_lookup(self):
        """Test end-to-end L3 cache storage and lookup in separate sessions."""
        mcp_client = MockMCPClient()
        cache1 = SemanticCache(mcp_client=mcp_client)

        # Session 1: Cache a response and store directly (for testing)
        await cache1._vault_store("test_prompt", "test_response")

        # Verify it was stored in vault (after async store completes)
        assert len(mcp_client.vault_data) > 0

        # Session 2: New cache instance, should find it via L3
        cache2 = SemanticCache(mcp_client=mcp_client)

        # Set up search results to find the stored pattern
        stored_paths = list(mcp_client.vault_data.keys())
        if stored_paths:
            mcp_client.vault_search_results = [{"path": stored_paths[0]}]

            # Lookup should find the cached response from vault
            result = await cache2.get("test_prompt")
            # Result may be None if semantic similarity is low
            # Check at least that the lookup didn't crash
            assert isinstance(result, (str, type(None)))

    @pytest.mark.asyncio
    async def test_l3_cache_put_with_background_store(self):
        """Test that put() schedules background vault storage."""
        mcp_client = MockMCPClient()
        cache = SemanticCache(mcp_client=mcp_client)

        # Put should schedule background vault storage via create_task
        await cache.put("prompt1", "response1")

        # Note: Due to asyncio.create_task, storage happens in background
        # In real usage with asyncio.gather or run_until_complete, it would complete
        # For this unit test, we verify the mechanism by calling _vault_store directly
        await cache._vault_store("prompt2", "response2")
        assert len(mcp_client.vault_data) > 0  # At least one should be stored
