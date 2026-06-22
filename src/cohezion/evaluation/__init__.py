"""Evaluation — self-evaluation engine for agent outputs."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.evaluation.self_eval import EvaluationResult as EvaluationResult
    from cohezion.evaluation.self_eval import SelfEvaluationEngine as SelfEvaluationEngine
