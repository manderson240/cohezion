"""Integration tests for cache warmer with vault execution history.

Tests verify that CacheWarmer properly:
- Queries vault for execution traces
- Filters by coherence and success
- Loads high-coherence executions into cache
- Handles edge cases (no data, low coherence, etc.)
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cohezion.cache.cache_warmer import CacheWarmer
from cohezion.cache.semantic_cache import SemanticCache


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client with vault methods."""
    client = MagicMock()
    client.vault_list = MagicMock(return_value=[])
    client.vault_read = MagicMock(return_value="{}")
    client.vault_write = MagicMock()
    client.vault_search = MagicMock(return_value=[])
    return client


@pytest.fixture
def mock_semantic_cache():
    """Create mock semantic cache."""
    cache = MagicMock(spec=SemanticCache)
    cache.put = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.get_stats = MagicMock(return_value={
        "overall_hit_rate": 0.3,
        "l1_hit_rate": 0.2,
        "l2_hit_rate": 0.4,
        "l1_size": 100,
        "l2_size": 200,
    })
    return cache


class TestCacheWarmerHistory:
    """Tests for warm_from_history method."""

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_warm_from_history_no_mcp(self, mock_semantic_cache):
        """Test that warming is skipped without MCP client."""
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=None)
        result = await warmer.warm_from_history("test_skill")
        assert result == 0

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_warm_from_history_no_traces(self, mock_mcp_client, mock_semantic_cache):
        """Test handling of no execution traces."""
        mock_mcp_client.vault_list.return_value = []
        
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=mock_mcp_client)
        result = await warmer.warm_from_history("test_skill")
        
        assert result == 0
        mock_mcp_client.vault_list.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_warm_from_history_loads_high_coherence(self, mock_mcp_client, mock_semantic_cache):
        """Test that high-coherence executions are loaded."""
        # Setup mock trace files
        mock_mcp_client.vault_list.return_value = [
            "execution_traces/test_skill/1234567890_exec.json",
            "execution_traces/test_skill/1234567891_exec.json",
        ]
        
        # Mock trace content - one high coherence, one low
        def mock_read(path):
            if "1234567890" in path:
                return json.dumps({
                    "task_description": "Write a function to sort",
                    "output_summary": "Here's the sorted list",
                    "coherence": 0.85,
                    "success": True,
                })
            else:
                return json.dumps({
                    "task_description": "Write another function",
                    "output_summary": "Another output",
                    "coherence": 0.5,  # Below threshold
                    "success": True,
                })
        
        mock_mcp_client.vault_read.side_effect = mock_read
        
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=mock_mcp_client)
        result = await warmer.warm_from_history("test_skill", min_coherence=0.7)
        
        # Only high-coherence execution should be loaded
        assert result == 1
        mock_semantic_cache.put.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_warm_from_history_filters_failed_executions(self, mock_mcp_client, mock_semantic_cache):
        """Test that failed executions are not loaded."""
        mock_mcp_client.vault_list.return_value = [
            "execution_traces/test_skill/1234567890_exec.json",
        ]
        
        # Mock failed execution
        mock_mcp_client.vault_read.return_value = json.dumps({
            "task_description": "Write a function",
            "output_summary": "Error occurred",
            "coherence": 0.9,  # High coherence but failed
            "success": False,
        })
        
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=mock_mcp_client)
        result = await warmer.warm_from_history("test_skill")
        
        # Failed execution should not be loaded
        assert result == 0
        mock_semantic_cache.put.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_warm_from_history_sorts_by_coherence(self, mock_mcp_client, mock_semantic_cache):
        """Test that executions are sorted by coherence (highest first)."""
        mock_mcp_client.vault_list.return_value = [
            "execution_traces/test_skill/trace1.json",
            "execution_traces/test_skill/trace2.json",
            "execution_traces/test_skill/trace3.json",
        ]
        
        # Mock traces with different coherence scores
        def mock_read(path):
            if "trace1" in path:
                return json.dumps({
                    "task_description": "Task 1",
                    "output_summary": "Output 1",
                    "coherence": 0.75,
                    "success": True,
                })
            elif "trace2" in path:
                return json.dumps({
                    "task_description": "Task 2",
                    "output_summary": "Output 2",
                    "coherence": 0.95,
                    "success": True,
                })
            else:
                return json.dumps({
                    "task_description": "Task 3",
                    "output_summary": "Output 3",
                    "coherence": 0.85,
                    "success": True,
                })
        
        mock_mcp_client.vault_read.side_effect = mock_read
        
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=mock_mcp_client)
        result = await warmer.warm_from_history("test_skill")
        
        assert result == 3
        # Verify put was called 3 times
        assert mock_semantic_cache.put.call_count == 3
        
        # First call should be highest coherence (0.95)
        first_call = mock_semantic_cache.put.call_args_list[0]
        assert first_call.kwargs["metadata"]["coherence"] == 0.95


class TestCacheWarmerRecentExecutions:
    """Tests for warm_from_recent_executions method."""

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_warm_from_recent_no_mcp(self, mock_semantic_cache):
        """Test that warming is skipped without MCP client."""
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=None)
        result = await warmer.warm_from_recent_executions()
        assert result == 0

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_warm_from_recent_no_traces(self, mock_mcp_client, mock_semantic_cache):
        """Test handling of no execution traces."""
        mock_mcp_client.vault_list.return_value = []
        
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=mock_mcp_client)
        result = await warmer.warm_from_recent_executions()
        
        assert result == 0

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_warm_from_recent_respects_limit(self, mock_mcp_client, mock_semantic_cache):
        """Test that limit is respected."""
        # Create 10 trace files
        mock_mcp_client.vault_list.return_value = [
            f"execution_traces/skill{i}/trace.json" for i in range(10)
        ]
        
        # All have high coherence
        def mock_read(path):
            return json.dumps({
                "task_description": "Task",
                "output_summary": "Output",
                "coherence": 0.9,
                "success": True,
                "end_time": "2026-04-19T12:00:00",
                "skill_name": "test",
            })
        
        mock_mcp_client.vault_read.side_effect = mock_read
        
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=mock_mcp_client)
        result = await warmer.warm_from_recent_executions(limit=5)
        
        # Should only load 5 despite 10 available
        assert result == 5
        assert mock_semantic_cache.put.call_count == 5

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_warm_from_recent_sorts_by_time_then_coherence(self, mock_mcp_client, mock_semantic_cache):
        """Test sorting by recency then coherence."""
        mock_mcp_client.vault_list.return_value = [
            "execution_traces/skill1/trace1.json",
            "execution_traces/skill2/trace2.json",
        ]
        
        def mock_read(path):
            if "trace1" in path:
                # Older but higher coherence
                return json.dumps({
                    "task_description": "Older task",
                    "output_summary": "Older output",
                    "coherence": 0.95,
                    "success": True,
                    "end_time": "2026-04-18T12:00:00",
                    "skill_name": "skill1",
                })
            else:
                # Newer but lower coherence
                return json.dumps({
                    "task_description": "Newer task",
                    "output_summary": "Newer output",
                    "coherence": 0.8,
                    "success": True,
                    "end_time": "2026-04-19T12:00:00",
                    "skill_name": "skill2",
                })
        
        mock_mcp_client.vault_read.side_effect = mock_read
        
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=mock_mcp_client)
        result = await warmer.warm_from_recent_executions(limit=2)
        
        assert result == 2
        # First should be newer (trace2)
        first_call = mock_semantic_cache.put.call_args_list[0]
        assert "Newer task" in first_call.kwargs["prompt"]


class TestCacheWarmerVault:
    """Tests for warm_from_vault method."""

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_warm_from_vault_loads_patterns(self, mock_mcp_client, mock_semantic_cache):
        """Test loading patterns from vault."""
        mock_mcp_client.vault_list.return_value = [
            "cache_patterns/pattern1.json",
            "cache_patterns/pattern2.json",
        ]
        
        def mock_read(path):
            if "pattern1" in path:
                return json.dumps({
                    "prompt": "Test prompt 1",
                    "response": "Test response 1",
                })
            else:
                return json.dumps({
                    "prompt": "Test prompt 2",
                    "response": "Test response 2",
                })
        
        mock_mcp_client.vault_read.side_effect = mock_read
        
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=mock_mcp_client)
        result = await warmer.warm_from_vault(limit=10)
        
        assert result == 2
        assert mock_semantic_cache.put.call_count == 2


class TestCacheWarmerTemplateMatch:
    """Tests for find_template_match method."""

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_find_template_match_l1_exact(self, mock_semantic_cache):
        """Test L1 exact match."""
        mock_semantic_cache.get = AsyncMock(return_value="Cached response")
        
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=None)
        result = await warmer.find_template_match("Test query")
        
        assert result is not None
        assert result["response"] == "Cached response"
        assert result["similarity"] == 1.0
        assert result["source"] == "L1_exact"

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_find_template_match_no_match(self, mock_semantic_cache):
        """Test when no match found."""
        mock_semantic_cache.get = AsyncMock(return_value=None)
        
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=None)
        result = await warmer.find_template_match("Test query")
        
        assert result is None


class TestCacheWarmerAnalyze:
    """Tests for analyze_cache_effectiveness method."""

    @pytest.mark.fast
    def test_analyze_cache_effectiveness(self, mock_semantic_cache):
        """Test cache analysis."""
        warmer = CacheWarmer(mock_semantic_cache, mcp_client=None)
        result = warmer.analyze_cache_effectiveness()
        
        assert "current_hit_rate" in result
        assert "l1_hit_rate" in result
        assert "l2_hit_rate" in result
        assert "cache_fullness_l1" in result
        assert "cache_fullness_l2" in result
        assert "recommendation" in result
        
        # Check calculation
        assert result["cache_fullness_l1"] == 100 / 512 * 100
        assert result["cache_fullness_l2"] == 200 / 1024 * 100
