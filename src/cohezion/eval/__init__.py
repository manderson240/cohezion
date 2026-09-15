"""Eval — capability scoring, HuggingFace export, and universe evaluation."""

import contextlib


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
    from cohezion.eval.pipeline import PipelineProgress as PipelineProgress
    from cohezion.eval.pipeline import RalphLoopConfig as RalphLoopConfig

with contextlib.suppress(Exception):
    from cohezion.eval.universe_evaluator import EpisodeMetrics as EpisodeMetrics
    from cohezion.eval.universe_evaluator import PolicyEvaluation as PolicyEvaluation
    from cohezion.eval.universe_evaluator import UniverseEvaluator as UniverseEvaluator

with contextlib.suppress(Exception):
    from cohezion.eval.self_evaluating_system import (
        DeterministicEvaluator as DeterministicEvaluator,
    )
    from cohezion.eval.self_evaluating_system import (
        EvalResult as EvalResult,
    )
    from cohezion.eval.self_evaluating_system import (
        EvalRun as EvalRun,
    )
    from cohezion.eval.self_evaluating_system import (
        GoldenDataset as GoldenDataset,
    )
    from cohezion.eval.self_evaluating_system import (
        GoldenExample as GoldenExample,
    )
    from cohezion.eval.self_evaluating_system import (
        JudgeResult as JudgeResult,
    )
    from cohezion.eval.self_evaluating_system import (
        LocalLLMJudge as LocalLLMJudge,
    )
    from cohezion.eval.self_evaluating_system import (
        RegressionPipeline as RegressionPipeline,
    )
    from cohezion.eval.self_evaluating_system import (
        SelfEvaluatingOrchestrator as SelfEvaluatingOrchestrator,
    )
