"""Tests for FLUX Protocol types and provider base."""

from __future__ import annotations

import time

import numpy as np
import pytest

from cohezion.flux.provider import FluxProvider
from cohezion.flux.types import FluxBlock, FluxContext, FluxSource


class TestFluxSource:
    def test_enum_values(self):
        assert FluxSource.VAULT.value == "vault"
        assert FluxSource.SURREAL.value == "surreal"
        assert FluxSource.TOOL.value == "tool"
        assert FluxSource.HISTORY.value == "history"
        assert FluxSource.CACHE.value == "cache"
        assert FluxSource.REGISTRY.value == "registry"


class TestFluxBlock:
    def test_create_block(self):
        block = FluxBlock(
            content="Previous execution used template X",
            source=FluxSource.VAULT,
            relevance_score=0.92,
        )
        assert block.content == "Previous execution used template X"
        assert block.source == FluxSource.VAULT
        assert block.relevance_score == 0.92
        assert block.embedding is None
        assert block.metadata == {}

    def test_block_with_embedding(self):
        emb = np.random.rand(384).astype(np.float32)
        block = FluxBlock(
            content="test",
            source=FluxSource.SURREAL,
            relevance_score=0.8,
            embedding=emb,
        )
        assert block.embedding is not None
        assert block.embedding.shape == (384,)

    def test_block_with_metadata(self):
        block = FluxBlock(
            content="tool output",
            source=FluxSource.TOOL,
            relevance_score=0.7,
            metadata={"tool_name": "web_search", "latency_ms": 200},
        )
        assert block.metadata["tool_name"] == "web_search"

    def test_block_timestamp_auto_set(self):
        before = time.time()
        block = FluxBlock(content="x", source=FluxSource.HISTORY, relevance_score=0.5)
        after = time.time()
        assert before <= block.timestamp <= after

    def test_content_hash_for_dedup(self):
        b1 = FluxBlock(content="same content", source=FluxSource.VAULT, relevance_score=0.9)
        b2 = FluxBlock(content="same content", source=FluxSource.CACHE, relevance_score=0.7)
        b3 = FluxBlock(content="different", source=FluxSource.VAULT, relevance_score=0.9)
        assert b1.content_hash == b2.content_hash
        assert b1.content_hash != b3.content_hash


class TestFluxContext:
    def test_create_context(self):
        blocks = [
            FluxBlock(content="a", source=FluxSource.VAULT, relevance_score=0.9),
            FluxBlock(content="b", source=FluxSource.CACHE, relevance_score=0.8),
        ]
        ctx = FluxContext(
            blocks=blocks,
            total_tokens_estimated=150,
            query="how to deploy",
            sources_queried=[FluxSource.VAULT, FluxSource.CACHE],
        )
        assert len(ctx.blocks) == 2
        assert ctx.total_tokens_estimated == 150

    def test_empty_context(self):
        ctx = FluxContext(
            blocks=[],
            total_tokens_estimated=0,
            query="test",
            sources_queried=[],
        )
        assert len(ctx.blocks) == 0


class TestFluxProviderABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            FluxProvider()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_concrete_provider(self):
        class MockProvider(FluxProvider):
            source = FluxSource.HISTORY

            async def get_context(self, query, top_k=5, **kwargs):
                return [
                    FluxBlock(
                        content=f"result for {query}", source=self.source, relevance_score=1.0
                    )
                ]

        provider = MockProvider()
        results = await provider.get_context("test query")
        assert len(results) == 1
        assert results[0].content == "result for test query"
        assert results[0].source == FluxSource.HISTORY
