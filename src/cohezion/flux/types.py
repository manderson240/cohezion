"""Core types for the FLUX Protocol."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    import numpy as np


class FluxSource(Enum):
    """Origin of a context block."""

    VAULT = "vault"
    SURREAL = "surreal"
    TOOL = "tool"
    HISTORY = "history"
    CACHE = "cache"
    REGISTRY = "registry"


@dataclass
class FluxBlock:
    """A single context block from any FLUX provider."""

    content: str
    source: FluxSource
    relevance_score: float
    embedding: np.ndarray | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def content_hash(self) -> str:
        """SHA-256 hash of content for deduplication."""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]


@dataclass
class FluxContext:
    """Aggregated context from multiple FLUX providers."""

    blocks: list[FluxBlock]
    total_tokens_estimated: int
    query: str
    sources_queried: list[FluxSource]
