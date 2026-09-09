"""Unit tests for DynamicModelEvaluator."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cohezion.inference.dynamic_model_evaluator import (
    DynamicModelEvaluator,
    ModelEvaluationScorecard,
)


@pytest.fixture
def evaluator() -> DynamicModelEvaluator:
    return DynamicModelEvaluator()


def test_verify_python_code_valid(evaluator: DynamicModelEvaluator):
    code_text = "```python\ndef is_even(n):\n    return n % 2 == 0\n```"

    def test_fn(env):
        fn = env.get("is_even")
        assert fn is not None
        return 1.0 if fn(4) is True and fn(5) is False else 0.0

    syntax_ok, pass_rate, _ = evaluator.verify_python_code(code_text, test_fn)
    assert syntax_ok is True
    assert pass_rate == 1.0


def test_verify_python_code_syntax_error(evaluator: DynamicModelEvaluator):
    broken_code = "```python\ndef bad_syntax(\n```"
    syntax_ok, pass_rate, _ = evaluator.verify_python_code(broken_code, lambda env: 1.0)
    assert syntax_ok is False
    assert pass_rate == 0.0


def test_compute_evi_no_escalation(evaluator: DynamicModelEvaluator):
    # High quality (0.90) -> small gap -> low EVI -> no escalation needed
    evi, escalate = evaluator.compute_evi(quality_score=0.90, task_importance=0.8)
    assert escalate is False
    assert evi <= 0.75


def test_compute_evi_escalation_required(evaluator: DynamicModelEvaluator):
    # Low quality (0.20) on high importance task -> large gap -> high EVI -> escalate!
    evi, escalate = evaluator.compute_evi(
        quality_score=0.20, task_importance=0.9, escalation_cost=0.5
    )
    assert escalate is True
    assert evi > 0.75


def test_evaluate_model_on_task_with_mock(evaluator: DynamicModelEvaluator):
    mock_resp = "```python\ndef double(x):\n    return x * 2\n```"
    with patch.object(evaluator, "query_model", return_value=(mock_resp, 120.5, 45.0)):
        scorecard = evaluator.evaluate_model_on_task(
            model="test-model",
            task_id="test_double",
            prompt="write double",
            test_fn=lambda env: 1.0 if env["double"](3) == 6 else 0.0,
            hardware_lane="NPU",
        )
        assert isinstance(scorecard, ModelEvaluationScorecard)
        assert scorecard.syntax_valid is True
        assert scorecard.test_pass_rate == 1.0
        assert scorecard.quality_score == 1.0
        assert scorecard.escalation_required is False
