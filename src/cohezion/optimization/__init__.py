"""Optimization — R-Zero local model optimizer."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.optimization.r_zero import LocalModelOptimizer as LocalModelOptimizer
    from cohezion.optimization.r_zero import RZeroMetrics as RZeroMetrics
