"""FLUX provider wrapping CapabilityRegistry for tool/skill discovery."""

from __future__ import annotations

import logging
from typing import Any

from cohezion.flux.provider import FluxProvider
from cohezion.flux.types import FluxBlock, FluxSource


logger = logging.getLogger(__name__)


class ToolFlux(FluxProvider):
    """Context from capability registry (skills, agents, MCP tools)."""

    source = FluxSource.TOOL

    def __init__(self, capability_registry: Any) -> None:
        self._registry = capability_registry

    async def get_context(
        self,
        query: str,
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[FluxBlock]:
        try:
            capabilities = self._registry.find(query, top_k=top_k)
        except Exception:
            logger.debug("CapabilityRegistry query failed (non-blocking)")
            return []

        return [
            FluxBlock(
                content=f"{cap.name}: {cap.description}",
                source=self.source,
                relevance_score=float(getattr(cap, "score", 0.5)),
                metadata={"type": getattr(cap, "type", "unknown"), "name": cap.name},
            )
            for cap in (capabilities or [])
        ]
