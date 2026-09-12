from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TransportResponse:
    content: str
    model_name: str
    latency_ms: float
    verified: bool


class BaseInferenceTransport(ABC):
    """Abstract base class for all inference transports.
    Ensures the router remains agnostic to the underlying API or protocol.
    """

    @abstractmethod
    async def query(
        self, prompt: str, model_id: str, params: dict[str, Any] | None = None
    ) -> TransportResponse | None:
        """Perform an inference call and return a standardized response."""
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if the transport is currently available."""
        pass
