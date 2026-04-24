# ruff: noqa: E501, RUF001  # math/physics symbols intentional
"""Divergence detection for sandboxed simulations.

Monitors per-sandbox coherence, numerical stability, and statistical outliers.
Mirrors the AxiomaticState.coherence_score() pattern from engine.py for HIHO
stability tracking at the 0.5 equilibrium point.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

# HIHO target coherence (Half-In-Half-Out equilibrium)
HIHO_TARGET = 0.5
# Maximum acceptable drift from HIHO target
HIHO_MAX_DRIFT = 0.4


@dataclass
class DivergenceStatus:
    """Result of a divergence check.

    Parameters
    ----------
    diverged : bool
        Whether divergence has been detected.
    reason : str
        Human-readable explanation of divergence (empty if not diverged).
    coherence : float
        Current HIHO coherence score (1.0 = perfect stability at 0.5).
    last_values : list[float]
        Recent values from the monitored signal.
    """

    diverged: bool
    reason: str
    coherence: float
    last_values: list[float] = field(default_factory=list)


class DivergenceDetector:
    """Per-sandbox divergence detector.

    Detects three classes of divergence:
    1. **NaN/Inf**: Non-finite values in simulation output.
    2. **Statistical outlier**: Value exceeds N standard deviations from running mean.
    3. **HIHO coherence drift**: Coherence drifts >0.4 from the 0.5 target.

    Parameters
    ----------
    max_sigma : float
        Maximum standard deviations from running mean before flagging divergence.
    window_size : int
        Number of recent values to retain for statistics.
    """

    def __init__(self, max_sigma: float = 3.0, window_size: int = 100):
        self.max_sigma = max_sigma
        self.window_size = window_size
        self._values: deque[float] = deque(maxlen=window_size)
        self._coherence_values: deque[float] = deque(maxlen=window_size)
        self._sum: float = 0.0
        self._sum_sq: float = 0.0
        self._count: int = 0

    def check(self, value: float, coherence: float | None = None) -> DivergenceStatus:
        """Check a new value for divergence.

        Parameters
        ----------
        value : float
            The simulation output value to check.
        coherence : float, optional
            Current HIHO coherence score. If provided, checked for drift.

        Returns
        -------
        DivergenceStatus
            Whether divergence was detected and why.
        """
        # 1. NaN/Inf check
        if math.isnan(value) or math.isinf(value):
            return DivergenceStatus(
                diverged=True,
                reason=f"Non-finite value detected: {value}",
                coherence=coherence if coherence is not None else 0.0,
                last_values=list(self._values),
            )

        # 2. Statistical outlier check (only after enough samples)
        if self._count >= 2:
            mean = self._sum / self._count
            variance = (self._sum_sq / self._count) - (mean * mean)
            stddev = math.sqrt(max(variance, 0.0))

            if stddev > 0:
                z_score = abs(value - mean) / stddev
                if z_score > self.max_sigma:
                    return DivergenceStatus(
                        diverged=True,
                        reason=(
                            f"Statistical outlier: z={z_score:.2f} "
                            f"(>{self.max_sigma}σ), value={value:.6f}, "
                            f"mean={mean:.6f}, stddev={stddev:.6f}"
                        ),
                        coherence=coherence if coherence is not None else 0.0,
                        last_values=list(self._values),
                    )
            elif abs(value - mean) > 0:
                # Zero stddev but value differs from mean — definite outlier
                return DivergenceStatus(
                    diverged=True,
                    reason=(
                        f"Statistical outlier: value={value:.6f} deviates from constant mean={mean:.6f} (stddev=0)"
                    ),
                    coherence=coherence if coherence is not None else 0.0,
                    last_values=list(self._values),
                )

        # Update running statistics
        self._values.append(value)
        self._sum += value
        self._sum_sq += value * value
        self._count += 1

        # Recompute running stats periodically when window is full
        if self._count > self.window_size and self._count % self.window_size == 0:
            self._recompute_stats()

        # 3. HIHO coherence drift check
        current_coherence = coherence if coherence is not None else self._estimate_coherence()
        if coherence is not None:
            self._coherence_values.append(coherence)

        if abs(current_coherence - HIHO_TARGET) > HIHO_MAX_DRIFT:
            return DivergenceStatus(
                diverged=True,
                reason=(
                    f"HIHO coherence drift: coherence={current_coherence:.3f}, "
                    f"target={HIHO_TARGET}, drift={abs(current_coherence - HIHO_TARGET):.3f} "
                    f"(>{HIHO_MAX_DRIFT})"
                ),
                coherence=current_coherence,
                last_values=list(self._values),
            )

        return DivergenceStatus(
            diverged=False,
            reason="",
            coherence=current_coherence,
            last_values=list(self._values)[-5:],
        )

    def _estimate_coherence(self) -> float:
        """Estimate coherence from value stability (mirrors AxiomaticState.coherence_score).

        Coherence is 1.0 when variance is zero, 0.0 when variance >= 0.25.
        """
        if self._count < 2:
            return HIHO_TARGET

        mean = self._sum / self._count
        variance = (self._sum_sq / self._count) - (mean * mean)
        variance = max(variance, 0.0)
        return max(1.0 - min(variance * 4, 1.0), 0.0)

    def _recompute_stats(self) -> None:
        """Recompute running statistics from current window."""
        self._sum = sum(self._values)
        self._sum_sq = sum(v * v for v in self._values)
        self._count = len(self._values)

    def reset(self) -> None:
        """Reset all state."""
        self._values.clear()
        self._coherence_values.clear()
        self._sum = 0.0
        self._sum_sq = 0.0
        self._count = 0

    def get_stats(self) -> dict:
        """Return current detector statistics."""
        mean = self._sum / self._count if self._count > 0 else 0.0
        variance = (self._sum_sq / self._count) - (mean * mean) if self._count > 0 else 0.0
        return {
            "count": self._count,
            "mean": mean,
            "variance": max(variance, 0.0),
            "window_size": self.window_size,
            "max_sigma": self.max_sigma,
            "coherence": self._estimate_coherence(),
        }
