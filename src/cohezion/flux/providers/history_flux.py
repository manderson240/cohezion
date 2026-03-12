"""FLUX provider for in-memory execution history."""

from __future__ import annotations

import time
from collections import deque
from typing import Any

from cohezion.flux.provider import FluxProvider
from cohezion.flux.types import FluxBlock, FluxSource


class HistoryFlux(FluxProvider):
    """Context from recent execution history (in-memory ring buffer)."""

    source = FluxSource.HISTORY

    def __init__(self, max_entries: int = 50) -> None:
        self._entries: deque[dict[str, Any]] = deque(maxlen=max_entries)

    def record(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add an entry to the history buffer."""
        self._entries.append(
            {
                "content": content,
                "metadata": metadata or {},
                "timestamp": time.time(),
            }
        )

    async def get_context(
        self,
        query: str,
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[FluxBlock]:
        if not self._entries:
            return []

        query_lower = query.lower()
        scored = []
        for entry in self._entries:
            content = entry["content"]
            # Simple keyword overlap scoring
            words = set(query_lower.split())
            content_words = set(content.lower().split())
            overlap = len(words & content_words)
            score = overlap / max(len(words), 1)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            FluxBlock(
                content=entry["content"],
                source=self.source,
                relevance_score=min(score, 1.0),
                metadata=entry.get("metadata", {}),
                timestamp=entry.get("timestamp", time.time()),
            )
            for score, entry in scored[:top_k]
        ]
