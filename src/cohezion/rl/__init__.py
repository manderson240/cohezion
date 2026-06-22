"""Reinforcement Learning module for FLUME manifold navigation."""

import contextlib


# Wiring-sweep 2026-06-22: causal_interpreter.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.rl.causal_interpreter import (
        CausalInterventionTester as CausalInterventionTester,
    )
    from cohezion.rl.causal_interpreter import (
        InterpretabilityReport as InterpretabilityReport,
    )
    from cohezion.rl.causal_interpreter import (
        InterventionResult as InterventionResult,
    )

# Wiring-sweep 2026-06-22: distributed_trainer.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.rl.distributed_trainer import (
        DistributedConfig as DistributedConfig,
    )
    from cohezion.rl.distributed_trainer import (
        DistributedPPOTrainer as DistributedPPOTrainer,
    )

# Wiring-sweep 2026-06-22: environment.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.rl.environment import FlumeNavEnv as FlumeNavEnv

# Wiring-sweep 2026-06-22: evo.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.rl.evo import (
        EthericVariantOscillator as EthericVariantOscillator,
    )
    from cohezion.rl.evo import (
        EVOTracker as EVOTracker,
    )

# Wiring-sweep 2026-06-22: grpo_trainer.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.rl.grpo_trainer import (
        GRPOConfig as GRPOConfig,
    )
    from cohezion.rl.grpo_trainer import (
        GRPOTrainer as GRPOTrainer,
    )

# Wiring-sweep 2026-06-22: lora_trainer.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.rl.lora_trainer import (
        LoRAConfig as LoRAConfig,
    )
    from cohezion.rl.lora_trainer import (
        SFTTrainer as SFTTrainer,
    )

# Wiring-sweep 2026-06-22: ppo_trainer.py was a genuine import-graph orphan.
# EpisodeResult/train collide with trainer.py; pick distinct names.
with contextlib.suppress(Exception):
    from cohezion.rl.ppo_trainer import (
        PPOConfig as PPOConfig,
    )
    from cohezion.rl.ppo_trainer import (
        PPOTrainer as PPOTrainer,
    )
    from cohezion.rl.ppo_trainer import (
        TRIUNEPolicy as TRIUNEPolicy,
    )

# Wiring-sweep 2026-06-22: reward_shaping.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.rl.reward_shaping import (
        CoherenceReward as CoherenceReward,
    )
    from cohezion.rl.reward_shaping import (
        CompositeReward as CompositeReward,
    )
    from cohezion.rl.reward_shaping import (
        DiversityBonus as DiversityBonus,
    )
    from cohezion.rl.reward_shaping import (
        HamiltonianReward as HamiltonianReward,
    )
    from cohezion.rl.reward_shaping import (
        StabilityPenalty as StabilityPenalty,
    )

# Wiring-sweep 2026-06-22: task_generator.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.rl.task_generator import (
        TaskGenerator as TaskGenerator,
    )
    from cohezion.rl.task_generator import (
        TaskSpec as TaskSpec,
    )

# Wiring-sweep 2026-06-22: trainer.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.rl.trainer import (
        EpisodeResult as EpisodeResult,
    )
    from cohezion.rl.trainer import (
        PolicyNetwork as PolicyNetwork,
    )
    from cohezion.rl.trainer import (
        TrainingConfig as TrainingConfig,
    )


__all__ = [
    "CausalInterventionTester",
    "CoherenceReward",
    "CompositeReward",
    "DistributedConfig",
    "DistributedPPOTrainer",
    "DiversityBonus",
    "EVOTracker",
    "EpisodeResult",
    "EthericVariantOscillator",
    "FlumeNavEnv",
    "GRPOConfig",
    "GRPOTrainer",
    "HamiltonianReward",
    "InterpretabilityReport",
    "InterventionResult",
    "LoRAConfig",
    "PPOConfig",
    "PPOTrainer",
    "PolicyNetwork",
    "SFTTrainer",
    "StabilityPenalty",
    "TRIUNEPolicy",
    "TaskGenerator",
    "TaskSpec",
    "TrainingConfig",
]
