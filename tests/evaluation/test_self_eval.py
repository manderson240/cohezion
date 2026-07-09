"""Tests for evaluation.SelfEvaluationEngine.

FIXED 2026-06-06 (backlog item 8 / audit §12.2): evaluate_execution_plan was a STUB that
discarded both arguments and returned a hardcoded 0.92, so the gate ALWAYS passed (a fake
green light, called for real by compound/capability_matrix.py). The score now DEPENDS on the
input (deterministic heuristic over structure, substance, and PRD keyword overlap). These
tests assert the FIXED behavior (the formerly-pinned "input-independent stub" test was flipped
deliberately); each fails a plausible wrong impl:
  - a hardcoded/again-input-independent score,
  - an empty plan that still passes the gate,
  - an inverted or unconditional threshold comparison,
  - a non-deterministic (model-call) score.
"""

from __future__ import annotations

from cohezion.evaluation.self_eval import SelfEvaluationEngine


# All 8 context content-words appear in the plan → overlap 1.0 → score saturates well above 0.85.
GOOD_CTX = "authentication login endpoint module tests validation hashing credentials"
GOOD_PLAN = (
    "1. Implement the authentication module with password hashing.\n"
    "2. Add a login endpoint and validation of credentials.\n"
    "3. Write tests for authentication, login, and validation."
)


def test_score_depends_on_input_not_hardcoded() -> None:
    # The §12.2 fix: score is a function of the input. Three different inputs → three scores.
    eng = SelfEvaluationEngine()
    good = eng.evaluate_execution_plan(GOOD_PLAN, GOOD_CTX)
    poor = eng.evaluate_execution_plan("fix it", GOOD_CTX)  # non-empty but no structure/overlap
    empty = eng.evaluate_execution_plan("", GOOD_CTX)
    assert good.score > poor.score > empty.score
    assert empty.score == 0.0


def test_empty_plan_fails_the_gate() -> None:
    r = SelfEvaluationEngine().evaluate_execution_plan("", "ctx")
    assert r.score == 0.0
    assert r.passed is False
    assert "Rewrite required" in r.feedback


def test_substantive_matching_plan_passes() -> None:
    r = SelfEvaluationEngine().evaluate_execution_plan(GOOD_PLAN, GOOD_CTX)
    assert r.passed is True
    assert r.score >= 0.85
    assert "coherence requirements" in r.feedback


def test_high_threshold_fails_a_mediocre_plan() -> None:
    # The real gate branch: passed = score >= threshold. A structured-but-context-poor plan
    # (~0.6) fails a 0.95 threshold. Discriminates an inverted/unconditional comparison.
    r = SelfEvaluationEngine(passing_threshold=0.95).evaluate_execution_plan(
        "1. do a thing", "unrelated context xyz"
    )
    assert r.passed is False


def test_score_is_deterministic() -> None:
    eng = SelfEvaluationEngine()
    a = eng.evaluate_execution_plan(GOOD_PLAN, GOOD_CTX).score
    b = eng.evaluate_execution_plan(GOOD_PLAN, GOOD_CTX).score
    assert a == b  # no model call / no randomness
