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

# Restored 2026-11-04: #242 (853084c05) squash-merged the wiring test for this edge but not
# the __init__ change, so the test failed on main from the day it landed.
# Only names whose guarded import succeeded, so `from ... import *` never breaks.
__all__ = [
    _name
    for _name in (
        "HyperparameterDebate",
        "IncrementalRLTrainer",
        "IncrementalResult",
        "IncrementalVAETrainer",
        "TrainedNavigator",
        "WeightBridge",
    )
    if _name in globals()
]
