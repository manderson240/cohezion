"""Viscoelastic Controller - Proactive stability management using Maxwellian relaxation."""

from __future__ import annotations

import time


class ViscoelasticController:
    """
    Manages system dilation using a viscoelastic model.
    Based on Research 2512.00056 (Phantom deviation around mass-gap H*).
    """

    def __init__(self, relaxation_tau: float = 30.0):
        self.viscosity = 0.0
        self.relaxation_tau = relaxation_tau
        self.last_pressure: float | None = None
        self.last_time: float | None = None

    def calculate_dilation_adjustment(
        self, cpu: float, ram: float, vram: float, dt_override: float | None = None
    ) -> float:
        """
        Calculate the viscous correction factor based on the rate of pressure change.

        Returns:
            A correction value to be subtracted from the base dilation factor.
        """
        now = time.time()
        current_pressure = max(cpu, ram, vram) / 100.0

        if self.last_time is None:
            self.last_time = now - 2.0
            self.last_pressure = current_pressure

        dt = dt_override if dt_override is not None else (now - self.last_time)

        if dt > 0:
            pressure_rate = (current_pressure - self.last_pressure) / dt

            if pressure_rate > 0:
                # If pressure is rising, increase viscosity (Slow down more aggressively)
                self.viscosity += pressure_rate * self.relaxation_tau
                # Cap viscosity to prevent excessive or permanent dilation
                self.viscosity = min(self.viscosity, 1.0)
            else:
                # Maxwell-type relaxation back to equilibrium
                decay = max(0.0, 1.0 - dt / self.relaxation_tau)
                self.viscosity *= decay

        self.last_time = now
        self.last_pressure = current_pressure

        return max(0.0, self.viscosity)

    def reset(self) -> None:
        """Reset controller state."""
        self.viscosity = 0.0
        self.last_pressure = None
        self.last_time = None
