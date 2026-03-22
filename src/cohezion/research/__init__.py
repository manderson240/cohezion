"""Autonomous research module for training optimization.

Elegant integration of karpathy/autoresearch patterns into Cohezion.
"""

from __future__ import annotations

from cohezion.research.agent import ResearchAgent, ResearchSession
from cohezion.research.config import (
    ExperimentResult,
    ResearchConfig,
)
from cohezion.research.security import (
    CodeChange,
    ResearchSecurityGuardrails,
    ValidationResult,
)


__version__ = "0.2.0"


# Lazy imports for optional components to avoid circular deps and heavy dependencies
__all__ = [
    "CodeChange",
    "DegradationSignal",
    "ExperimentResult",
    "MultiAgentResearchConfig",
    "MultiAgentResult",
    "OptimizationResult",
    # Core
    "ResearchAgent",
    "ResearchConfig",
    # Squad
    "ResearchSecurityGuardrails",
    "ResearchSession",
    "ResearchSquad",
    # Multi-agent
    "ResearchSwarm",
    "SimpleMultiAgent",
    "SimpleTrainingRunner",
    # Training
    "TrainingExecutor",
    "ValidationResult",
    "integrate_with_compound_system",
]


def __getattr__(name):
    """Lazy load components to avoid circular dependencies and heavy imports."""
    if name in (
        "MultiAgentResearchConfig",
        "MultiAgentResult",
        "ResearchSwarm",
        "SimpleMultiAgent",
    ):
        from cohezion.research.multi_agent import (
            MultiAgentResearchConfig,
            MultiAgentResult,
            ResearchSwarm,
            SimpleMultiAgent,
        )

        return locals()[name]
    elif name in (
        "DegradationSignal",
        "OptimizationResult",
        "ResearchSquad",
        "integrate_with_compound_system",
    ):
        from cohezion.research.research_squad import (
            DegradationSignal,
            OptimizationResult,
            ResearchSquad,
            integrate_with_compound_system,
        )

        return locals()[name]
    elif name in ("SimpleTrainingRunner", "TrainingExecutor"):
        from cohezion.research.training import (
            SimpleTrainingRunner,
            TrainingExecutor,
        )

        return locals()[name]
    raise AttributeError(f"module 'cohezion.research' has no attribute '{name}'")


def get_version() -> str:
    """Get research module version."""
    return __version__
