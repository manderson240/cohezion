"""Base agent for competition tasks."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.competition.orchestrator.model_dispatcher import GenerationResult, ModelDispatcher


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Specialist agent with local model access."""

    def __init__(self, name: str, dispatcher: ModelDispatcher) -> None:
        self.name = name
        self.dispatcher = dispatcher

    def think(self, system: str, prompt: str, **kwargs: Any) -> GenerationResult:
        logger.info(f"[{self.name}] thinking...")
        return self.dispatcher.generate(system, prompt, **kwargs)

    @abstractmethod
    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute one task and return results."""
        ...
