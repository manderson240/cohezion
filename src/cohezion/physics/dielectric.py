"""Diaelectric / Dielectric field bridge module.

Models the Biefield-Brown electrohydrodynamic (EHD) thrust effect and its
mapping to U(1) gauge theory via permittivity tensor modification of the vacuum.

References:
    Brown, T.T. (1956). Electrokinetic Apparatus. US Patent 2,949,550.
    Talley, R.L. (1991). Twenty-First Century Propulsion. USAF Phillips Lab PL-TR-91-3009.
    Puthoff, H.E. (2002). Engineering the Zero-Point Field. Ann. Fond. L. de Broglie 27(4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)

_U1_GENERATOR_INDEX: int = 2  # L_z — rotation about z-axis for U(1) subgroup


@dataclass
class DielectricField:
    """Asymmetric capacitor in a dielectric medium.

    Models permittivity-driven EHD thrust (Biefield-Brown effect) and maps
    the permittivity deviation to a U(1) GaugeConnection for integration with
    Cohezion's gauge theory module (FourFabricGauge).
    """

    permittivity_tensor: np.ndarray = field(default_factory=lambda: np.eye(3, dtype=np.float64))
    electrode_separation: float = 1e-2  # metres
    voltage: float = 1e4  # volts
    fabric_name: str = "field"  # one of: space, field, control, precipitation

    def __post_init__(self) -> None:
        if self.permittivity_tensor.shape != (3, 3):
            raise ValueError(
                f"permittivity_tensor must be 3x3, got {self.permittivity_tensor.shape}"
            )

    @property
    def mean_permittivity(self) -> float:
        """Scalar effective permittivity (trace / 3)."""
        return float(np.trace(self.permittivity_tensor)) / 3.0

    def biefield_brown_force(self) -> np.ndarray:
        """EHD thrust vector using Christenson-Moller scaling.

        F = ε₀ · ε_eff · (V/d)² · A_eff  [N/m²]

        Direction is along the electric field gradient (z-axis by convention).
        """
        eps_0 = 8.854e-12  # F/m
        eps_eff = self.mean_permittivity
        e_field = self.voltage / self.electrode_separation
        # Unit area thrust (per m²); direction along z
        magnitude = eps_0 * eps_eff * e_field**2
        return np.array([0.0, 0.0, magnitude], dtype=np.float64)

    def to_gauge_connection(self):
        """Map permittivity deviation to a U(1) GaugeConnection.

        Permittivity deviation from vacuum (ε_r - 1) modifies local vacuum
        impedance, equivalent to a U(1) gauge potential in the fiber bundle.
        Returns a GaugeConnection object from cohezion.physics.gauge_theory.
        """
        from cohezion.physics.gauge_theory import GaugeConnection  # lazy import

        eps_deviation = self.permittivity_tensor - np.eye(3)
        # Embed in so(3) ≅ R³ potential: use the z-row as the gauge potential
        potential = np.zeros((3, 3), dtype=np.float64)
        potential[_U1_GENERATOR_INDEX, :] = np.diag(eps_deviation)
        gc = GaugeConnection(fabric_name=self.fabric_name)
        gc.set_potential(potential)
        return gc


__all__ = ["DielectricField"]
