"""Damped routing oscillator — universal pattern from control theory.

Motivated by: Hackaday, "Patterns Everywhere" (2026-06-13).
  https://hackaday.com/2026/06/13/patterns-everywhere/

The core observation: PID/damping patterns recur across mechanical systems
(horse-wagon braking), electronic filters, and quantum oscillators.  The
"judicious balance of amplification and damping" is the universal design
criterion — and it is exactly the HIHO stability principle.

Damped harmonic oscillator (canonical form):
    ẍ + 2ζω₀ẋ + ω₀²x = F(t)/m

where ζ is the damping ratio:
    ζ < 1  →  underdamped   (oscillation, overshoot, tier thrashing)
    ζ = 1  →  critically damped (HIHO optimal: fastest settling, no overshoot)
    ζ > 1  →  overdamped    (sluggish convergence, missed quality opportunities)

Cohezion routing mapping:
    x       = tier selection variable  (0=NPU → 1=cloud)
    ẋ       = routing velocity          (rate of tier change)
    ζ       = HIHO damping ratio        (routing balance parameter)
    ω₀      = quality threshold frequency (how fast the system responds to quality signals)
    F(t)/m  = quality forcing signal    (DegradationDetector output, normalized)

Critical damping (ζ=1) minimises the settle time 4/(ζω₀) while eliminating
overshoot — the routing system converges to the right tier without oscillating
between NPU and cloud.

Dynamical analogies (Olson 1943, 1958):
    Mechanical  →  Electrical  →  Acoustic  →  Routing
    mass        →  inductance  →  acoustic mass  →  tier inertia
    spring      →  capacitance →  acoustic stiffness → quality restoring force
    damper      →  resistance  →  acoustic resistance → routing smoothing
    force       →  voltage     →  pressure  →  quality signal

References:
    - Olson, H. F. (1958). Dynamical Analogies (2nd ed.). Van Nostrand.
    - Williams, E. (2026). "Patterns Everywhere." Hackaday.
    - Landau, L. & Lifshitz, E. (1976). Mechanics, §21–26 (damped oscillations).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np


logger = logging.getLogger(__name__)

_CRITICAL_DAMPING: float = 1.0
_HIHO_THRESHOLD: float = 0.5
_DEFAULT_TOLERANCE: float = 0.05
_2PCT_SETTLE_FACTOR: float = 4.0  # settle time ≈ 4/(ζω₀) for 2% criterion


@dataclass
class DampedRoutingOscillator:
    """Damped harmonic oscillator model for Cohezion tiered routing.

    Parameters
    ----------
    damping_ratio : float
        ζ — dimensionless damping coefficient.
        ζ < 1 = underdamped (oscillatory, tier thrashing risk).
        ζ = 1 = critically damped (HIHO optimal).
        ζ > 1 = overdamped (slow convergence).
    natural_frequency : float
        ω₀ — angular frequency in rad/s (quality response speed).
        Higher ω₀ = faster tier adaptation.
    x0 : float
        Initial tier position in [0, 1].  0 = NPU, 1 = cloud.
    v0 : float
        Initial routing velocity (rate of tier change).
    """

    damping_ratio: float = 1.0
    natural_frequency: float = 1.0
    x0: float = 0.5
    v0: float = 0.0

    def __post_init__(self) -> None:
        if self.damping_ratio < 0:
            raise ValueError("damping_ratio must be non-negative")
        if self.natural_frequency <= 0:
            raise ValueError("natural_frequency must be positive")

    # ── Derived quantities ───────────────────────────────────────────────

    @property
    def damped_frequency(self) -> float:
        """ω_d = ω₀ √(1 − ζ²)  — actual oscillation frequency (underdamped only).

        Returns 0.0 for critically/overdamped systems (no oscillation).
        """
        if self.damping_ratio >= 1.0:
            return 0.0
        return self.natural_frequency * np.sqrt(1.0 - self.damping_ratio**2)

    @property
    def decay_rate(self) -> float:
        """α = ζω₀ — exponential envelope decay rate."""
        return self.damping_ratio * self.natural_frequency

    @property
    def settle_time_2pct(self) -> float:
        """Approximate 2% settling time: t_s ≈ 4 / (ζω₀).

        Minimised at critical damping; grows for both under- and over-damped
        systems (though overdamped growth is monotone, underdamped has ringing).
        """
        alpha = self.decay_rate
        if alpha < 1e-12:
            return float("inf")
        return _2PCT_SETTLE_FACTOR / alpha

    # ── HIHO metrics ─────────────────────────────────────────────────────

    def hiho_damping_score(self) -> float:
        """HIHO kernel applied to the damping ratio.

        Maps ζ to a 0–1 score that peaks at ζ = 1 (critical damping = HIHO optimum).

        score = 4 × min(ζ, 1) × (1 − min(ζ, 1))   ... but this peaks at ζ=0.5.

        Instead we use a peaked kernel centred on ζ=1:
            u = ζ / (ζ + 1)  ∈ [0, 1) for ζ ≥ 0
            score = 4 × u × (1 − u)  → peaks at u = 0.5 → ζ = 1.

        score = 1.0  when ζ = 1  (critical damping, HIHO equilibrium)
        score → 0   when ζ → 0 or ζ → ∞  (no damping or infinite damping)
        """
        u = self.damping_ratio / (self.damping_ratio + 1.0)
        return 4.0 * u * (1.0 - u)

    def is_critically_damped(self, tolerance: float = _DEFAULT_TOLERANCE) -> bool:
        """True when |ζ − 1| ≤ tolerance — routing is in the HIHO equilibrium."""
        return abs(self.damping_ratio - _CRITICAL_DAMPING) <= tolerance

    def is_underdamped(self) -> bool:
        return self.damping_ratio < _CRITICAL_DAMPING

    def is_overdamped(self) -> bool:
        return self.damping_ratio > _CRITICAL_DAMPING

    # ── Analytical solution ──────────────────────────────────────────────

    def analytical_response(self, t: float, forcing: float = 0.0) -> tuple[float, float]:
        """Exact impulse-free solution x(t), ẋ(t) from (x0, v0).

        Handles all three regimes:
            underdamped  (ζ < 1): oscillatory envelope
            critically damped (ζ = 1): algebraic decay
            overdamped   (ζ > 1): two real exponentials

        Parameters
        ----------
        t : float
            Time in seconds.
        forcing : float
            Constant external forcing F(t)/m (quality signal, default 0).
            Included as steady-state offset x_ss = forcing / ω₀².

        Returns
        -------
        (x, v) position and velocity at time t
        """
        omega0 = self.natural_frequency
        zeta = self.damping_ratio
        alpha = zeta * omega0
        x0, v0 = self.x0, self.v0

        # Steady-state offset from constant forcing
        x_ss = forcing / (omega0**2) if omega0 > 0 else 0.0
        # Shift initial conditions relative to steady state
        y0 = x0 - x_ss
        dy0 = v0

        if zeta < 1.0:  # underdamped
            wd = self.damped_frequency
            A = y0
            B = (dy0 + alpha * y0) / wd
            e = np.exp(-alpha * t)
            cos_t = np.cos(wd * t)
            sin_t = np.sin(wd * t)
            x = x_ss + e * (A * cos_t + B * sin_t)
            v = e * ((B * wd - alpha * A) * cos_t - (A * wd + alpha * B) * sin_t)
        elif abs(zeta - 1.0) < 1e-10:  # critically damped
            A = y0
            B = dy0 + alpha * y0
            e = np.exp(-alpha * t)
            x = x_ss + e * (A + B * t)
            v = e * (B - alpha * (A + B * t))
        else:  # overdamped
            r1 = -alpha + omega0 * np.sqrt(zeta**2 - 1.0)
            r2 = -alpha - omega0 * np.sqrt(zeta**2 - 1.0)
            denom = r1 - r2
            if abs(denom) < 1e-14:
                # Fallback to critical-damping formula
                A = y0
                B = dy0 + alpha * y0
                e = np.exp(-alpha * t)
                x = x_ss + e * (A + B * t)
                v = e * (B - alpha * (A + B * t))
            else:
                C1 = (dy0 - r2 * y0) / denom
                C2 = (r1 * y0 - dy0) / denom
                x = x_ss + C1 * np.exp(r1 * t) + C2 * np.exp(r2 * t)
                v = C1 * r1 * np.exp(r1 * t) + C2 * r2 * np.exp(r2 * t)

        return float(x), float(v)

    # ── Numerical simulation ─────────────────────────────────────────────

    def step(
        self,
        x: float,
        v: float,
        dt: float = 0.01,
        forcing: float = 0.0,
    ) -> tuple[float, float]:
        """Velocity-Verlet step for the damped oscillator.

        ẍ = −2ζω₀ẋ − ω₀²x + F/m

        Returns (x_new, v_new).
        """
        omega0 = self.natural_frequency
        zeta = self.damping_ratio
        acc = -2.0 * zeta * omega0 * v - omega0**2 * x + forcing
        v_new = v + dt * acc
        x_new = x + dt * v_new
        return float(x_new), float(v_new)

    def simulate(
        self,
        n_steps: int = 200,
        dt: float = 0.01,
        forcing_fn: Callable[[float], float] | None = None,
    ) -> np.ndarray:
        """Simulate trajectory from (x0, v0).

        Parameters
        ----------
        n_steps : int
            Number of time steps.
        dt : float
            Step size in seconds.
        forcing_fn : callable(t) → float, optional
            Time-varying quality forcing signal.  None = free oscillation.

        Returns
        -------
        ndarray, shape (n_steps + 1, 3)
            Columns: [t, x, v].
        """
        traj = np.empty((n_steps + 1, 3))
        x, v = self.x0, self.v0
        traj[0] = [0.0, x, v]
        for i in range(n_steps):
            t = (i + 1) * dt
            forcing = float(forcing_fn(t)) if forcing_fn is not None else 0.0
            x, v = self.step(x, v, dt=dt, forcing=forcing)
            traj[i + 1] = [t, x, v]
        return traj

    # ── Routing tier inference ───────────────────────────────────────────

    def routing_tier(self, x: float | None = None) -> str:
        """Map oscillator position x ∈ [0, 1] to a Cohezion routing tier.

        x ∈ [0.00, 0.25) → "npu"   (fast, cheap)
        x ∈ [0.25, 0.50) → "igpu"  (HIHO hybrid — includes x0=0.5 default)
        x ∈ [0.50, 0.75) → "cpu"   (reasoning, escalation)
        x ∈ [0.75, 1.00] → "cloud" (last resort, quality-critical)

        Uses current x0 if x is not provided.
        """
        pos = self.x0 if x is None else x
        pos = max(0.0, min(1.0, pos))
        if pos < 0.25:
            return "npu"
        if pos <= 0.50:
            return "igpu"
        if pos < 0.75:
            return "cpu"
        return "cloud"

    # ── PID analog decomposition ─────────────────────────────────────────

    def pid_coefficients(self) -> dict[str, float]:
        """Return PID-equivalent coefficients from the oscillator parameters.

        The damped oscillator transfer function 1/(s² + 2ζω₀s + ω₀²) is
        equivalent to a PID controller in certain feedback configurations:

            Kp  = ω₀²               (proportional — quality restoring force)
            Ki  = 0                  (integral — not in pure 2nd-order HO)
            Kd  = 2ζω₀              (derivative — damping term)

        The ratio Kd/(2Kp) = ζ/ω₀ is the "damping time constant" — how
        long the system takes to integrate routing velocity into tier position.
        """
        kp = self.natural_frequency**2
        kd = 2.0 * self.damping_ratio * self.natural_frequency
        return {
            "Kp": kp,
            "Ki": 0.0,
            "Kd": kd,
            "damping_time_constant": kd / (2.0 * kp) if kp > 0 else float("inf"),
        }

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serializable summary for SurrealDB traces."""
        return {
            "damping_ratio": self.damping_ratio,
            "natural_frequency": self.natural_frequency,
            "x0": self.x0,
            "v0": self.v0,
            "damped_frequency": self.damped_frequency,
            "decay_rate": self.decay_rate,
            "settle_time_2pct": self.settle_time_2pct,
            "hiho_damping_score": self.hiho_damping_score(),
            "is_critically_damped": self.is_critically_damped(),
            "is_underdamped": self.is_underdamped(),
            "is_overdamped": self.is_overdamped(),
            "routing_tier": self.routing_tier(),
        }


# ── Cohezion routing convenience constructors ───────────────────────────────


def make_hiho_oscillator(
    natural_frequency: float = 2.0,
    x0: float = 0.5,
) -> DampedRoutingOscillator:
    """Critically damped oscillator at the HIHO equilibrium.

    ζ = 1.0 — fastest convergence without overshoot.
    x0 = 0.5 — balanced midpoint (iGPU tier boundary).

    Use for: routing decisions at quality-budget parity.
    """
    return DampedRoutingOscillator(
        damping_ratio=_CRITICAL_DAMPING,
        natural_frequency=natural_frequency,
        x0=x0,
        v0=0.0,
    )


def make_triune_oscillator(
    quality_signal: float = 0.0,
    damping_ratio: float = 1.0,
) -> DampedRoutingOscillator:
    """Routing oscillator for Triune tier selection.

    Maps quality_signal ∈ [-1, 1] to initial tier position:
        quality_signal = -1.0  → x0 = 0.0 (full NPU)
        quality_signal =  0.0  → x0 = 0.5 (HIHO iGPU)
        quality_signal = +1.0  → x0 = 1.0 (full cloud)

    The oscillator then damps toward the equilibrium tier.
    """
    x0 = 0.5 + 0.5 * np.clip(quality_signal, -1.0, 1.0)
    return DampedRoutingOscillator(
        damping_ratio=damping_ratio,
        natural_frequency=2.0,  # ω₀ = 2 rad/s → 2% settle in ~2s
        x0=float(x0),
        v0=0.0,
    )


def make_underdamped_oscillator(
    zeta: float = 0.3,
    natural_frequency: float = 2.0,
) -> DampedRoutingOscillator:
    """Underdamped oscillator — illustrates tier thrashing regime.

    Used in tests and educational contexts to show why ζ < 1 causes
    oscillation between tiers (the horse-wagon over-braking pattern).
    """
    if zeta >= 1.0:
        raise ValueError(f"zeta must be < 1 for underdamped regime, got {zeta}")
    return DampedRoutingOscillator(
        damping_ratio=zeta,
        natural_frequency=natural_frequency,
        x0=0.5,
        v0=0.5,  # initial kick to make oscillation visible
    )


def settle_time_comparison(
    omega0: float = 2.0,
    zeta_values: list[float] | None = None,
) -> list[dict]:
    """Compare settle times across damping ratios.

    Useful for calibrating routing thresholds: shows how much faster
    critical damping converges vs under/over-damped configurations.

    Returns a list of {zeta, settle_time, hiho_score, regime} dicts.
    """
    if zeta_values is None:
        zeta_values = [0.1, 0.3, 0.5, 0.707, 1.0, 1.5, 2.0, 3.0]
    records = []
    for zeta in zeta_values:
        osc = DampedRoutingOscillator(damping_ratio=zeta, natural_frequency=omega0)
        regime = (
            "critical"
            if osc.is_critically_damped()
            else ("under" if osc.is_underdamped() else "over")
        )
        records.append(
            {
                "zeta": zeta,
                "settle_time": osc.settle_time_2pct,
                "hiho_score": osc.hiho_damping_score(),
                "regime": regime,
            }
        )
    return records
