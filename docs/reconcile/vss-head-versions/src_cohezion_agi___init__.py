"""Cohezion AGI Progress & AutoHarness Synthesis Package

Implements AutoHarness (arXiv:2603.03329v1) code-as-action policy synthesis,
ARC-Prize/AIMO reasoning solvers, and self-evaluating R-Zero evolution.
"""

from cohezion.agi.autoharness_policy import ActionPolicyResult, AutoHarnessPolicy
from cohezion.agi.kaggle_autoharness import (
    AIMOProofState,
    ARCGridInvariant,
    KaggleAutoHarness,
    KaggleHarnessResult,
)

__all__ = [
    "AutoHarnessPolicy",
    "ActionPolicyResult",
    "KaggleAutoHarness",
    "ARCGridInvariant",
    "AIMOProofState",
    "KaggleHarnessResult",
]

