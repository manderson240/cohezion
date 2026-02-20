"""Real embodied environments for agent training.

Provides actual browser, shell, and API environments with real execution
capabilities. Unlike simulated environments, these interact with real systems
and produce verifiable outcomes.

All environments capture execution traces for journey tracking and evaluation.
"""

from cohezion.real_envs.browser_env import (
    BrowserAction,
    BrowserEnvironment,
    BrowserObservation,
    BrowserState,
)
from cohezion.real_envs.shell_env import (
    ShellAction,
    ShellEnvironment,
    ShellObservation,
    ShellState,
)
from cohezion.real_envs.api_env import (
    APIAction,
    APIEnvironment,
    APIObservation,
    APIState,
)
from cohezion.real_envs.base import (
    RealAction,
    RealEnvironment,
    RealObservation,
    RealState,
    EnvironmentStep,
    TrajectorySegment,
)

__all__ = [
    # Browser
    "BrowserAction",
    "BrowserEnvironment",
    "BrowserObservation",
    "BrowserState",
    # Shell
    "ShellAction",
    "ShellEnvironment",
    "ShellObservation",
    "ShellState",
    # API
    "APIAction",
    "APIEnvironment",
    "APIObservation",
    "APIState",
    # Base
    "RealAction",
    "RealEnvironment",
    "RealObservation",
    "RealState",
    "EnvironmentStep",
    "TrajectorySegment",
]
