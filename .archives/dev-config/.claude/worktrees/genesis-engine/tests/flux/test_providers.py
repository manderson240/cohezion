"""Tests for FLUX provider implementations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cohezion.flux.providers.cache_flux import CacheFlux
from cohezion.flux.providers.history_flux import HistoryFlux
from cohezion.flux.providers.surreal_flux import SurrealFlux
from cohezion.flux.providers.tool_flux import ToolFlux
from cohezion.flux.providers.vault_flux import VaultFlux
from cohezion.flux.types import FluxSource


class TestVaultFlux:
    @pytest.mark.asyncio
    async def test_returns_flux_blocks_from_vault(self):
        mock_vault_logger = MagicMock()
        mock_vault_logger.get_experience_guidance = MagicMock(
            return_value={
                "guidance": "Use template X for deployment tasks",
                "similar_tasks": ["deploy-api-v2", "deploy-worker"],
            }
        )
        provider = VaultFlux(vault_logger=mock_vault_logger)
        blocks = await provider.get_context("deploy API")
        assert len(blocks) >= 1
        assert blocks[0].source == FluxSource.VAULT
        assert "template X" in blocks[0].content

    @pytest.mark.asyncio
    async def test_empty_guidance_returns_empty(self):
        mock_vault_logger = MagicMock()
        mock_vault_logger.get_experience_guidance = MagicMock(return_value={})
        provider = VaultFlux(vault_logger=mock_vault_logger)
        blocks = await provider.get_context("unknown task")
        assert blocks == []


class TestSurrealFlux:
    @pytest.mark.asyncio
    async def test_returns_blocks_from_surreal_query(self):
        mock_client = AsyncMock()
        mock_client.query_similar = AsyncMock(return_value=[
            {"content": "prior run data", "score": 0.85, "id": "node:1"},
            {"content": "related concept", "score": 0.72, "id": "node:2"},
        ])
        provider = SurrealFlux(surreal_client=mock_client)
        blocks = await provider.get_context("research patterns", top_k=2)
        assert len(blocks) == 2
        assert blocks[0].source == FluxSource.SURREAL
        assert blocks[0].relevance_score == 0.85

    @pytest.mark.asyncio
    async def test_handles_empty_results(self):
        mock_client = AsyncMock()
        mock_client.query_similar = AsyncMock(return_value=[])
        provider = SurrealFlux(surreal_client=mock_client)
        blocks = await provider.get_context("nothing matches")
        assert blocks == []


class TestToolFlux:
    @pytest.mark.asyncio
    async def test_returns_blocks_from_capability_search(self):
        mock_cap = MagicMock()
        mock_cap.find = MagicMock(return_value=[
            MagicMock(name="web_search", description="Search the web", score=0.9, type="mcp"),
            MagicMock(name="arxiv_search", description="Search arxiv papers", score=0.8, type="skill"),
        ])
        provider = ToolFlux(capability_registry=mock_cap)
        blocks = await provider.get_context("find research papers")
        assert len(blocks) == 2
        assert blocks[0].source == FluxSource.TOOL


class TestHistoryFlux:
    @pytest.mark.asyncio
    async def test_records_and_retrieves(self):
        provider = HistoryFlux(max_entries=10)
        provider.record("Executed deploy task successfully", {"task": "deploy"})
        provider.record("Ran test suite, 52 passed", {"task": "test"})

        blocks = await provider.get_context("deploy")
        assert len(blocks) >= 1
        assert blocks[0].source == FluxSource.HISTORY

    @pytest.mark.asyncio
    async def test_empty_history_returns_empty(self):
        provider = HistoryFlux()
        blocks = await provider.get_context("anything")
        assert blocks == []

    def test_max_entries_enforced(self):
        provider = HistoryFlux(max_entries=3)
        for i in range(5):
            provider.record(f"entry {i}", {})
        assert len(provider._entries) == 3


class TestCacheFlux:
    @pytest.mark.asyncio
    async def test_returns_blocks_from_cache(self):
        mock_cache = MagicMock()
        mock_cache.search_l2 = MagicMock(return_value=[
            {"content": "cached result A", "score": 0.95},
            {"content": "cached result B", "score": 0.80},
        ])
        provider = CacheFlux(semantic_cache=mock_cache)
        blocks = await provider.get_context("similar query")
        assert len(blocks) == 2
        assert blocks[0].source == FluxSource.CACHE
        assert blocks[0].relevance_score == 0.95

    @pytest.mark.asyncio
    async def test_handles_no_cache(self):
        provider = CacheFlux(semantic_cache=None)
        blocks = await provider.get_context("test")
        assert blocks == []
