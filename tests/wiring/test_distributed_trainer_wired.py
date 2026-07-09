"""Discriminating test for the wiring-sweep edge: rl → distributed_trainer (2026-06-06).

`distributed_trainer` was a genuine production orphan in rl/ — its DistributedConfig /
ScalingMetrics / DistributedPPOTrainer / DistributedLauncher / ScalingBenchmark (DDP/FSDP
distributed PPO training) had ZERO importers anywhere. Wired non-destructively via a guarded
`cohezion.rl` __init__ re-export (torch-guarded — imports torch + torch.distributed at scope).

Falsifiable: this test fails if the static edge is removed — every name must resolve FROM the
package AND be the source module's own object (identity), and appear in __all__. It also pins
that the causal_interpreter edge (the first guarded block) stays intact alongside the new one.
"""

from __future__ import annotations

import pytest


def test_distributed_trainer_reexported_from_rl() -> None:
    pytest.importorskip("torch")  # module imports torch.distributed at scope; skip if absent
    import cohezion.rl as rl
    import cohezion.rl.distributed_trainer as src

    for name in (
        "DistributedConfig",
        "ScalingMetrics",
        "DistributedPPOTrainer",
        "DistributedLauncher",
        "ScalingBenchmark",
    ):
        assert hasattr(rl, name), f"rl.{name} unreachable — wiring edge missing"
        assert getattr(rl, name) is getattr(src, name), f"{name} is not the source object"
        assert name in rl.__all__, f"{name} missing from rl.__all__"


def test_causal_interpreter_edge_still_intact() -> None:
    # The two guarded blocks must coexist — adding distributed_trainer must not unbind the first.
    pytest.importorskip("torch")
    import cohezion.rl as rl

    assert "ActivationPatcher" in rl.__all__
    assert hasattr(rl, "CausalInterventionTester")
