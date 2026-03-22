"""FLUX provider wrapping the Obsidian vault via VaultLogger."""

from __future__ import annotations

import logging
from typing import Any

from cohezion.flux.provider import FluxProvider
from cohezion.flux.types import FluxBlock, FluxSource


logger = logging.getLogger(__name__)


class VaultFlux(FluxProvider):
    """Context from Obsidian vault experience guidance."""

    source = FluxSource.VAULT

    def __init__(self, vault_logger: Any) -> None:
        self._vault = vault_logger

    async def get_context(
        self,
        query: str,
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[FluxBlock]:
        try:
            guidance = self._vault.get_experience_guidance(query)
        except Exception:
            logger.debug("Vault guidance query failed (non-blocking)")
            return []

        if not guidance:
            return []

        blocks: list[FluxBlock] = []
        if "guidance" in guidance:
            blocks.append(
                FluxBlock(
                    content=str(guidance["guidance"]),
                    source=self.source,
                    relevance_score=0.9,
                    metadata={"similar_tasks": guidance.get("similar_tasks", [])},
                )
            )
        return blocks[:top_k]
