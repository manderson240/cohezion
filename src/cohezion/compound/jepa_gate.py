"""JEPA pre-execution simulation gate (#139, GIC Decision-making, arXiv 2606.23991).

Uses the JEPAWorldModel to predict the expected outcome coherence BEFORE committing
a task to the 11-step CompoundExecutor pipeline.  The predicted 12D state's mean
value acts as a proxy for execution quality.

Verdict thresholds (calibrated against Cohezion 12D trajectory norms):
  PROCEED  — predicted coherence ≥ 0.6 (expected quality, proceed as normal)
  REROUTE  — predicted coherence in [0.1, 0.6) (marginal; try cheaper tier first)
  SKIP     — predicted coherence < 0.1 (execution predicted to be low-value)

Fail-open: when no world_model is available, verdict is always PROCEED.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Default 12D zero-vector used when current_state is None.
_DEFAULT_STATE = np.zeros(12, dtype=np.float32)
# Default action vector (neutral, no-op) for state transition simulation.
_DEFAULT_ACTION = np.zeros(12, dtype=np.float32)

_THRESHOLD_PROCEED: float = 0.6  # coherence ≥ this → PROCEED
_THRESHOLD_REROUTE: float = 0.1  # coherence ≥ this → REROUTE; below → SKIP
# Epsilon guards exact threshold boundaries against float64 pairwise-summation drift.
_EPS: float = 1e-9


class PreExecutionVerdict(Enum):
    """Outcome of the JEPA pre-execution coherence check."""

    PROCEED = "proceed"  # Predicted quality OK — run normally.
    REROUTE = "reroute"  # Marginal quality — reroute to cheaper or richer tier.
    SKIP = "skip"  # Predicted quality too low — skip execution entirely.


class JepaGate:
    """Pre-execution gate that queries a JEPA world model for outcome coherence.

    Args:
        world_model: A JEPAWorldModel-compatible object exposing
            ``predict_next_state(state, action) -> np.ndarray``.
            Pass None to get a permanently fail-open gate (always PROCEED).
        proceed_threshold: Minimum mean predicted state value to PROCEED.
        reroute_threshold: Minimum mean predicted state value to REROUTE
            (below this → SKIP).
    """

    def __init__(
        self,
        world_model: Any | None,
        proceed_threshold: float = _THRESHOLD_PROCEED,
        reroute_threshold: float = _THRESHOLD_REROUTE,
    ) -> None:
        self._world_model = world_model
        self._proceed_threshold = proceed_threshold
        self._reroute_threshold = reroute_threshold
        # Readable after check() — callers can feed this into DegradationDetector.
        # Initialized to 1.0 (optimistic, fail-open default).
        self.last_coherence: float = 1.0

    def check(
        self,
        task_description: str,
        current_state: "np.ndarray | None" = None,
    ) -> PreExecutionVerdict:
        """Predict execution coherence and return a routing verdict.

        Args:
            task_description: Human-readable task string (used for logging).
            current_state: Current 12D trajectory state from JourneyTracker.
                Defaults to the zero-vector when None.

        Returns:
            PreExecutionVerdict based on the predicted mean coherence.
        """
        if self._world_model is None:
            self.last_coherence = 1.0
            return PreExecutionVerdict.PROCEED

        state = current_state if current_state is not None else _DEFAULT_STATE
        try:
            predicted = self._world_model.predict_next_state(state, _DEFAULT_ACTION)
            coherence = float(np.mean(np.clip(predicted, 0.0, 1.0)))
        except Exception as exc:
            logger.debug("JEPA gate prediction failed (fail-open): %s", exc)
            self.last_coherence = 1.0
            return PreExecutionVerdict.PROCEED

        self.last_coherence = coherence

        if coherence + _EPS >= self._proceed_threshold:
            verdict = PreExecutionVerdict.PROCEED
        elif coherence + _EPS >= self._reroute_threshold:
            verdict = PreExecutionVerdict.REROUTE
        else:
            verdict = PreExecutionVerdict.SKIP

        logger.debug(
            "JEPA gate: task=%r coherence=%.3f verdict=%s",
            task_description[:60],
            coherence,
            verdict.value,
        )
        return verdict
