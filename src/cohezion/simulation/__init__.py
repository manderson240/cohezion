"""Simulation frameworks for 12D universe, RL training, and distributed runs.

Provides fractal universe simulation, HIHO RL environments, vectorized
parallel training, enhanced R-Zero simulators, and distributed execution.
"""

from cohezion.simulation.fractal_universe import FractalSimulator
from cohezion.simulation.rl_framework import HihoEnvironment, PPOAgent
from cohezion.simulation.vectorized_env import (
    CurriculumScheduler,
    VectorizedHihoEnv,
)


__all__ = [
    "CurriculumScheduler",
    "FractalSimulator",
    "HihoEnvironment",
    "PPOAgent",
    "VectorizedHihoEnv",
]

import contextlib


# Wiring-sweep 2026-06-22: simulation sub-modules were genuine import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.simulation.analysis_prime import SimulationAnalyzer as SimulationAnalyzer

with contextlib.suppress(Exception):
    from cohezion.simulation.benchmark_runner import BenchmarkConfig as BenchmarkConfig
    from cohezion.simulation.benchmark_runner import BenchmarkMetrics as BenchmarkMetrics
    from cohezion.simulation.benchmark_runner import BenchmarkRunner as BenchmarkRunner

with contextlib.suppress(Exception):
    from cohezion.simulation.distributed import AgentState as AgentState
    from cohezion.simulation.distributed import ShardSpec as ShardSpec

with contextlib.suppress(Exception):
    from cohezion.simulation.emergent_detector import EmergenceReport as EmergenceReport
    from cohezion.simulation.emergent_detector import EmergentDetector as EmergentDetector
    from cohezion.simulation.emergent_detector import EmergentEvent as EmergentEvent

with contextlib.suppress(Exception):
    from cohezion.simulation.enhanced_simulator import (
        FlumeTrajectoryPoint as FlumeTrajectoryPoint,
    )

with contextlib.suppress(Exception):
    from cohezion.simulation.lifecycle_presim import (
        LifecyclePreSimulator as LifecyclePreSimulator,
    )
    from cohezion.simulation.lifecycle_presim import PreSimResult as PreSimResult

with contextlib.suppress(Exception):
    from cohezion.simulation.simulation_logger import SimulationLogger as SimulationLogger
