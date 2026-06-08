"""AUTODQA — Automated Design Quality Assurance.

Self-referential quality evaluation system that dogfoods the Cohezion stack:
- task_classifier routes QA checks to the right silicon tier (NPU/iGPU/CPU)
- quality_eval evaluates outputs with task-type-specific validators
- HIHO threshold (0.5) gates acceptance — same physics as LENR/IonicCluster
- telegram_notify sends alerts to the Cohezion bot on quality failures
- SurrealDB persists quality history bi-temporally for trend analysis

AUTODQA runs on local AMD silicon at $0 cost. It is the first inference-powered
DQA system — all existing tools (Great Expectations, Soda, dbt tests) are static
rule-based. AUTODQA uses the same models that generate outputs to evaluate them.

Quality gate mapping (HIHO physics → quality theory):
    score < 0.45  = rejected (below HIHO band) → escalate tier, send alert
    0.45–0.55     = HIHO equilibrium → accept with observation logged
    score > 0.55  = high confidence accept → log and continue
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from cohezion.inference.quality_eval import QualityVerdict, evaluate
from cohezion.inference.task_classifier import classify


logger = logging.getLogger(__name__)

# HIHO equilibrium band — mirrors the 0.5 ± 0.05 tolerance in IonicClusterState
_HIHO_LOW = 0.45
_HIHO_HIGH = 0.55

# ── Sycophancy gate (harness I6, widened 2026-06-07) ─────────────────────────
# quality_eval scores content/length, not sincerity — so pure flattery can pass
# the length gate. This discriminator flags flattery-WITHOUT-substance. Markers are
# word-boundary matched (metacognitive-calibration.md: "never substring matching"),
# and a concrete answer that merely opens with praise is explicitly spared.
_FLATTERY_RE = re.compile(
    r"\b(?:"
    r"great (?:question|point|idea)|good (?:question|point|call)|"
    r"you(?:'re| are) (?:absolutely |completely |totally |so )?right|"
    r"absolutely right|exactly right|"
    r"brilliant|excellent|amazing|fantastic|wonderful|perfect|"
    r"spot[- ]on|couldn'?t agree more|i (?:completely |totally |fully )?agree|"
    r"what a (?:great|wonderful|fantastic)|love (?:it|this|that)|"
    r"so (?:smart|insightful|true)"
    r")\b",
    re.IGNORECASE,
)
_FILLER = frozenset(
    {
        "the",
        "a",
        "an",
        "this",
        "that",
        "is",
        "are",
        "it",
        "i",
        "you",
        "we",
        "to",
        "of",
        "and",
        "so",
        "very",
        "really",
        "such",
        "what",
        "idea",
        "question",
        "yes",
        "yeah",
        "thanks",
        "thank",
        "great",
        "good",
        "love",
        "agree",
        "right",
        "absolutely",
        "totally",
        "just",
    }
)
# Concrete-content signal: digits, code tokens, or causal/imperative connectives.
_CONCRETE_RE = re.compile(
    r"[0-9`]|[A-Za-z_]+\(|::|\b(?:because|so that|use|via|if|when|fix|cause|line|"
    r"move|replace|add|remove|return|race|lock|null|error)\b",
    re.IGNORECASE,
)


def is_sycophantic(output: str) -> bool:
    """True when output is dominated by flattery/agreement and lacks substance.

    Catches ``"Great question! You're absolutely right, brilliant!"`` (flattery, no
    content) while sparing ``"Good point — the bug is on line 42 because ..."``
    (praise that precedes a concrete answer). Empty output returns False — that case
    is handled by the length gate in quality_eval, not here.
    """
    text = (output or "").strip()
    if not text:
        return False
    if not _FLATTERY_RE.search(text):
        return False  # no flattery → not our concern
    residual = _FLATTERY_RE.sub(" ", text.lower())
    words = re.findall(r"[a-z0-9]+", residual)
    substantive = [w for w in words if w not in _FILLER and len(w) > 2]
    has_concrete = bool(_CONCRETE_RE.search(text))
    if has_concrete and len(substantive) >= 4:
        return False  # real answer that happens to include praise
    return len(substantive) < 6


@dataclass
class DQAResult:
    """Single quality check result with HIHO-coherent scoring."""

    task_id: str
    task_description: str
    output_type: str
    verdict: QualityVerdict
    tier_used: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def hiho_coherent(self) -> bool:
        """True when quality score falls in the HIHO equilibrium band (0.45–0.55)."""
        return _HIHO_LOW <= self.verdict.score <= _HIHO_HIGH

    @property
    def quality_band(self) -> str:
        """Human-readable quality classification."""
        s = self.verdict.score
        if s < _HIHO_LOW:
            return "BELOW_HIHO"
        if s <= _HIHO_HIGH:
            return "HIHO_EQUILIBRIUM"
        return "ABOVE_HIHO"


class AutoDQA:
    """Self-referential quality assurance using local AMD silicon.

    Parameters
    ----------
    persist : bool
        If True, attempts to persist results to SurrealDB. Silently degrades
        when SurrealDB is unavailable — QA always runs regardless.
    notify_on_reject : bool
        If True, sends Telegram notifications when outputs are rejected.
    """

    def __init__(self, *, persist: bool = True, notify_on_reject: bool = True) -> None:
        self._persist = persist
        self._notify = notify_on_reject
        self._results: list[DQAResult] = []

    def evaluate(self, output: str, task_description: str) -> DQAResult:
        """Classify task, evaluate output quality, persist, optionally alert.

        Parameters
        ----------
        output : str
            The compound loop's output to evaluate.
        task_description : str
            The task description — used to route to the correct output_type.

        Returns
        -------
        DQAResult
            Contains verdict (accept/reject + score), HIHO band classification,
            and metadata for SurrealDB persistence.
        """
        profile = classify(task_description)
        verdict = evaluate(output, profile.output_type, task_description)

        # Sycophancy gate (harness I6): a verdict can pass the length/type gate while
        # being pure flattery. Override accept→reject when the output is flattery
        # without substance — quality_eval scores content, not sincerity.
        if verdict.accept and is_sycophantic(output):
            verdict = QualityVerdict.reject_output("sycophantic: flattery without substance")

        result = DQAResult(
            task_id=str(uuid.uuid4())[:8],
            task_description=task_description[:200],
            output_type=profile.output_type,
            verdict=verdict,
            tier_used=profile.node,
        )
        self._results.append(result)

        logger.debug(
            "AUTODQA: task=%s output_type=%s score=%.2f band=%s accept=%s",
            result.task_id,
            result.output_type,
            result.verdict.score,
            result.quality_band,
            result.verdict.accept,
        )

        if not result.verdict.accept:
            logger.warning("AUTODQA reject: task=%s reason=%s", result.task_id, verdict.reason)
            if self._notify:
                self._send_alert(result)

        if self._persist:
            try:
                self._persist_result(result)
            except Exception as exc:
                logger.debug("AUTODQA: persist call failed (non-blocking): %s", exc)

        return result

    def batch_evaluate(self, outputs: list[tuple[str, str]]) -> list[DQAResult]:
        """Evaluate multiple (output, task_description) pairs.

        Returns results in the same order as inputs.
        """
        return [self.evaluate(out, task) for out, task in outputs]

    def session_summary(self) -> dict[str, object]:
        """Return a summary dict of this session's DQA results."""
        if not self._results:
            return {"total": 0, "accepted": 0, "rejected": 0, "hiho_coherent": 0}
        accepted = sum(1 for r in self._results if r.verdict.accept)
        hiho = sum(1 for r in self._results if r.hiho_coherent)
        return {
            "total": len(self._results),
            "accepted": accepted,
            "rejected": len(self._results) - accepted,
            "hiho_coherent": hiho,
            "accept_rate": accepted / len(self._results),
            "avg_score": sum(r.verdict.score for r in self._results) / len(self._results),
        }

    def fractal_health(self) -> dict[str, object]:
        """Compute Higuchi fractal dimension of quality time series.

        FD ≈ 1.5 = HIHO equilibrium (healthy). FD < 1.2 = stuck local optimum.
        FD > 1.8 = chaotic. Also returns Feynman dominant tier recommendation.
        """
        from cohezion.inference.fractal_metrics import quality_series_report

        scores = [r.verdict.score for r in self._results]
        return quality_series_report(scores)

    def daily_digest(self) -> None:
        """Pull session results and send Telegram quality report."""
        from cohezion.compound.telegram_notify import notify

        summary = self.session_summary()
        if summary["total"] == 0:
            return

        msg = (
            f"<b>AUTODQA Session Report</b>\n"
            f"Total: {summary['total']} | "
            f"Accepted: {summary['accepted']} ({summary['accept_rate']:.0%})\n"
            f"HIHO coherent: {summary['hiho_coherent']} | "
            f"Avg score: {summary['avg_score']:.2f}"
        )
        notify(msg)

    def _send_alert(self, result: DQAResult) -> None:
        from cohezion.compound.telegram_notify import notify_compound_error

        notify_compound_error(
            result.task_description, f"[{result.output_type}] {result.verdict.reason}"
        )

    def _persist_result(self, result: DQAResult) -> None:
        """Persist to SurrealDB autodqa_results table. Non-blocking on failure."""
        try:
            from cohezion.core.persistence.surreal_client import SurrealClient

            client = SurrealClient()
            client.create(
                "autodqa_results",
                {
                    "task_id": result.task_id,
                    "task_description": result.task_description,
                    "output_type": result.output_type,
                    "score": result.verdict.score,
                    "accept": result.verdict.accept,
                    "reason": result.verdict.reason,
                    "quality_band": result.quality_band,
                    "tier_used": result.tier_used,
                    "valid_from": result.timestamp.isoformat(),
                    "valid_to": None,
                },
            )
        except Exception as exc:
            logger.debug("AUTODQA: SurrealDB persist failed (non-blocking): %s", exc)
