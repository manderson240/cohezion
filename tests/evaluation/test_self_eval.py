"""Verification leg for evaluation.SelfEvaluationEngine (V-model audit, 2026-06-05).

PIN-ACTUAL pattern (see skill xfail-strict-bug-bridge-pattern §Companion): this module is
a STUB — evaluate_execution_plan ignores its inputs and returns a hardcoded score=0.92
("a real implementation would use Gemini 3 Pro"). These tests PIN the actual behavior and
the one piece of real logic (the threshold gate), and document the smell. The stub is
CALLED for real by compound/capability_matrix.py:504, so its always-pass behavior matters.
Flagged in docs/audits/VMODEL_AUDIT_2026-06-05.md §12.2. Remediation = separate gated track.
"""
from __future__ import annotations

from cohezion.evaluation.self_eval import SelfEvaluationEngine


def test_BUG_score_is_input_independent_stub() -> None:
    # BUG/stub: the score ignores plan and prd_context entirely (hardcoded 0.92). Two totally
    # different inputs yield an identical score. Pins current reality; a real impl must differ.
    eng = SelfEvaluationEngine()
    r1 = eng.evaluate_execution_plan("a tiny one-line plan", "PRD A")
    r2 = eng.evaluate_execution_plan("a completely different, enormous, contradictory plan", "PRD Z")
    assert r1.score == r2.score == 0.92


def test_threshold_gate_passes_at_default_threshold() -> None:
    r = SelfEvaluationEngine().evaluate_execution_plan("plan", "ctx")
    assert r.passed is True                       # 0.92 >= 0.85
    assert "coherence requirements" in r.feedback


def test_threshold_above_simulated_score_fails() -> None:
    # The ONE real branch: passed = score >= passing_threshold. With threshold 0.95, the
    # hardcoded 0.92 fails. Discriminates an inverted comparison or an unconditional pass.
    r = SelfEvaluationEngine(passing_threshold=0.95).evaluate_execution_plan("plan", "ctx")
    assert r.passed is False
    assert "Rewrite required" in r.feedback


def test_threshold_exactly_at_score_passes_boundary() -> None:
    # Boundary: >= is inclusive, so threshold exactly 0.92 must PASS.
    r = SelfEvaluationEngine(passing_threshold=0.92).evaluate_execution_plan("p", "c")
    assert r.passed is True
