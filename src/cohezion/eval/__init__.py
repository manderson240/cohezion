"""Evaluation subsystem — capability scorecards, the eval pipeline, universe + HF export.

Public re-exports so each eval module is reachable from a STATIC production import edge, not
only from the test suite. Before this, `eval/__init__.py` was empty, leaving `huggingface_export`,
`pipeline`, and `universe_evaluator` as intra-package orphans (imported by `tests/eval/*` alone);
`capability_scorecard` was already reached by `compound/capability_matrix`. Re-exported here for a
uniform surface (wiring-sweep, 2026-06-07). The `X as X` alias marks each an intentional re-export.
"""

from cohezion.eval.capability_scorecard import CapabilityScorecard as CapabilityScorecard
from cohezion.eval.huggingface_export import HuggingFaceExporter as HuggingFaceExporter
from cohezion.eval.pipeline import EvalPipeline as EvalPipeline
from cohezion.eval.universe_evaluator import UniverseEvaluator as UniverseEvaluator


__all__ = [
    "CapabilityScorecard",
    "EvalPipeline",
    "HuggingFaceExporter",
    "UniverseEvaluator",
]
