"""Tests for FluxAggregator — unified context query."""

from __future__ import annotations

import pytest

from cohezion.flux.aggregator import FluxAggregator
from cohezion.flux.provider import FluxProvider
from cohezion.flux.types import FluxBlock, FluxContext, FluxSource


class MockProvider(FluxProvider):
    def __init__(self, source: FluxSource, blocks: list[FluxBlock]) -> None:
        self.source = source
        self._blocks = blocks

    async def get_context(self, query, top_k=5, **kwargs):
        return self._blocks[:top_k]


class TestFluxAggregator:
    @pytest.mark.asyncio
    async def test_single_provider(self):
        blocks = [FluxBlock(content="vault result", source=FluxSource.VAULT, relevance_score=0.9)]
        agg = FluxAggregator([MockProvider(FluxSource.VAULT, blocks)])
        ctx = await agg.get_context("test query")
        assert len(ctx.blocks) == 1
        assert ctx.blocks[0].content == "vault result"

    @pytest.mark.asyncio
    async def test_multiple_providers_merged(self):
        vault_blocks = [FluxBlock(content="vault A", source=FluxSource.VAULT, relevance_score=0.9)]
        cache_blocks = [FluxBlock(content="cache B", source=FluxSource.CACHE, relevance_score=0.8)]
        history_blocks = [FluxBlock(content="history C", source=FluxSource.HISTORY, relevance_score=0.7)]

        agg = FluxAggregator([
            MockProvider(FluxSource.VAULT, vault_blocks),
            MockProvider(FluxSource.CACHE, cache_blocks),
            MockProvider(FluxSource.HISTORY, history_blocks),
        ])
        ctx = await agg.get_context("test", top_k=10)
        assert len(ctx.blocks) == 3
        # Should be sorted by relevance
        assert ctx.blocks[0].relevance_score >= ctx.blocks[1].relevance_score

    @pytest.mark.asyncio
    async def test_deduplication(self):
        """Same content from different sources should be deduped."""
        block1 = FluxBlock(content="same content", source=FluxSource.VAULT, relevance_score=0.9)
        block2 = FluxBlock(content="same content", source=FluxSource.CACHE, relevance_score=0.7)

        agg = FluxAggregator([
            MockProvider(FluxSource.VAULT, [block1]),
            MockProvider(FluxSource.CACHE, [block2]),
        ])
        ctx = await agg.get_context("test")
        assert len(ctx.blocks) == 1
        # Should keep the higher-scored one
        assert ctx.blocks[0].relevance_score == 0.9

    @pytest.mark.asyncio
    async def test_source_filtering(self):
        vault = [FluxBlock(content="vault", source=FluxSource.VAULT, relevance_score=0.9)]
        cache = [FluxBlock(content="cache", source=FluxSource.CACHE, relevance_score=0.8)]

        agg = FluxAggregator([
            MockProvider(FluxSource.VAULT, vault),
            MockProvider(FluxSource.CACHE, cache),
        ])
        ctx = await agg.get_context("test", sources=[FluxSource.VAULT])
        assert len(ctx.blocks) == 1
        assert ctx.blocks[0].source == FluxSource.VAULT

    @pytest.mark.asyncio
    async def test_top_k_limit(self):
        blocks = [
            FluxBlock(content=f"block {i}", source=FluxSource.VAULT, relevance_score=1.0 - i * 0.1)
            for i in range(10)
        ]
        agg = FluxAggregator([MockProvider(FluxSource.VAULT, blocks)])
        ctx = await agg.get_context("test", top_k=3)
        assert len(ctx.blocks) == 3

    @pytest.mark.asyncio
    async def test_min_relevance_filter(self):
        blocks = [
            FluxBlock(content="high", source=FluxSource.VAULT, relevance_score=0.9),
            FluxBlock(content="low", source=FluxSource.VAULT, relevance_score=0.05),
        ]
        agg = FluxAggregator([MockProvider(FluxSource.VAULT, blocks)])
        ctx = await agg.get_context("test", min_relevance=0.1)
        assert len(ctx.blocks) == 1
        assert ctx.blocks[0].content == "high"

    @pytest.mark.asyncio
    async def test_token_estimation(self):
        blocks = [
            FluxBlock(content="short", source=FluxSource.VAULT, relevance_score=0.9),
            FluxBlock(content="this is a longer content block with more words", source=FluxSource.CACHE, relevance_score=0.8),
        ]
        agg = FluxAggregator([
            MockProvider(FluxSource.VAULT, [blocks[0]]),
            MockProvider(FluxSource.CACHE, [blocks[1]]),
        ])
        ctx = await agg.get_context("test")
        assert ctx.total_tokens_estimated > 0

    @pytest.mark.asyncio
    async def test_register_provider(self):
        agg = FluxAggregator()
        blocks = [FluxBlock(content="added later", source=FluxSource.TOOL, relevance_score=0.8)]
        agg.register_provider(MockProvider(FluxSource.TOOL, blocks))
        ctx = await agg.get_context("test")
        assert len(ctx.blocks) == 1

    @pytest.mark.asyncio
    async def test_empty_providers(self):
        agg = FluxAggregator()
        ctx = await agg.get_context("test")
        assert len(ctx.blocks) == 0
        assert ctx.total_tokens_estimated == 0

    @pytest.mark.asyncio
    async def test_provider_failure_non_blocking(self):
        """A failing provider shouldn't break the aggregation."""

        class FailingProvider(FluxProvider):
            source = FluxSource.SURREAL
            async def get_context(self, query, top_k=5, **kwargs):
                raise ConnectionError("DB down")

        good_blocks = [FluxBlock(content="still works", source=FluxSource.VAULT, relevance_score=0.9)]
        agg = FluxAggregator([
            FailingProvider(),
            MockProvider(FluxSource.VAULT, good_blocks),
        ])
        ctx = await agg.get_context("test")
        assert len(ctx.blocks) == 1
        assert ctx.blocks[0].content == "still works"
