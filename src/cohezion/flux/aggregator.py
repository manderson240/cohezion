"""FLUX Aggregator — unified context query across all providers.

Fans out queries to registered providers in parallel, deduplicates
by content hash, re-ranks by relevance, and estimates token cost.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from cohezion.flux.types import FluxBlock, FluxContext, FluxSource


if TYPE_CHECKING:
    from cohezion.flux.provider import FluxProvider


logger = logging.getLogger(__name__)

# Rough estimate: ~4 chars per token (English text)
_CHARS_PER_TOKEN = 4


class FluxAggregator:
    """Unified context interface merging all FLUX providers."""

    def __init__(self, providers: list[FluxProvider] | None = None) -> None:
        self._providers: list[FluxProvider] = list(providers or [])

    def register_provider(self, provider: FluxProvider) -> None:
        self._providers.append(provider)

    def record_history(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Record an entry to the HistoryFlux provider if registered."""
        from cohezion.flux.providers.history_flux import HistoryFlux

        for provider in self._providers:
            if isinstance(provider, HistoryFlux):
                provider.record(content, metadata)
                return
        logger.debug("record_history called but no HistoryFlux provider is registered")

    async def get_context(
        self,
        query: str,
        top_k: int = 10,
        sources: list[FluxSource] | None = None,
        min_relevance: float = 0.0,
    ) -> FluxContext:
        """Query all providers, merge, deduplicate, and rank results."""
        if not self._providers:
            return FluxContext(
                blocks=[],
                total_tokens_estimated=0,
                query=query,
                sources_queried=[],
            )

        # Filter providers by requested sources
        active = self._providers
        if sources is not None:
            source_set = set(sources)
            active = [p for p in self._providers if p.source in source_set]

        # Fan out queries in parallel
        tasks = [self._safe_query(p, query, top_k) for p in active]
        results = await asyncio.gather(*tasks)

        # Flatten and collect
        all_blocks: list[FluxBlock] = []
        for provider_blocks in results:
            all_blocks.extend(provider_blocks)

        # Filter by min_relevance
        if min_relevance > 0:
            all_blocks = [b for b in all_blocks if b.relevance_score >= min_relevance]

        # Deduplicate by content hash (keep highest scored)
        seen: dict[str, FluxBlock] = {}
        for block in all_blocks:
            h = block.content_hash
            if h not in seen or block.relevance_score > seen[h].relevance_score:
                seen[h] = block
        deduped = list(seen.values())

        # Sort by relevance descending
        deduped.sort(key=lambda b: b.relevance_score, reverse=True)

        # Truncate
        final = deduped[:top_k]

        # Estimate tokens
        total_chars = sum(len(b.content) for b in final)
        token_estimate = max(1, total_chars // _CHARS_PER_TOKEN) if final else 0

        return FluxContext(
            blocks=final,
            total_tokens_estimated=token_estimate,
            query=query,
            sources_queried=[p.source for p in active],
        )

    @staticmethod
    async def _safe_query(
        provider: FluxProvider,
        query: str,
        top_k: int,
    ) -> list[FluxBlock]:
        """Query a provider with non-blocking error handling."""
        try:
            return await provider.get_context(query, top_k=top_k)
        except Exception:
            logger.debug(
                "FLUX provider %s failed (non-blocking)",
                provider.source.value,
            )
            return []
