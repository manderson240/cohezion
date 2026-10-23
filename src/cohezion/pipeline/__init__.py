"""Pipeline module — connects mass sim, training, and weight transfer."""

import contextlib


__all__: list[str] = []

with contextlib.suppress(Exception):
    from cohezion.pipeline.hyperparameter_debate import HyperparameterDebate as HyperparameterDebate

    __all__ += ["HyperparameterDebate"]

with contextlib.suppress(Exception):
    from cohezion.pipeline.incremental_trainer import IncrementalResult as IncrementalResult
    from cohezion.pipeline.incremental_trainer import IncrementalRLTrainer as IncrementalRLTrainer
    from cohezion.pipeline.incremental_trainer import IncrementalVAETrainer as IncrementalVAETrainer

    __all__ += ["IncrementalResult", "IncrementalRLTrainer", "IncrementalVAETrainer"]

with contextlib.suppress(Exception):
    from cohezion.pipeline.trained_navigator import TrainedNavigator as TrainedNavigator

    __all__ += ["TrainedNavigator"]

with contextlib.suppress(Exception):
    from cohezion.pipeline.weight_bridge import WeightBridge as WeightBridge

    __all__ += ["WeightBridge"]
