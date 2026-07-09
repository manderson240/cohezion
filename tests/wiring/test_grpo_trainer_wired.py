"""Discriminating test for the wiring-sweep edge: rl → grpo_trainer (2026-06-06).

`grpo_trainer` was a genuine production orphan in rl/ — its GRPOConfig / GRPOMetrics / GRPOTrainer
/ AsyncGRPOTrainer (Group Relative Policy Optimization training) had ZERO importers anywhere.
Wired non-destructively via a guarded `cohezion.rl` __init__ re-export (torch-guarded). This is
the THIRD guarded block in rl/__init__ — the test also pins that all three coexist.

Falsifiable: fails if the static edge is removed — every name must resolve FROM the package AND be
the source module's own object (identity), and appear in __all__.
"""

from __future__ import annotations

import pytest


def test_grpo_trainer_reexported_from_rl() -> None:
    pytest.importorskip("torch")
    import cohezion.rl as rl
    import cohezion.rl.grpo_trainer as src

    for name in ("GRPOConfig", "GRPOMetrics", "GRPOTrainer", "AsyncGRPOTrainer"):
        assert hasattr(rl, name), f"rl.{name} unreachable — wiring edge missing"
        assert getattr(rl, name) is getattr(src, name), f"{name} is not the source object"
        assert name in rl.__all__, f"{name} missing from rl.__all__"


def test_all_three_rl_guarded_blocks_coexist() -> None:
    # Adding grpo_trainer must not unbind the causal_interpreter or distributed_trainer edges.
    pytest.importorskip("torch")
    import cohezion.rl as rl

    assert hasattr(rl, "ActivationPatcher")  # causal_interpreter (block 1)
    assert hasattr(rl, "DistributedLauncher")  # distributed_trainer (block 2)
    assert hasattr(rl, "AsyncGRPOTrainer")  # grpo_trainer (block 3)
