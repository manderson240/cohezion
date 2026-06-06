"""SELF_EVALUATION_PRIME pre-flight checks before code execution."""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel


logger = logging.getLogger(__name__)

_STRUCTURE_RE = re.compile(r"(^|\n)\s*(\d+[.)]|[-*]|step\b)", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-z0-9]+")


class EvaluationResult(BaseModel):
    """Result of a self-evaluation pre-flight check."""

    score: float
    passed: bool
    feedback: str


class SelfEvaluationEngine:
    """Enforces quality thresholds before agentic execution."""

    passing_threshold: float

    def __init__(self, passing_threshold: float = 0.85) -> None:
        self.passing_threshold = passing_threshold

    @staticmethod
    def _score_plan(plan: str, prd_context: str) -> float:
        """Deterministic, input-DEPENDENT coherence score in [0, 1] (FIX 2026-06-06, §12.2).

        The prior impl discarded both arguments and returned a hardcoded 0.92, so the gate
        ALWAYS passed regardless of input (a fake green light). This scores real signals:
        a non-empty plan earns base credit; structural steps, adequate substance, and keyword
        overlap with the PRD context add to it. An empty/trivial plan scores low and FAILS the
        gate; a substantive plan that addresses the PRD scores high and passes. No model call —
        deterministic and offline (a model-backed scorer can replace this behind the same API).
        """
        text = (plan or "").strip()
        if not text:
            return 0.0
        score = 0.4  # base credit for a non-empty plan
        if _STRUCTURE_RE.search(text):
            score += 0.2  # structural coherence (numbered/bulleted/"step")
        if len(text) >= 80:
            score += 0.1  # adequate substance (not a one-liner)
        ctx = (prd_context or "").strip()
        if ctx:
            ctx_words = set(_WORD_RE.findall(ctx.lower()))
            plan_words = set(_WORD_RE.findall(text.lower()))
            overlap = len(ctx_words & plan_words) / max(1, len(ctx_words))
            score += 0.3 * overlap  # relevance to the PRD context
        return round(min(1.0, score), 4)

    def evaluate_execution_plan(self, plan: str, prd_context: str) -> EvaluationResult:
        """Evaluate an execution plan against PRD context and R-Zero metrics."""
        logger.debug("Evaluating execution plan for SELF_EVALUATION_PRIME coherence...")

        score = self._score_plan(plan, prd_context)

        passed = score >= self.passing_threshold
        feedback = (
            "Plan meets architectural coherence requirements."
            if passed
            else "Plan coherence too low. Rewrite required."
        )

        if not passed:
            logger.warning(
                f"Self-Evaluation failed: Score {score:.2f} < {self.passing_threshold:.2f}"
            )
        else:
            logger.info(f"Self-Evaluation passed: Score {score:.2f}")

        return EvaluationResult(score=score, passed=passed, feedback=feedback)
