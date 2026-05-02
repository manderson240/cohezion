"""FLUX provider wrapping SemanticCache L2 search."""

from __future__ import annotations

import logging
from typing import Any

from cohezion.flux.provider import FluxProvider
from cohezion.flux.types import FluxBlock, FluxSource


logger = logging.getLogger(__name__)


class CacheFlux(FluxProvider):
    """Context from SemanticCache L2 cosine similarity search."""

    source = FluxSource.CACHE

    def __init__(self, semantic_cache: Any | None = None) -> None:
        self._cache = semantic_cache

    async def get_context(
        self,
        query: str,
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[FluxBlock]:
        if self._cache is None:
            return []

        try:
            results = self._cache.search_l2(query, top_k=top_k)
        except Exception:
            logger.debug("SemanticCache L2 search failed (non-blocking)")
            return []

        return [
            FluxBlock(
                content=str(r.get("content", "")),
                source=self.source,
                relevance_score=float(r.get("score", 0.0)),
            )
            for r in (results or [])
        ]
