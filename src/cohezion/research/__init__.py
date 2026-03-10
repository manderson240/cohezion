"""Autonomous research module for training optimization.

Elegant integration of karpathy/autoresearch patterns into Cohezion.
"""

from __future__ import annotations

from cohezion.research.agent import ResearchAgent, ResearchSession
from cohezion.research.config import (
    ExperimentResult,
    ResearchConfig,
    MultiAgentResearchConfig,
    MultiAgentResult,
)
from cohezion.research.multi_agent import (
    ResearchSwarm,
    SimpleMultiAgent,
)
from cohezion.research.security import (
    CodeChange,
    ResearchSecurityGuardrails,
    ValidationResult,
)
from cohezion.research.training import (
    SimpleTrainingRunner,
    TrainingExecutor,
)

__all__ = [
    # Core
    "ResearchAgent",
    "ResearchSession",
    "ResearchConfig",
    "ExperimentResult",
    # Multi-agent
    "ResearchSwarm",
    "MultiAgentResearchConfig",
    "MultiAgentResult",
    "SimpleMultiAgent",
    # Security
    "ResearchSecurityGuardrails",
    "CodeChange",
    "ValidationResult",
    # Training
    "TrainingExecutor",
    "SimpleTrainingRunner",
]

__version__ = "0.2.0"


def get_version() -> str:
    """Get research module version."""
    return __version__
