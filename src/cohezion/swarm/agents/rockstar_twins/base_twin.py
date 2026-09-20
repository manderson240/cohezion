"""Base class and models for Rockstar Scientist Digital Twins."""

from __future__ import annotations

import contextlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cohezion.microservices.spec import BoundedContext, MicroserviceContract


@dataclass
class RefactoringProposal:
    """Refactoring proposal synthesized by a Rockstar Scientist Digital Twin."""

    scientist_name: str
    microservice_name: str
    bounded_context: BoundedContext
    analyzed_modules: list[str]
    total_loc: int
    estimated_entropy_reduction_pct: float
    refactored_interfaces: list[str]
    subscribed_events: list[str]
    published_events: list[str]
    theoretical_rationale: str
    hardware_target: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scientist_name": self.scientist_name,
            "microservice_name": self.microservice_name,
            "bounded_context": self.bounded_context.name,
            "analyzed_modules": self.analyzed_modules,
            "total_loc": self.total_loc,
            "estimated_entropy_reduction_pct": self.estimated_entropy_reduction_pct,
            "refactored_interfaces": self.refactored_interfaces,
            "subscribed_events": self.subscribed_events,
            "published_events": self.published_events,
            "theoretical_rationale": self.theoretical_rationale,
            "hardware_target": self.hardware_target,
            "created_at": self.created_at,
        }


class RockstarScientistTwin(ABC):
    """Abstract Digital Twin embodying a pioneer scientist's methodology."""

    def __init__(
        self,
        name: str,
        title: str,
        domain: str,
        core_maxim: str,
        target_microservice: str,
        target_modules: list[str],
        hardware_target: str = "Host CPU / UMA",
    ) -> None:
        self.name = name
        self.title = title
        self.domain = domain
        self.core_maxim = core_maxim
        self.target_microservice = target_microservice
        self.target_modules = target_modules
        self.hardware_target = hardware_target

    def count_target_loc(self, base_dir: Path) -> int:
        """Count total lines of code across assigned monolithic target modules."""
        total = 0
        for mod in self.target_modules:
            p = base_dir / mod
            if p.is_file() and p.suffix == ".py":
                with contextlib.suppress(Exception):
                    total += len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
            elif p.is_dir():
                for py_file in p.glob("**/*.py"):
                    with contextlib.suppress(Exception):
                        total += len(
                            py_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                        )
        return total

    @abstractmethod
    def synthesize_bounded_context(self) -> BoundedContext:
        """Define the formal Domain-Driven Bounded Context for the target microservice."""

    @abstractmethod
    def synthesize_contract(self) -> MicroserviceContract:
        """Generate the formal microservice interface and communication contract."""

    @abstractmethod
    def develop_refactoring_proposal(self, base_dir: Path) -> RefactoringProposal:
        """Analyze monolithic slice and generate a comprehensive refactoring proposal."""
