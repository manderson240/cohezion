"""Universe simulation engine and sandbox isolation.

Provides 12D/2048D manifold simulation, containerized code execution,
multi-backend sandbox isolation, divergence detection, agentic task
environments, capability evaluation, and experiment tracking.
"""

from cohezion.universe.agentic_env import (
    AgenticEnvironment,
    TaskScenario,
    ToolRegistry,
    TrajectoryRecorder,
)
from cohezion.universe.capability_eval import (
    EvalRunner,
    EvalScorer,
    RegressionDetector,
    TaskSuite,
    build_core_capability_suite,
)
from cohezion.universe.divergence import DivergenceDetector, DivergenceStatus
from cohezion.universe.engine import UniverseSimulationEngine
from cohezion.universe.example_simulations import EXAMPLES
from cohezion.universe.experiment_tracker import (
    ExperimentTracker,
    RunConfig,
)
from cohezion.universe.sandbox import ContainerizedUniverse, SandboxResult
from cohezion.universe.sandbox_backends import (
    BackendResult,
    DockerBackend,
    IsolationBackend,
    SubprocessBackend,
    SystemdRunBackend,
    select_backend,
)
from cohezion.universe.sandbox_manager import SandboxManager, get_sandbox_manager
from cohezion.universe.sandbox_profiles import (
    PROFILES,
    SandboxProfile,
    SandboxTier,
    get_profile,
)
from cohezion.universe.sandbox_results import persist_result


__all__ = [
    "EXAMPLES",
    "PROFILES",
    "BackendResult",
    "ContainerizedUniverse",
    "DivergenceDetector",
    "DivergenceStatus",
    "DockerBackend",
    "IsolationBackend",
    "SandboxManager",
    "SandboxProfile",
    "SandboxResult",
    "SandboxTier",
    "SubprocessBackend",
    "SystemdRunBackend",
    "TaskScenario",
    "TaskSuite",
    "ToolRegistry",
    "TrajectoryRecorder",
    "UniverseSimulationEngine",
    "build_core_capability_suite",
    "get_profile",
    "get_sandbox_manager",
    "persist_result",
    "select_backend",
]
