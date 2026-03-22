"""FLUX provider wrapping SurrealDB vector similarity search."""

from __future__ import annotations

import logging
from typing import Any

from cohezion.flux.provider import FluxProvider
from cohezion.flux.types import FluxBlock, FluxSource


logger = logging.getLogger(__name__)


class SurrealFlux(FluxProvider):
    """Context from SurrealDB vector similarity search."""

    source = FluxSource.SURREAL

    def __init__(self, surreal_client: Any) -> None:
        self._client = surreal_client

    async def get_context(
        self,
        query: str,
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[FluxBlock]:
        try:
            results = await self._client.query_similar(query, limit=top_k)
        except Exception:
            logger.debug("SurrealDB query failed (non-blocking)")
            return []

        return [
            FluxBlock(
                content=str(r.get("content", "")),
                source=self.source,
                relevance_score=float(r.get("score", 0.0)),
                metadata={"id": r.get("id", "")},
            )
            for r in (results or [])
        ]
