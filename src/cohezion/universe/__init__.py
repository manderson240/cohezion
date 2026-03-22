"""Universe simulation engine and sandbox isolation.

Provides 12D/2048D manifold simulation, containerized code execution,
multi-backend sandbox isolation, and divergence detection.
"""

from cohezion.universe.divergence import DivergenceDetector, DivergenceStatus
from cohezion.universe.engine import UniverseSimulationEngine
from cohezion.universe.example_simulations import EXAMPLES
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
    "BackendResult",
    "ContainerizedUniverse",
    "DivergenceDetector",
    "DivergenceStatus",
    "DockerBackend",
    "EXAMPLES",
    "IsolationBackend",
    "PROFILES",
    "SandboxManager",
    "SandboxProfile",
    "SandboxResult",
    "SandboxTier",
    "SubprocessBackend",
    "SystemdRunBackend",
    "UniverseSimulationEngine",
    "get_profile",
    "get_sandbox_manager",
    "persist_result",
    "select_backend",
]
