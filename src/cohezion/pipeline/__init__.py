"""Pipeline module — connects mass sim, training, and weight transfer."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.pipeline.hyperparameter_debate import HyperparameterDebate as HyperparameterDebate

with contextlib.suppress(Exception):
    from cohezion.pipeline.incremental_trainer import IncrementalResult as IncrementalResult
    from cohezion.pipeline.incremental_trainer import IncrementalRLTrainer as IncrementalRLTrainer
    from cohezion.pipeline.incremental_trainer import IncrementalVAETrainer as IncrementalVAETrainer

with contextlib.suppress(Exception):
    from cohezion.pipeline.trained_navigator import TrainedNavigator as TrainedNavigator

with contextlib.suppress(Exception):
    from cohezion.pipeline.weight_bridge import WeightBridge as WeightBridge
