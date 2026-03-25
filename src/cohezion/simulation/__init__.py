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
