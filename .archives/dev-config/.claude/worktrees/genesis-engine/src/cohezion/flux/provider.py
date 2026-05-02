"""Base class for all FLUX context providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.flux.types import FluxBlock, FluxSource


class FluxProvider(ABC):
    """Abstract base for context providers.

    Each provider wraps a specific context source (vault, SurrealDB, etc.)
    and returns ``FluxBlock`` items ranked by relevance.
    """

    source: FluxSource

    @abstractmethod
    async def get_context(
        self,
        query: str,
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[FluxBlock]:
        """Query this provider for relevant context blocks."""
