"""Resilience strategies and autonomic management for compound loop fault tolerance."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.resilience.manager import AutonomicManager as AutonomicManager

with contextlib.suppress(Exception):
    from cohezion.resilience.strategies import (
        ContextReductionStrategy as ContextReductionStrategy,
    )
    from cohezion.resilience.strategies import HealingStrategy as HealingStrategy
    from cohezion.resilience.strategies import ModelSwapStrategy as ModelSwapStrategy
    from cohezion.resilience.strategies import (
        SystemRestartStrategy as SystemRestartStrategy,
    )
