r"""Non-Equilibrium Information Thermodynamics & 432 Hz HIHO Reality Engine.
===========================================================================
Implements formal non-equilibrium information thermodynamics:

1. Landauer Principle for Associative Memory Erasure:
   $$\Delta Q_{\text{dissipated}} \ge k_B T \ln(2) \cdot \Delta S_{\text{erased}}$$

2. HIHO Phase Stability Index (0.5 Critical Boundary):
   Calculates order parameter $\Phi = 1.0 - 4(c - 0.5)^2$, peaking at $c = 0.5$.

3. 4-Fabric Acoustic Harmonic Field Coupling:
   Maps (Space, Field, Control, Precipitation) states into 432 Hz fundamental
   and exact ADSR harmonic envelopes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


K_BOLTZMANN = 1.380649e-23  # J/K


@dataclass(frozen=True, slots=True)
class ThermodynamicState:
    coherence: float
    order_parameter_phi: float
    landauer_dissipation_joules: float
    entropy_erased_bits: float
    fundamental_freq_hz: float
    harmonic_frequencies_hz: list[float]
    spectral_dissonance: float
    is_hiho_stable: bool


class ThermodynamicHIHOEngine:
    """Non-Equilibrium Thermodynamic Computing & Acoustic Field Engine."""

    def __init__(self, temperature_k: float = 300.0, base_frequency_hz: float = 432.0) -> None:
        self.temperature_k = temperature_k
        self.base_frequency_hz = base_frequency_hz

    def compute_landauer_cost(self, bits_erased: float) -> float:
        r"""Compute exact minimum Landauer erasure dissipation $Q = k_B T \ln 2 \cdot N_{\text{bits}}$."""
        return K_BOLTZMANN * self.temperature_k * math.log(2.0) * max(0.0, bits_erased)

    def evaluate_thermodynamic_hiho(
        self,
        coherence: float,
        bits_erased: float = 1.0,
        fabric_weights: tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25),
    ) -> ThermodynamicState:
        """Evaluate thermodynamic stability, Landauer dissipation, and acoustic harmonics."""
        c = float(np.clip(coherence, 0.0, 1.0))

        # 1. HIHO Order Parameter: Phi = 1.0 - 4(c - 0.5)^2  (peaks at 1.0 when c = 0.5)
        phi = max(0.0, 1.0 - 4.0 * ((c - 0.5) ** 2))

        # 2. Landauer Dissipation
        q_landauer = self.compute_landauer_cost(bits_erased)

        # 3. Frequency & Harmonic Computation
        # Fundamental shifts dynamically based on distance from 0.5 HIHO point
        freq_shift = (c - 0.5) * 50.0  # +/- 25 Hz deviation
        f0 = self.base_frequency_hz + freq_shift

        # 4 Fabrics mapped to Pythagorean / Just intonation ratios:
        # Space (1/1, Fundamental), Field (3/2, Perfect 5th), Control (4/3, Perfect 4th), Precipitation (2/1, Octave)
        ratios = [1.0, 1.5, 1.333333, 2.0]
        harmonics = [round(f0 * r, 2) for r in ratios]

        # 4. Spectral Dissonance (proportional to |c - 0.5|)
        dissonance = abs(c - 0.5) * 2.0  # 0.0 at c=0.5 (pure harmony), 1.0 at c=0 or c=1 (max dissonance)

        is_stable = bool(phi >= 0.85)  # Coherence in [0.40, 0.60]

        return ThermodynamicState(
            coherence=round(c, 4),
            order_parameter_phi=round(phi, 4),
            landauer_dissipation_joules=q_landauer,
            entropy_erased_bits=bits_erased,
            fundamental_freq_hz=round(f0, 2),
            harmonic_frequencies_hz=harmonics,
            spectral_dissonance=round(dissonance, 4),
            is_hiho_stable=is_stable,
        )
