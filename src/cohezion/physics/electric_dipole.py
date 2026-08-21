"""Electric dipole moment — the canonical physical instance of the HIHO kernel.

Two opposite charges held apart by ``d`` form a dipole ``p = q·d`` (pointing from negative to
positive, magnitude ``qd``). An external field exerts ``τ = p × E``, which rotates it toward
alignment. This underlies water's polarity, capacitor dielectrics, and molecular orientation in
chemistry and biology — charge separation at the smallest scale shaping macroscopic matter.

WHY THIS MODULE EXISTS (Wire-at-Creation status, stated honestly — adversarial review
2026-08-21 found the original "three real consumers" claim two-thirds inflated):

1. ONE real code consumer: ``dielectric.py``'s :meth:`DielectricField.from_dipoles` imports
   :func:`permittivity_from_dipoles`, closing the physical chain ``p = qd`` → ``P = N⟨p⟩`` →
   ``ε_r = 1 + χ`` → bulk response (permittivity was previously a free input parameter).
   That bridge is itself exercised only by tests so far — no production caller yet; wiring
   it into a DegradationDetector/CompoundExecutor path is the open Wire-at-Creation TODO.

2. Motivations that are NOT code consumers (do not read them as wiring): ``toroidal_moment.py``
   mentions dipoles in prose only (never imports this), and the U1 anchoring below is a
   doc/test relationship, not consumption.

3. It anchors harness invariant **U1** in a worked example. U1 asserts that all seven physics
   substrates share the kernel ``4x(1-x)``, peaking at ``x = 0.5``. Under the natural alignment
   coordinate ``x = (1 + cos θ)/2`` that kernel is EXACTLY ``sin²θ``::

       4x(1-x) = (1 + cos θ)(1 - cos θ) = 1 - cos²θ = sin²θ

   so ``τ = pE·sin θ = pE·√(HIHO kernel)`` and ``U = −p·E = −pE·(2x − 1)``. The dipole is
   therefore not *another* substrate obeying the kernel; it is the kernel's textbook realization.

   This also sharpens what HIHO's 0.5 means. At ``x = 0.5`` (θ = 90°) the alignment energy is
   ZERO — no commitment either way — while the restoring torque is MAXIMUM. "Half-in, half-out"
   is exactly *zero commitment, maximum responsiveness*, reached by identity rather than analogy.

SCOPE NOTE, so this is not over-read: the identity is algebraic and holds for any variable
reparametrised as ``x = (1+cos θ)/2``. The seven substrates' variables are not all alignment
angles — BEC condensate fraction and IonicCluster ionisation fraction are POPULATION fractions.
The algebra is exact; the physical interpretation varies per substrate. That the dipole law
*unifies* U1 is a hypothesis to test substrate-by-substrate, not a result claimed here.

Terminology warning: ``flume/bioelectric_swarm.py`` uses ``polarize``/``depolarize`` for MEMBRANE
POTENTIAL in mV. That is unrelated to dipole polarization. Grepping ``polariz`` finds it and not
this module.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


# Matches the convention in ionic_cluster.py / lenr.py: each substrate carries the threshold and
# the kernel inline (harness S9 treats the shared formula as a cross-substrate invariant to be
# verified, not a helper to be factored out).
_HIHO_THRESHOLD: float = 0.5
_DEFAULT_TOLERANCE: float = 0.05

# Vacuum permittivity (F/m) and Boltzmann constant (J/K), CODATA.
_EPSILON_0: float = 8.8541878128e-12
_K_B: float = 1.380649e-23


@dataclass(frozen=True)
class ElectricDipole:
    """A pair of opposite charges ``±q`` separated by displacement ``d``.

    ``separation`` runs from the NEGATIVE charge to the POSITIVE one, which fixes the sign of
    ``p`` and therefore the sign of the energy. Getting that backwards flips ``U`` and makes the
    aligned state look maximally unfavourable, so the direction is part of the contract.
    """

    charge: float
    separation: np.ndarray

    def __post_init__(self) -> None:
        sep = np.asarray(self.separation, dtype=float)
        if sep.shape != (3,):
            raise ValueError(f"separation must be a 3-vector, got shape {sep.shape}")
        object.__setattr__(self, "separation", sep)

    @property
    def moment(self) -> np.ndarray:
        """``p = q·d`` — the dipole moment vector (C·m)."""
        return self.charge * self.separation

    @property
    def magnitude(self) -> float:
        """``|p| = q·d``."""
        return float(np.linalg.norm(self.moment))

    def torque(self, field: np.ndarray) -> np.ndarray:
        """``τ = p × E`` — rotates the dipole toward alignment with the field.

        Returned as a VECTOR, not a magnitude: the axis carries the sense of rotation, and a
        caller summing torques over many dipoles needs it. Magnitude alone silently discards
        whether two dipoles rotate the same way.
        """
        return np.cross(self.moment, np.asarray(field, dtype=float))

    def energy(self, field: np.ndarray) -> float:
        """``U = −p·E`` — minimal when aligned, maximal when anti-aligned.

        This is the quantity that distinguishes θ = 0 from θ = 180°. Both have ZERO torque, so
        torque alone cannot tell "aligned" from "exactly backwards" — a distinction that matters
        because one is a stable equilibrium and the other is unstable.
        """
        return -float(np.dot(self.moment, np.asarray(field, dtype=float)))

    def alignment_fraction(self, field: np.ndarray) -> float:
        """``x = (1 + cos θ)/2`` — 1.0 aligned, 0.0 anti-aligned, 0.5 perpendicular.

        Returns 0.5 for a null dipole or null field: with no defined angle, the honest answer is
        the no-preference midpoint, which is also the value at which the kernel below peaks.
        """
        p = self.moment
        e = np.asarray(field, dtype=float)
        np_, ne = np.linalg.norm(p), np.linalg.norm(e)
        if np_ == 0.0 or ne == 0.0:
            return _HIHO_THRESHOLD
        cos_theta = float(np.clip(np.dot(p, e) / (np_ * ne), -1.0, 1.0))
        return (1.0 + cos_theta) / 2.0

    def hiho_kernel(self, field: np.ndarray) -> float:
        """``4x(1-x)``, which for this parametrisation equals ``sin²θ`` exactly.

        Equivalently ``(|τ| / (|p||E|))²`` — the squared normalised torque. Peaks at 1.0 when
        perpendicular, vanishes at either alignment extreme.
        """
        x = self.alignment_fraction(field)
        return 4.0 * x * (1.0 - x)

    def hiho_equilibrium(self, field: np.ndarray, tolerance: float = _DEFAULT_TOLERANCE) -> bool:
        """True when alignment sits within ``tolerance`` of the HIHO midpoint.

        The ``+1e-9`` guard mirrors ionic_cluster/bec_bridge (harness S7): without it a value
        exactly at the tolerance boundary fails on one side and passes on the other, because
        ``0.55 - 0.5 == 0.050000000000000044`` in float64.
        """
        return abs(self.alignment_fraction(field) - _HIHO_THRESHOLD) <= tolerance + 1e-9


def permittivity_from_dipoles(
    number_density: float,
    dipole_magnitude: float,
    temperature_k: float = 293.15,
) -> float:
    """Relative permittivity ``ε_r = 1 + N p² / (3 ε₀ k_B T)`` (Debye orientational term).

    Supplies ``dielectric.DielectricField`` with a permittivity DERIVED from charge separation
    rather than supplied as a free parameter — the ``P = N⟨p⟩`` link that was missing.

    Valid in the weak-field / high-temperature regime ``pE ≪ k_BT``, where the Langevin function
    linearises. It deliberately models ONLY the orientational (dipolar) contribution and omits
    electronic and ionic polarizability, so it under-predicts ε_r for real materials. That is the
    honest direction for a dipole module to err in; a fudge factor tuned to match water would
    make it match one substance and mislead everywhere else.

    Returns 1.0 (vacuum) for non-positive density or temperature rather than raising: a zero
    density is a legitimate state, not an error.
    """
    if number_density <= 0.0 or temperature_k <= 0.0:
        return 1.0
    chi = (number_density * dipole_magnitude**2) / (3.0 * _EPSILON_0 * _K_B * temperature_k)
    return 1.0 + chi
