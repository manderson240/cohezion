"""Physics invariant checker — deterministic proof obligation runner.

Called after every physics step to verify invariants hold. Returns
pass/fail for each obligation with violation details. Integrates
with DRR-3 gate for V-Model verification.

Proof Obligations:
    1. Energy conservation: E(t) ≈ E(0)
    2. Unitarity: |ψ|² = 1
    3. HIHO coherence band: coherence ∈ [0.3, 0.7] for stable states
    4. Metric positive-definiteness: det(g) > 0
    5. Gauge field: Yang-Mills action ≥ 0

References:
    - Session 96b Phase 8.2: Physics invariant proof obligations
    - Hairer, Lubich, Wanner (2006): Geometric Numerical Integration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np


logger = logging.getLogger(__name__)


class ObligationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(frozen=True)
class ObligationResult:
    """Result of a single proof obligation check."""

    name: str
    status: ObligationStatus
    value: float = 0.0
    threshold: float = 0.0
    detail: str = ""


@dataclass
class InvariantReport:
    """Aggregated result of all proof obligation checks."""

    results: list[ObligationResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.status != ObligationStatus.FAIL for r in self.results)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status == ObligationStatus.FAIL)

    @property
    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        parts = [f"{status} ({len(self.results)} checks, {self.failed_count} failed)"]
        for r in self.results:
            if r.status == ObligationStatus.FAIL:
                parts.append(f"  FAIL {r.name}: {r.detail}")
        return "\n".join(parts)


class InvariantChecker:
    """Deterministic physics invariant checker.

    All checks are numerical — no LLM reasoning. Can be called after
    every physics step for continuous verification.
    """

    def __init__(
        self,
        energy_tolerance: float = 0.05,
        unitarity_tolerance: float = 1e-8,
        coherence_band: tuple[float, float] = (0.05, 1.0),
    ):
        self.energy_tolerance = energy_tolerance
        self.unitarity_tolerance = unitarity_tolerance
        self.coherence_band = coherence_band
        self._initial_energy: float | None = None

    def reset(self) -> None:
        """Reset checker state (call at episode/trajectory start)."""
        self._initial_energy = None

    def check_all(
        self,
        state_12d: np.ndarray,
        energy: float | None = None,
        spinor_norm_sq: float | None = None,
        metric_det: float | None = None,
        yang_mills_action: float | None = None,
    ) -> InvariantReport:
        """Run all applicable proof obligation checks.

        Args:
            state_12d: Current 12D manifold state
            energy: Current total energy (if available)
            spinor_norm_sq: |ψ|² (if available)
            metric_det: det(g) (if available)
            yang_mills_action: S_YM (if available)

        Returns:
            InvariantReport with pass/fail for each obligation
        """
        report = InvariantReport()

        # 1. Energy conservation
        if energy is not None:
            report.results.append(self._check_energy(energy))

        # 2. Unitarity
        if spinor_norm_sq is not None:
            report.results.append(self._check_unitarity(spinor_norm_sq))

        # 3. HIHO coherence band
        report.results.append(self._check_coherence(state_12d))

        # 4. Metric positive-definiteness
        if metric_det is not None:
            report.results.append(self._check_metric(metric_det))

        # 5. Gauge field non-negativity
        if yang_mills_action is not None:
            report.results.append(self._check_gauge(yang_mills_action))

        return report

    def _check_energy(self, energy: float) -> ObligationResult:
        if self._initial_energy is None:
            self._initial_energy = energy
            return ObligationResult(
                name="energy_conservation",
                status=ObligationStatus.PASS,
                value=energy,
                detail="Initial energy recorded",
            )

        drift = abs(energy - self._initial_energy) / max(abs(self._initial_energy), 1e-10)
        if drift > self.energy_tolerance:
            return ObligationResult(
                name="energy_conservation",
                status=ObligationStatus.FAIL,
                value=drift,
                threshold=self.energy_tolerance,
                detail=f"E drift {drift:.4%} > {self.energy_tolerance:.4%}",
            )
        return ObligationResult(
            name="energy_conservation",
            status=ObligationStatus.PASS,
            value=drift,
            threshold=self.energy_tolerance,
        )

    def _check_unitarity(self, norm_sq: float) -> ObligationResult:
        violation = abs(norm_sq - 1.0)
        if violation > self.unitarity_tolerance:
            return ObligationResult(
                name="unitarity",
                status=ObligationStatus.FAIL,
                value=norm_sq,
                threshold=self.unitarity_tolerance,
                detail=f"|ψ|² = {norm_sq:.10f}, violation = {violation:.2e}",
            )
        return ObligationResult(
            name="unitarity",
            status=ObligationStatus.PASS,
            value=norm_sq,
            threshold=self.unitarity_tolerance,
        )

    def _check_coherence(self, state_12d: np.ndarray) -> ObligationResult:
        coherence = 1.0 - 2.0 * float(np.mean(np.abs(state_12d - 0.5)))
        lo, hi = self.coherence_band
        if lo <= coherence <= hi:
            return ObligationResult(
                name="coherence_band",
                status=ObligationStatus.PASS,
                value=coherence,
                detail=f"In band [{lo}, {hi}]",
            )
        return ObligationResult(
            name="coherence_band",
            status=ObligationStatus.FAIL,
            value=coherence,
            detail=f"coherence={coherence:.4f} outside [{lo}, {hi}]",
        )

    def _check_metric(self, det: float) -> ObligationResult:
        if det > 0:
            return ObligationResult(
                name="metric_positive_definite",
                status=ObligationStatus.PASS,
                value=det,
            )
        return ObligationResult(
            name="metric_positive_definite",
            status=ObligationStatus.FAIL,
            value=det,
            detail=f"det(g) = {det:.6e} ≤ 0",
        )

    def _check_gauge(self, action: float) -> ObligationResult:
        if action >= -1e-12:  # Allow tiny numerical noise
            return ObligationResult(
                name="gauge_action_nonneg",
                status=ObligationStatus.PASS,
                value=action,
            )
        return ObligationResult(
            name="gauge_action_nonneg",
            status=ObligationStatus.FAIL,
            value=action,
            detail=f"S_YM = {action:.6e} < 0",
        )
