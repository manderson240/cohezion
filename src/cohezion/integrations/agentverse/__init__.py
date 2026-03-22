"""Cohezion-AgentVerse integration.

Provides adapters and bridges for using AgentVerse multi-agent frameworks
with Cohezion's compound engineering system.
"""

from cohezion.integrations.agentverse.benchmark_runner import (
    AgentVerseBenchmarkRunner,
    BenchmarkResult,
)
from cohezion.integrations.agentverse.bridge import (
    AgentVerseBridge,
    CoherenceViolation,
)
from cohezion.integrations.agentverse.cohezion_agent import CohezionAgentAdapter
from cohezion.integrations.agentverse.cohezion_environment import (
    CohezionEnvironment,
    CohezionSimulationEnvironment,
    CohezionTaskSolvingEnvironment,
)
from cohezion.integrations.agentverse.compound_loop import (
    CompoundBenchmarkLoop,
    IterationResult,
    LoopConfig,
    LoopResult,
)


__all__ = [
    "AgentVerseBenchmarkRunner",
    "AgentVerseBridge",
    "BenchmarkResult",
    "CoherenceViolation",
    "CohezionAgentAdapter",
    "CohezionEnvironment",
    "CohezionSimulationEnvironment",
    "CohezionTaskSolvingEnvironment",
    "CompoundBenchmarkLoop",
    "IterationResult",
    "LoopConfig",
    "LoopResult",
]
