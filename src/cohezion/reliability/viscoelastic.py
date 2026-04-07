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
        self.last_pressure = None
        self.last_time = None

    def calculate_dilation_adjustment(
        self,
        cpu: float,
        ram: float,
        vram: float,
        active_calls: int = 0,
        max_concurrency: int = 4,
        total_agents: int = 0,
        dt_override: float | None = None,
    ) -> float:
        """
        Calculate the viscous correction factor based on 'Semantic Pressure' change rate.
        Semantic Pressure combines hardware load with agentic density.

        Returns:
            A correction value to be subtracted from the base dilation factor.
        """
        now = time.time()

        # 1. Hardware Pressure (0.0 to 1.0)
        hw_pressure = max(cpu, ram, vram) / 100.0

        # 2. Agentic Pressure (Density of active reasoning)
        # Normalize calls against concurrency limits
        call_pressure = min(active_calls / max(1, max_concurrency), 2.0)
        # Weight total agents (Logarithmic scaling: 100 agents = 1.0 pressure boost)
        import math

        agent_pressure = math.log10(max(1, total_agents)) / 2.0

        # 3. Composite Semantic Pressure
        # Weights: 60% Hardware, 40% Agentic Density
        current_pressure = (hw_pressure * 0.6) + ((call_pressure + agent_pressure) * 0.4)
        current_pressure = min(current_pressure, 2.0)  # Allow over-pressure for rapid dilation

        if self.last_time is None:
            self.last_time = now - 2.0
            self.last_pressure = current_pressure

        dt = dt_override if dt_override is not None else (now - self.last_time)

        if dt > 0:
            # Hubble-rate equivalent: Delta Pressure over Delta Time
            pressure_rate = (current_pressure - self.last_pressure) / dt

            if pressure_rate > 0:
                # Rising semantic pressure = Increase Viscosity (Phantom expansion phase)
                # Slow down proactively BEFORE OOM/Thermal tripwire
                self.viscosity += pressure_rate * self.relaxation_tau
                self.viscosity = min(self.viscosity, 1.0)
            else:
                # Maxwell-type relaxation back to stable manifold state
                decay = max(0.0, 1.0 - dt / self.relaxation_tau)
                self.viscosity *= decay

        self.last_time = now
        self.last_pressure = current_pressure

        return max(0.0, self.viscosity)

    def reset(self):
        """Reset controller state."""
        self.viscosity = 0.0
        self.last_pressure = None
        self.last_time = None
