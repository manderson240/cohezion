"""ConservationFilter — Anomaly Gate Phases 1-2: float-error vs genuine structural divergence.

The hard requirement of the Anomaly Gate is distinguishing a *hallucinated floating-point error*
(a mesh/boundary artifact) from a *genuine structural divergence* (a candidate breakthrough), so the
reflection loop never flattens emergent behavior back into standard constraints — and never quarantines
a numerical bug as a discovery.

The discriminator, expressed from quantities already in cohezion's MHD stack, is:

    split the invariants into NUMERICAL-INTEGRITY vs PHYSICAL, and trigger the gate only when a
    PHYSICAL quantity violates tau WHILE every NUMERICAL-INTEGRITY invariant still holds.

  * Numerical-integrity invariants — a valid integrator *must* hold these. If any fails, the result is
    an artifact, not physics:
      - solenoidal constraint   ∇·B = 0          (MHDField.compute_divergence)
      - unitarity               |ψ|² = 1          (InvariantChecker, tol 1e-8)
      - metric positive-definite det(g) > 0
      - gauge action ≥ 0
      - coherence in band, finite values
  * Physical quantity — energy. A spike here is the candidate anomaly:
      - energy conservation     ΔE/E₀ ≤ tau       (InvariantChecker, default tau = 0.05)

Verdicts:
  * STANDARD — everything within tolerance.
  * REJECT   — a numerical-integrity invariant failed (non-finite, ∇·B drift, |ψ|²≠1, …): an artifact;
               route to the syntax/divergence retry path (error_loop divergence/permanent class).
  * ANOMALY  — energy violates tau WHILE integrity holds: a structural candidate; escalate to the
               adversarial Skeptic (Anomaly Gate Phase 3).

CRITICAL: this reads the **raw, pre-squash** conserved quantities. The HIHO kernel squashes outputs to
[0,1], so an energy blow-up maps to a finite near-zero score that passes naive checks and reads as
ΔE≈0. tau MUST be calibrated against raw energy/∇·B/|ψ|², never the squashed coherence score.

Deterministic — no LLM (Anomaly Gate Phase 2 is explicitly a plain script). Composes with error_loop.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

from cohezion.physics.invariant_checker import InvariantChecker, ObligationStatus


__all__ = ["ConservationFilter", "ConservationResult", "Verdict"]

# Obligation names whose violation is a PHYSICAL signal (candidate anomaly), not an artifact.
_PHYSICAL_NAMES = ("energy_conservation",)


class Verdict(StrEnum):
    STANDARD = "standard"  # within tolerance — log as a normal run
    REJECT = "reject"  # numerical-integrity artifact — retry, not a discovery
    ANOMALY = (
        "anomaly"  # structural: physical violation with integrity intact — escalate to Skeptic
    )


@dataclass(frozen=True)
class ConservationResult:
    verdict: Verdict
    reason: str
    integrity_ok: bool
    physical_violation: bool
    div_b_error: float
    failed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "reason": self.reason,
            "integrity_ok": self.integrity_ok,
            "physical_violation": self.physical_violation,
            "div_b_error": self.div_b_error,
            "failed": list(self.failed),
        }


class ConservationFilter:
    """Deterministic conservation gate over an MHD step's raw outputs.

    Parameters
    ----------
    energy_tolerance:
        tau — allowed |ΔE/E₀| before energy is flagged (default 0.05, the InvariantChecker default).
    div_b_tolerance:
        Max |∇·B| before the solenoidal constraint is considered violated (a mesh/boundary artifact).
    unitarity_tolerance:
        |ψ|² deviation from 1 tolerated.

    Stateful: the first ``evaluate`` call establishes the energy baseline E₀ (call ``reset`` per run).
    """

    def __init__(
        self,
        energy_tolerance: float = 0.05,
        div_b_tolerance: float = 1e-6,
        unitarity_tolerance: float = 1e-8,
    ) -> None:
        self.div_b_tolerance = div_b_tolerance
        self._checker = InvariantChecker(
            energy_tolerance=energy_tolerance, unitarity_tolerance=unitarity_tolerance
        )

    def reset(self) -> None:
        """Reset the energy baseline (call at the start of each simulation run)."""
        self._checker.reset()

    def evaluate(
        self,
        state_12d: np.ndarray,
        *,
        raw_energy: float,
        spinor_norm_sq: float | None = None,
        div_b_error: float = 0.0,
        metric_det: float | None = None,
    ) -> ConservationResult:
        """Classify one MHD step's RAW (pre-squash) outputs as standard / reject / anomaly."""
        # 0. Non-finite anything = numerical artifact (the float-error case), reject outright.
        if not math.isfinite(raw_energy) or not math.isfinite(div_b_error):
            return ConservationResult(
                Verdict.REJECT,
                "non-finite raw energy or ∇·B (numerical blow-up)",
                integrity_ok=False,
                physical_violation=False,
                div_b_error=div_b_error,
                failed=["finiteness"],
            )

        # 1. Solenoidal constraint ∇·B = 0 — a real integrator holds this; drift = mesh/boundary artifact.
        div_b_ok = abs(div_b_error) <= self.div_b_tolerance

        # 2. Proof obligations on RAW quantities (energy/unitarity/coherence/metric).
        report = self._checker.check_all(
            np.asarray(state_12d, dtype=float),
            energy=raw_energy,
            spinor_norm_sq=spinor_norm_sq,
            metric_det=metric_det,
        )
        failed = [r.name for r in report.results if r.status == ObligationStatus.FAIL]
        physical_failed = [n for n in failed if n in _PHYSICAL_NAMES]
        integrity_failed = [n for n in failed if n not in _PHYSICAL_NAMES]
        if not div_b_ok:
            integrity_failed.append("solenoidal_div_b")

        integrity_ok = not integrity_failed
        physical_violation = bool(physical_failed)

        # 3. Decide. Integrity failure dominates: it makes any physical spike untrustworthy.
        if not integrity_ok:
            return ConservationResult(
                Verdict.REJECT,
                f"numerical-integrity invariant failed: {', '.join(integrity_failed)} "
                f"(artifact, not physics — route to retry)",
                integrity_ok=False,
                physical_violation=physical_violation,
                div_b_error=div_b_error,
                failed=integrity_failed + physical_failed,
            )
        if physical_violation:
            return ConservationResult(
                Verdict.ANOMALY,
                f"energy violates tau while integrity holds: {', '.join(physical_failed)} "
                f"(structural candidate — escalate to Skeptic)",
                integrity_ok=True,
                physical_violation=True,
                div_b_error=div_b_error,
                failed=physical_failed,
            )
        return ConservationResult(
            Verdict.STANDARD,
            "all invariants within tolerance",
            integrity_ok=True,
            physical_violation=False,
            div_b_error=div_b_error,
            failed=[],
        )
