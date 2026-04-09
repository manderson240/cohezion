"""Base framework for autonomous research loops."""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass
from typing import Any, Generic, TypeVar


log = logging.getLogger("autoresearch")

T = TypeVar("T")  # Result type


@dataclass
class ExperimentResult:
    """Standardized result for an autonomous experiment."""

    success: bool
    metric: float | None = None
    error: str | None = None
    metadata: dict[str, Any] = None


class ResearchDriver(abc.ABC, Generic[T]):
    """Abstract base class for autonomous experimentation drivers."""

    def __init__(self, objective: str, time_budget_seconds: int = 300):
        self.objective = objective
        self.time_budget = time_budget_seconds
        self.cycles = 0

    @abc.abstractmethod
    def select_next_node(self) -> Any:
        """Select the next strategy or parameter set to test."""
        pass

    @abc.abstractmethod
    def generate_candidate(self, node: Any) -> str:
        """Generate candidate code or configuration."""
        pass

    @abc.abstractmethod
    def evaluate_candidate(self, candidate: str) -> ExperimentResult:
        """Execute and evaluate the candidate."""
        pass

    @abc.abstractmethod
    def update_model(self, node: Any, result: ExperimentResult):
        """Update the world model or search tree with the result."""
        pass

    def run_cycle(self) -> bool:
        """Execute a single research cycle."""
        self.cycles += 1
        node = self.select_next_node()
        if not node:
            log.info("No nodes available for research.")
            return False

        log.info(f"Cycle {self.cycles}: Testing {node}")
        candidate = self.generate_candidate(node)

        result = self.evaluate_candidate(candidate)
        self.update_model(node, result)

        return result.success

    def run_continuous(self, max_cycles: int = 0):
        """Run the research loop continuously."""
        try:
            while max_cycles == 0 or self.cycles < max_cycles:
                if not self.run_cycle():
                    break
        except KeyboardInterrupt:
            log.info("Research loop interrupted by user.")
