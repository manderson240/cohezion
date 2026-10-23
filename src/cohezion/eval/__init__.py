"""Eval — capability scoring, HuggingFace export, and universe evaluation."""

import contextlib


__all__ = [
    "CapabilityScorecard",
    "EvalPipeline",
    "HuggingFaceExporter",
    "UniverseEvaluator",
]


with contextlib.suppress(Exception):
    from cohezion.eval.capability_scorecard import CapabilityScorecard as CapabilityScorecard
    from cohezion.eval.capability_scorecard import StatisticalComparison as StatisticalComparison

with contextlib.suppress(Exception):
    from cohezion.eval.huggingface_export import HuggingFaceExporter as HuggingFaceExporter

with contextlib.suppress(Exception):
    from cohezion.eval.self_eval import EvaluationResult as EvaluationResult
    from cohezion.eval.self_eval import SelfEvaluationEngine as SelfEvaluationEngine

with contextlib.suppress(Exception):
    from cohezion.eval.pipeline import EpisodeResult as EpisodeResult
    from cohezion.eval.pipeline import EvalPipeline as EvalPipeline
    from cohezion.eval.pipeline import PipelineProgress as PipelineProgress
    from cohezion.eval.pipeline import RalphLoopConfig as RalphLoopConfig

with contextlib.suppress(Exception):
    from cohezion.eval.universe_evaluator import EpisodeMetrics as EpisodeMetrics
    from cohezion.eval.universe_evaluator import PolicyEvaluation as PolicyEvaluation
    from cohezion.eval.universe_evaluator import UniverseEvaluator as UniverseEvaluator

# Guarded imports above may fail; list only names that actually bound, so
# `from <package> import *` cannot raise on a missing optional dependency.
__all__ = [_name for _name in __all__ if _name in globals()]
