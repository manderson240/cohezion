"""Optimization — R-Zero local model optimizer and Challenger vs Solver engine."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.optimization.r_zero import LocalModelOptimizer as LocalModelOptimizer
    from cohezion.optimization.r_zero import RZeroMetrics as RZeroMetrics
    from cohezion.optimization.r_zero_challenger_solver import (
        ProceduralARCGenerator as ProceduralARCGenerator,
        RZeroChallenge as RZeroChallenge,
        RZeroChallenger as RZeroChallenger,
        RZeroEvaluation as RZeroEvaluation,
        RZeroPragmatist as RZeroPragmatist,
        RZeroSolution as RZeroSolution,
        RZeroSolver as RZeroSolver,
        RZeroTriadLoop as RZeroTriadLoop,
    )
