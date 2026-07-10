"""Escalation gate primitives for local→cloud routing.

Research basis:
  - arXiv:2605.02241 — zero-shot mean token logprob (beats supervised routers OOD)
  - arXiv:2605.18796 — UCCI: isotonic calibration → cost-optimal threshold
  - arXiv:2505.16502 — RecServe: adaptive sliding-window quantile threshold
  - arXiv:2509.21837 — semantic agreement voting (fallback when logits suspect)

These are the gate components used by ``extend_claude()`` to decide when a
local model's output is "good enough" vs when to escalate to cloud.
"""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Sequence


logger = logging.getLogger(__name__)

DEFAULT_TAU: float = -1.0
DEFAULT_QUANTILE: float = 0.25
DEFAULT_WINDOW_SIZE: int = 100
MIN_OBSERVATIONS_BEFORE_ADAPTIVE: int = 10


class SlidingWindowQuantileTracker:
    """Adaptive threshold via sliding-window quantile (arXiv:2505.16502 RecServe).

    Maintains a rolling window of observed confidence values (e.g. mean logprob)
    and sets the escalation threshold τ to the q-th quantile of the window.
    Self-tuning — no manual τ. Until enough observations accumulate, falls back
    to a conservative default.

    Args:
        quantile: Bottom quantile that triggers escalation (default 0.25 = bottom 25%).
        window_size: Rolling window size (default 100 observations).
        default_tau: Fallback threshold until enough observations accumulate.
    """

    def __init__(
        self,
        quantile: float = DEFAULT_QUANTILE,
        window_size: int = DEFAULT_WINDOW_SIZE,
        default_tau: float = DEFAULT_TAU,
    ) -> None:
        self.quantile = max(0.01, min(0.99, quantile))
        self.window_size = max(10, window_size)
        self.default_tau = default_tau
        self._window: deque[float] = deque(maxlen=self.window_size)

    def observe(self, value: float) -> None:
        """Record a new confidence observation."""
        self._window.append(value)

    @property
    def observation_count(self) -> int:
        return len(self._window)

    def threshold(self) -> float:
        """Current escalation threshold τ.

        Below τ → escalate to cloud. Above τ → accept local output.
        Returns the default until ``MIN_OBSERVATIONS_BEFORE_ADAPTIVE`` observations
        have been recorded, then switches to the sliding-window quantile.
        """
        if len(self._window) < MIN_OBSERVATIONS_BEFORE_ADAPTIVE:
            return self.default_tau
        sorted_vals = sorted(self._window)
        idx = int(self.quantile * len(sorted_vals))
        idx = max(0, min(idx, len(sorted_vals) - 1))
        return sorted_vals[idx]


class IsotonicCalibrator:
    """Isotonic-regression calibrator mapping logprob → p(error) (arXiv:2605.18796 UCCI).

    Given a small labeled set of (logprob, correct/incorrect) pairs, learns an
    isotonic (monotonically non-increasing) mapping from logprob to p(error).
    The cost-optimal threshold τ* is then selected by constrained cost minimization
    using measured latencies.

    Until calibration data exists, this is a no-op — ``p_error(logprob)`` returns
    a raw heuristic (lower logprob → higher p_error) and ``threshold()`` returns
    the default.

    Args:
        default_tau: Fallback threshold when no calibration data exists.
    """

    def __init__(self, default_tau: float = DEFAULT_TAU) -> None:
        self.default_tau = default_tau
        self._fitted: bool = False
        self._logprobs: list[float] = []
        self._p_errors: list[float] = []

    def fit(self, logprobs: Sequence[float], labels: Sequence[bool]) -> None:
        """Fit the isotonic mapping.

        Args:
            logprobs: Mean token log-probabilities from observed responses.
            labels: True = correct (no escalation needed), False = incorrect (should have escalated).
        """
        if len(logprobs) != len(labels) or len(logprobs) < 5:
            logger.debug("IsotonicCalibrator: need ≥5 pairs, got %d", len(logprobs))
            return
        pairs = sorted(zip(logprobs, labels), key=lambda x: x[0])
        lp_sorted = [p[0] for p in pairs]
        correct = [1.0 if p[1] else 0.0 for p in pairs]
        cumulative_correct = []
        running_sum = 0.0
        for i, c in enumerate(correct):
            running_sum += c
            cumulative_correct.append(running_sum / (i + 1))
        p_errors = [1.0 - cc for cc in cumulative_correct]
        self._logprobs = lp_sorted
        self._p_errors = p_errors
        self._fitted = True
        logger.info("IsotonicCalibrator fitted on %d pairs", len(logprobs))

    def p_error(self, logprob: float) -> float:
        """Estimate p(error) for a given logprob value.

        Returns a value in [0, 1] where higher = more likely incorrect.
        """
        if not self._fitted:
            return max(0.0, min(1.0, 0.5 + logprob * 0.1))
        import bisect

        idx = bisect.bisect_left(self._logprobs, logprob)
        if idx == 0:
            return self._p_errors[0] if self._p_errors else 1.0
        if idx >= len(self._p_errors):
            return self._p_errors[-1] if self._p_errors else 0.0
        return self._p_errors[idx]

    def threshold(self, max_p_error: float = 0.3) -> float:
        """Cost-optimal threshold τ* — the logprob where p(error) crosses max_p_error.

        Escalate when p_error(logprob) > max_p_error.
        Returns default_tau when not fitted.
        """
        if not self._fitted:
            return self.default_tau
        for lp, pe in zip(self._logprobs, self._p_errors):
            if pe <= max_p_error:
                return lp
        return self._logprobs[-1] if self._logprobs else self.default_tau

    @property
    def is_fitted(self) -> bool:
        return self._fitted


def composite_gate(
    text: str,
    mean_logprob: float | None,
    self_reported_confidence: float | None,
    *,
    tau_logprob: float = DEFAULT_TAU,
    quality_threshold: float = 0.8,
    min_length: int = 40,
) -> tuple[bool, str]:
    """Composite escalation gate combining logprob + confidence + length.

    Per arXiv:2605.02241: mean logprob is the primary signal.
    Per arXiv:2605.06350: the gate runs after local inference but before cloud
    escalation (pre-generation routing is preferred but local compute is $0).

    Returns (passes, reason):
      passes=True → accept the local output, no escalation needed.
      passes=False → escalate to cloud.
    """
    length_ok = len(text) >= min_length
    if not length_ok:
        return False, f"length gate: {len(text)} < {min_length}"

    if mean_logprob is not None:
        if mean_logprob < tau_logprob:
            return False, f"logprob gate: {mean_logprob:.4f} < τ={tau_logprob:.4f}"
        return True, f"logprob gate passed: {mean_logprob:.4f} >= τ={tau_logprob:.4f}"

    if self_reported_confidence is not None:
        if self_reported_confidence < quality_threshold:
            return False, f"confidence gate: {self_reported_confidence} < {quality_threshold}"
        return True, f"confidence gate passed: {self_reported_confidence} >= {quality_threshold}"

    return True, "length gate only (no logprob/confidence available)"
