"""RubricMiddleware — structured task output verification via Lemonade :13305.

Evaluates compound executor outputs against a caller-supplied rubric before
they are persisted to the semantic cache or used as MGPO learning signal.

Architecture (from LangChain trace-judge pattern):
  - System prompt: rubric definition
  - User message: task output to evaluate
  - Response format: JSON {"perceived_error": bool, "reason": str}
  - Fail-open: any inference or parse failure → RubricVerdict(passed=True)

Wiring in CompoundExecutor:
  Between success determination and Step 7 (skill refinement / MGPO accumulation).
  Failed verdict → should_refine=False, MGPO skip — keeps bad outputs out of
  the learning substrate.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field


try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_ROUTER_URL = "http://localhost:13305/v1/chat/completions"

_SYSTEM_TEMPLATE = """\
You are a task output judge. Evaluate the user-provided output against the rubric below.

Rubric:
{rubric}

Respond ONLY with valid JSON in exactly this format:
{{"perceived_error": <true|false>, "reason": "<one sentence explanation>"}}

perceived_error must be true if the output violates the rubric, false otherwise."""

# Appended only while qualify(metric="auc") runs: the judge also reports a rankable suspicion score.
_SCORE_SUFFIX = """

Also include a numeric "score" field: how likely the output is to violate the rubric \
(higher = more likely an error). Exact format: \
{"perceived_error": <true|false>, "score": <number>, "reason": "<one sentence>"}"""


@dataclass
class RubricVerdict:
    """Structured judgment from RubricMiddleware.evaluate()."""

    passed: bool
    reason: str
    raw_response: str = field(default="")


class RubricMiddleware:
    """Evaluates task outputs against a rubric via Lemonade :13305.

    Usage::

        rm = RubricMiddleware(rubric="Output must be factually grounded.")
        verdict = rm.evaluate(task_output=result.output, task_context=skill_name)
        if not verdict.passed:
            logger.info("Rubric rejected: %s", verdict.reason)
    """

    def __init__(
        self,
        rubric: str,
        model: str | None = None,
        timeout: float = 10.0,
        router_url: str = _ROUTER_URL,
        require_qualification: bool = False,
    ) -> None:
        self.rubric = rubric
        self._model = model
        self._timeout = timeout
        self._router_url = router_url
        # RQ (salted calibration, from the GEMS judge desk 2026-10-16): None = never qualified, True/False = qualify() result.
        # A judge that failed qualify(), or that must qualify and has not, never gates the learning substrate.
        self.require_qualification = require_qualification
        self.qualified: bool | None = None
        self.qualification_score: float | None = None
        self._metric = "balanced_accuracy"  # metric of the last qualify(); evaluate() follows it
        self._score_cut: float | None = None  # learned decision cut (auc qualification only)
        self._qualified_for: tuple | None = (
            None  # (rubric, model, router_url, metric, score_cut) the qualification measured
        )

    def _fingerprint(self) -> tuple:
        return (self.rubric, self._model, self._router_url, self._metric, self._score_cut)

    def is_qualified(self) -> bool | None:
        """True/False from qualify(); None if never qualified. A True that does not match the current judge
        (rubric/model/router changed, or `qualified` set by hand) is False: the measurement was of another judge."""
        q = getattr(self, "qualified", None)
        if q is True and getattr(self, "_qualified_for", None) != self._fingerprint():
            return False
        return q

    def qualify(
        self,
        gold: list[tuple[str, str, bool]],
        threshold: float = 0.8,
        min_per_class: int = 2,
        metric: str = "balanced_accuracy",
    ) -> float:
        """Score the judge on known answers: gold = [(task_output, task_context, should_fail)].

        Returns BALANCED accuracy (mean of per-class recall; plain accuracy would let a one-sided judge pass a skewed
        gold set) and sets `qualified`. Unparseable, non-boolean or failed answers count as WRONG: the evaluate()
        fail-open default would otherwise read every one as a correct pass.

        metric="auc": the judge's JSON reply carries a numeric `score` (higher = more likely an error) and the
        result is the Mann-Whitney ROC AUC (ties = 0.5) of known-bad over known-good items, so a judge that ranks
        perfectly but whose scores sit on the wrong side of any fixed cut still qualifies. Fail-closed: a missing,
        unparseable, non-numeric or non-finite score takes the WORST rank for its class (known-bad = least
        suspicious, known-good = most suspicious). NOTE: this qualifies RANKING; evaluate() still acts on the
        boolean `perceived_error`, whose calibration AUC does not measure.
        """
        if metric not in ("balanced_accuracy", "auc"):
            raise ValueError(f"unknown qualify metric {metric!r}: use 'balanced_accuracy' or 'auc'")
        if not 0.5 < threshold <= 1.0:
            raise ValueError(
                "threshold must be in (0.5, 1.0]: at or below 0.5 a coin flip qualifies"
            )
        pos = [g for g in gold if g[2]]
        neg = [g for g in gold if not g[2]]
        if len(pos) < min_per_class or len(neg) < min_per_class:
            raise ValueError(
                f"qualify() needs >= {min_per_class} known-bad and >= {min_per_class} known-good items"
            )
        self.qualified = False  # never gate while (re)qualifying

        self._metric, self._score_cut = metric, None
        if metric == "auc":
            score, self._score_cut = self._auc_score(pos, neg)
            self.qualification_score = score
            self._qualified_for = self._fingerprint()
            self.qualified = score >= threshold - 1e-9
            logger.info("RubricMiddleware qualify: AUC %.3f -> qualified=%s", score, self.qualified)
            return score

        def correct(item: tuple[str, str, bool]) -> bool:
            try:
                data = json.loads(self._call_inference(item[0], item[1]))
                v = data.get("perceived_error") if isinstance(data, dict) else None
                return isinstance(v, bool) and v == item[2]
            except Exception:
                return False

        hits_pos, hits_neg = sum(map(correct, pos)), sum(map(correct, neg))
        score = (hits_pos / len(pos) + hits_neg / len(neg)) / 2
        self.qualification_score = score
        self._qualified_for = self._fingerprint()
        self.qualified = score >= threshold - 1e-9
        logger.info(
            "RubricMiddleware qualify: balanced accuracy %.3f -> qualified=%s",
            score,
            self.qualified,
        )
        return score

    def _item_score(self, item: tuple[str, str, bool]) -> float:
        """Judge's suspicion score for one gold item; worst rank for its class when unusable (fail-closed)."""
        worst = -math.inf if item[2] else math.inf
        try:
            data = json.loads(self._call_inference(item[0], item[1], want_score=True))
            v = data.get("score") if isinstance(data, dict) else None
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                return worst
            return float(v)
        except Exception:
            return worst

    def _auc_score(
        self, pos: list[tuple[str, str, bool]], neg: list[tuple[str, str, bool]]
    ) -> tuple[float, float]:
        """(Mann-Whitney AUC, Youden cut) over the gold scores.

        AUC = P(bad outranks good) + 0.5 * P(tie). The cut is t* = argmax_t TPR(t) - FPR(t) over the observed
        usable scores (flag iff score >= t), ties broken toward the HIGHER cut (fewer false rejections): derived
        from measured outcomes, never from the judge's own scale. No usable score at all -> inf (never rejects).
        """
        ps = [self._item_score(g) for g in pos]
        ns = [self._item_score(g) for g in neg]
        wins = sum((p > n) + 0.5 * (p == n) for p in ps for n in ns)
        cuts = sorted({x for x in ps + ns if math.isfinite(x)})
        best_cut, best_j = math.inf, -math.inf
        for t in cuts:  # ascending: ">=" lets a later (higher) cut win ties
            j = sum(p >= t for p in ps) / len(ps) - sum(n >= t for n in ns) / len(ns)
            if j >= best_j:
                best_cut, best_j = t, j
        return wins / (len(ps) * len(ns)), best_cut

    def evaluate(
        self,
        task_output: str,
        task_context: str = "",
    ) -> RubricVerdict:
        """Evaluate task_output against the rubric.

        Returns RubricVerdict(passed=True) on any inference or parse failure
        (fail-open) so the learning loop is never blocked by infrastructure.
        """
        q = self.is_qualified()
        if q is False or (getattr(self, "require_qualification", False) and q is None):
            return RubricVerdict(
                passed=True,
                reason="unqualified judge: verdict not used (fail-open)",
                raw_response="",
            )
        if q is True and self._metric == "auc" and self._score_cut is not None:
            return self._evaluate_by_score(task_output, task_context)
        try:
            raw = self._call_inference(task_output, task_context)
            return self._parse_verdict(raw)
        except Exception as exc:
            logger.debug("RubricMiddleware: evaluation failed (fail-open): %s", exc)
            return RubricVerdict(passed=True, reason="", raw_response="")

    def _evaluate_by_score(self, task_output: str, task_context: str) -> RubricVerdict:
        """AUC-qualified judges gate on score >= learned cut, never on their own boolean (AUC never measured it).

        Asymmetry by design: qualify() is fail-closed (an unusable gold score takes the worst rank), but here an
        unusable score or failed call PASSES -- evaluate() never rejects on noise, keeping its fail-open contract.
        """
        cut = self._score_cut
        if cut is None:  # only reachable if the cut was cleared mid-flight: never gate without one
            return RubricVerdict(passed=True, reason="", raw_response="")
        try:
            raw = self._call_inference(task_output, task_context, want_score=True)
            data = json.loads(raw)
            v = data.get("score") if isinstance(data, dict) else None
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                return RubricVerdict(passed=True, reason="", raw_response=raw)
            flagged = v >= cut
            reason = str(data.get("reason", "")) if isinstance(data, dict) else ""
            return RubricVerdict(passed=not flagged, reason=reason, raw_response=raw)
        except Exception as exc:
            logger.debug("RubricMiddleware: score evaluation failed (fail-open): %s", exc)
            return RubricVerdict(passed=True, reason="", raw_response="")

    # ── internal ──────────────────────────────────────────────────────────

    def _build_messages(
        self, task_output: str, task_context: str, want_score: bool = False
    ) -> list[dict]:
        system_content = _SYSTEM_TEMPLATE.format(rubric=self.rubric)
        if want_score:  # explicit argument, not instance state: concurrent calls must not share it
            system_content += _SCORE_SUFFIX
        user_content = task_output
        if task_context:
            user_content = f"[Context: {task_context}]\n\n{task_output}"
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def _call_inference(self, task_output: str, task_context: str, want_score: bool = False) -> str:
        body: dict = {
            "messages": self._build_messages(task_output, task_context, want_score),
            "response_format": {"type": "json_object"},
            "max_tokens": 256,
            "temperature": 0.0,
        }
        if self._model is not None:
            body["model"] = self._model

        resp = httpx.post(  # type: ignore[reportOptionalMemberAccess]
            self._router_url,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def _parse_verdict(self, raw: str) -> RubricVerdict:
        try:
            data = json.loads(raw)
            perceived_error = data.get("perceived_error")
            if perceived_error is None:
                # Key missing → fail-open
                return RubricVerdict(passed=True, reason="", raw_response=raw)
            reason = str(data.get("reason", ""))
            return RubricVerdict(
                passed=not bool(perceived_error),
                reason=reason,
                raw_response=raw,
            )
        except (TypeError, KeyError, ValueError) as exc:
            logger.debug("RubricMiddleware: parse failed (fail-open): %s", exc)
            return RubricVerdict(passed=True, reason="", raw_response=raw)
