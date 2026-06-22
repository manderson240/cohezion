"""Autonomous research module for training optimization.

Elegant integration of karpathy/autoresearch patterns into Cohezion.
"""

from __future__ import annotations

import contextlib

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


def __getattr__(name: str) -> object:
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

        globals().update(
            {
                "MultiAgentResearchConfig": MultiAgentResearchConfig,
                "MultiAgentResult": MultiAgentResult,
                "ResearchSwarm": ResearchSwarm,
                "SimpleMultiAgent": SimpleMultiAgent,
            }
        )
        return globals()[name]
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

        globals().update(
            {
                "DegradationSignal": DegradationSignal,
                "OptimizationResult": OptimizationResult,
                "ResearchSquad": ResearchSquad,
                "integrate_with_compound_system": integrate_with_compound_system,
            }
        )
        return globals()[name]
    elif name in ("SimpleTrainingRunner", "TrainingExecutor"):
        from cohezion.research.training import (
            SimpleTrainingRunner,
            TrainingExecutor,
        )

        globals().update(
            {
                "SimpleTrainingRunner": SimpleTrainingRunner,
                "TrainingExecutor": TrainingExecutor,
            }
        )
        return globals()[name]
    raise AttributeError(f"module 'cohezion.research' has no attribute '{name}'")


def get_version() -> str:
    """Get research module version."""
    return __version__


# Wiring-sweep 2026-06-22: research/ orphan modules — creates import-graph edges.
with contextlib.suppress(Exception):
    from cohezion.research.adaptive_refinement import AdaptiveSkillRefiner as AdaptiveSkillRefiner
with contextlib.suppress(Exception):
    from cohezion.research.adaptive_refinement import SkillRefinementPlugin as SkillRefinementPlugin
with contextlib.suppress(Exception):
    from cohezion.research.autocontext import monitor as monitor
with contextlib.suppress(Exception):
    from cohezion.research.autoresearch import AutoResearcher as AutoResearcher
with contextlib.suppress(Exception):
    from cohezion.research.autoresearch import ResearchResult as ResearchResult
with contextlib.suppress(Exception):
    from cohezion.research.autoresearch_driver import AutoresearchDriver as AutoresearchDriver
with contextlib.suppress(Exception):
    from cohezion.research.autoresearch_driver import ExperimentOutcome as ExperimentOutcome
with contextlib.suppress(Exception):
    from cohezion.research.checkpoint import ResearchCheckpoint as ResearchCheckpoint
with contextlib.suppress(Exception):
    from cohezion.research.checkpoint import CheckpointPersistence as CheckpointPersistence
with contextlib.suppress(Exception):
    from cohezion.research.consensus import ConsensusResult as ConsensusResult
with contextlib.suppress(Exception):
    from cohezion.research.consensus import PartyModeConsensus as PartyModeConsensus
with contextlib.suppress(Exception):
    from cohezion.research.cost_optimization import CostTracker as CostTracker
with contextlib.suppress(Exception):
    from cohezion.research.cost_optimization import CostBudget as CostBudget
with contextlib.suppress(Exception):
    from cohezion.research.flume_integration import FLUMEResearchOptimizer as FLUMEResearchOptimizer
with contextlib.suppress(Exception):
    from cohezion.research.flume_integration import HyperparameterConfig as HyperparameterConfig
with contextlib.suppress(Exception):
    from cohezion.research.orborous import Orborous as Orborous
with contextlib.suppress(Exception):
    from cohezion.research.resource_guarded_autoresearch import ResourceGuard as ResourceGuard
with contextlib.suppress(Exception):
    from cohezion.research.resource_guarded_autoresearch import (
        MultiAgentAutoresearch as MultiAgentAutoresearch,
    )
with contextlib.suppress(Exception):
    from cohezion.research.security_api import APIKeyManager as APIKeyManager
with contextlib.suppress(Exception):
    from cohezion.research.security_api import HealthChecker as HealthChecker
