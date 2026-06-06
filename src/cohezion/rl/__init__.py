"""Reinforcement Learning module for FLUME manifold navigation."""

import contextlib


__all__: list[str] = []

# Wiring-sweep 2026-06-06: causal_interpreter was a genuine production orphan — its
# ActivationPatcher / CausalInterventionTester / InterventionResult / InterpretabilityReport
# (causal-intervention interpretability for RL policies) had ZERO importers anywhere. Cycle-safe
# (no cohezion module-scope import). Guarded re-export (it imports torch at module scope — the
# suppress tolerates a torch-absent environment) makes it statically reachable.
with contextlib.suppress(Exception):
    from cohezion.rl.causal_interpreter import (
        ActivationPatcher as ActivationPatcher,
    )
    from cohezion.rl.causal_interpreter import (
        CausalInterventionTester as CausalInterventionTester,
    )
    from cohezion.rl.causal_interpreter import (
        InterpretabilityReport as InterpretabilityReport,
    )
    from cohezion.rl.causal_interpreter import (
        InterventionResult as InterventionResult,
    )

    __all__ += [
        "ActivationPatcher",
        "CausalInterventionTester",
        "InterpretabilityReport",
        "InterventionResult",
    ]

# Wiring-sweep 2026-06-06: distributed_trainer was a genuine production orphan — its
# DistributedConfig / ScalingMetrics / DistributedPPOTrainer / DistributedLauncher /
# ScalingBenchmark (DDP/FSDP distributed PPO training) had ZERO importers anywhere. Cycle-safe.
# SEPARATE guarded block (torch + torch.distributed at module scope) so its failure domain is
# isolated from the causal_interpreter re-export above.
with contextlib.suppress(Exception):
    from cohezion.rl.distributed_trainer import (
        DistributedConfig as DistributedConfig,
    )
    from cohezion.rl.distributed_trainer import (
        DistributedLauncher as DistributedLauncher,
    )
    from cohezion.rl.distributed_trainer import (
        DistributedPPOTrainer as DistributedPPOTrainer,
    )
    from cohezion.rl.distributed_trainer import (
        ScalingBenchmark as ScalingBenchmark,
    )
    from cohezion.rl.distributed_trainer import (
        ScalingMetrics as ScalingMetrics,
    )

    __all__ += [
        "DistributedConfig",
        "DistributedLauncher",
        "DistributedPPOTrainer",
        "ScalingBenchmark",
        "ScalingMetrics",
    ]

# Wiring-sweep 2026-06-06: grpo_trainer was a genuine production orphan — its GRPOConfig /
# GRPOMetrics / GRPOTrainer / AsyncGRPOTrainer (Group Relative Policy Optimization training) had
# ZERO importers anywhere. Cycle-safe (torch only, no transformers — imports cleanly). SEPARATE
# guarded block (failure-domain isolation). Completes rl/'s clean genuine-A wiring (lora_trainer
# stays blocked on its transformers import — see ledger Needs-human).
with contextlib.suppress(Exception):
    from cohezion.rl.grpo_trainer import (
        AsyncGRPOTrainer as AsyncGRPOTrainer,
    )
    from cohezion.rl.grpo_trainer import (
        GRPOConfig as GRPOConfig,
    )
    from cohezion.rl.grpo_trainer import (
        GRPOMetrics as GRPOMetrics,
    )
    from cohezion.rl.grpo_trainer import (
        GRPOTrainer as GRPOTrainer,
    )

    __all__ += ["AsyncGRPOTrainer", "GRPOConfig", "GRPOMetrics", "GRPOTrainer"]
