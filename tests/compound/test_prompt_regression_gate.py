"""Behavioral regression gate (FAPO R3) — defends the compound self-improvement loop from QUIET
prompt regression (a skill edit that fixes one case while silently breaking others). run_fn mocked.
"""
from __future__ import annotations

from cohezion.compound.prompt_version_registry import _validate, evaluate_regression


class TestValidator:
    def test_contains_default(self):
        assert _validate("the answer is NEGATIVE", "negative") is True
        assert _validate("POSITIVE", "negative") is False

    def test_exact(self):
        assert _validate(" B ", "B", "exact") is True
        assert _validate("B.", "B", "exact") is False

    def test_regex_and_malformed(self):
        assert _validate("score: 0.95", r"score:\s*\d\.\d+", "regex") is True
        assert _validate("no score", r"score:\s*\d", "regex") is False
        assert _validate("x", "(unclosed", "regex") is True  # malformed → don't block


def _fixtures():
    return [
        {"input": "is 2+2=5?", "expected_output": "no", "critical": True},
        {"input": "say hi", "expected_output": "hi", "critical": True},
    ]


class TestEvaluateRegression:
    def test_all_pass_promotes(self):
        ans = {"is 2+2=5?": "no, that's wrong", "say hi": "hi there"}
        assert evaluate_regression(_fixtures(), "cand", lambda c, i: ans[i]) is True

    def test_critical_regression_blocks(self):
        """Discriminating: a candidate that breaks a CRITICAL fixture is blocked. A no-eval impl
        (always promote → True) fails this."""
        ans = {"is 2+2=5?": "yes!", "say hi": "hi there"}  # first critical fixture regressed
        assert evaluate_regression(_fixtures(), "cand", lambda c, i: ans[i]) is False

    def test_noncritical_failure_allowed(self):
        fx = [{"input": "x", "expected_output": "y", "critical": False}]
        assert evaluate_regression(fx, "cand", lambda c, i: "wrong") is True

    def test_execution_error_fails_open(self):
        def boom(c, i):
            raise RuntimeError("inference down")

        assert evaluate_regression(_fixtures(), "cand", boom) is True

    def test_false_improvement_detected(self):
        """The article's failure mode: aggregate looks OK (1/2 pass) but a CRITICAL category broke."""
        ans = {"is 2+2=5?": "yes", "say hi": "hi"}  # 1 pass, 1 critical fail
        assert evaluate_regression(_fixtures(), "cand", lambda c, i: ans[i]) is False
