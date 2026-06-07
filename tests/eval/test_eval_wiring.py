"""Wiring test: eval/__init__ re-exports each eval module's primary class (wiring-sweep 2026-06-07).

Before this, the empty `eval/__init__.py` left `huggingface_export`/`pipeline`/`universe_evaluator`
reachable ONLY from the test suite (intra-package orphans). The re-export adds the missing static
production import edge.

Discriminating: each test asserts the name re-exported from the PACKAGE is the SAME object as the
class in its module — so removing or mis-pointing a re-export edge FAILS, not just "a name exists".
"""

from __future__ import annotations

import cohezion.eval as evalpkg
from cohezion.eval.capability_scorecard import CapabilityScorecard
from cohezion.eval.huggingface_export import HuggingFaceExporter
from cohezion.eval.pipeline import EvalPipeline
from cohezion.eval.universe_evaluator import UniverseEvaluator


def test_each_eval_module_reexported_is_the_real_class() -> None:
    assert evalpkg.CapabilityScorecard is CapabilityScorecard
    assert evalpkg.HuggingFaceExporter is HuggingFaceExporter
    assert evalpkg.EvalPipeline is EvalPipeline
    assert evalpkg.UniverseEvaluator is UniverseEvaluator


def test_all_lists_every_reexport() -> None:
    assert set(evalpkg.__all__) == {
        "CapabilityScorecard",
        "EvalPipeline",
        "HuggingFaceExporter",
        "UniverseEvaluator",
    }
