"""Dynamic Entropy-Bounded Horizon Controller (Pathway III - Consensus Architecture).
==================================================================================
Synthesizes:
1. Dynamic Stopping Rule:
   H_stop = min { t | S(a_t) >= S_crit OR h(s_t) <= 0 OR Delta d_D(z_t, z_0) >= D_max OR t >= H_max }
2. Eliminates exponential error compounding ((1+L)^t * epsilon_0) in open-loop simulation.
3. Automatically allocates deeper rollouts (up to 30 steps) when confidence is high,
   and early-truncates rollouts (4-6 steps) when epistemic uncertainty spikes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np


@dataclass(frozen=True)
class HorizonDecision:
    """Calculated simulation horizon and execution bounds."""

    computed_horizon: int
    should_terminate: bool
    termination_reason: str
    current_entropy: float
    geodesic_drift: float
    clearance_margin: float


class DynamicEntropyHorizonController:
    """Calculates adaptive mental simulation depth and monitors early termination."""

    def __init__(
        self,
        h_min: int = 4,
        h_max: int = 30,
        entropy_critical: float = 1.38,  # Critical entropy threshold (approx ln(4) in nats)
        max_geodesic_drift: float = 4.5,  # Maximum Poincaré ball distance before divergence
        base_horizon: int = 15,
    ) -> None:
        self.h_min = h_min
        self.h_max = h_max
        self.entropy_critical = entropy_critical
        self.max_geodesic_drift = max_geodesic_drift
        self.base_horizon = base_horizon

    def calculate_horizon(
        self,
        current_entropy: float,
        clearance_margin: float = 1.0,
        remaining_budget_fraction: float = 1.0,
    ) -> int:
        """Calculates optimal rollout depth proportional to confidence and remaining quota.
        
        Formula:
            H_dyn = clip(floor(H_base * (S_crit / (S_t + eps)) * (1 + h(s)/h_max)), H_min, H_max)
        """
        eps = 1e-6
        # Certainty scaling factor: higher when entropy is low
        certainty_factor = self.entropy_critical / max(eps, current_entropy + 0.1)
        # Margin boost: positive clearance margin safely allows deeper simulation
        margin_scale = max(0.2, min(2.0, 1.0 + (clearance_margin / 10.0)))
        # Budget conservation scale
        budget_scale = max(0.5, min(1.0, remaining_budget_fraction))

        raw_h = self.base_horizon * certainty_factor * margin_scale * budget_scale
        return int(np.clip(math.floor(raw_h), self.h_min, self.h_max))

    def evaluate_step(
        self,
        step_idx: int,
        step_entropy: float,
        geodesic_drift: float,
        clearance_margin: float = 1.0,
        current_max_horizon: Optional[int] = None,
    ) -> HorizonDecision:
        """Evaluates whether the ongoing mental simulation step should terminate early."""
        max_h = current_max_horizon or self.h_max

        # 1. Check critical predictive transition entropy
        if step_entropy >= self.entropy_critical:
            return HorizonDecision(
                computed_horizon=step_idx,
                should_terminate=True,
                termination_reason=f"Predictive entropy spiked ({step_entropy:.3f} >= {self.entropy_critical:.3f})",
                current_entropy=step_entropy,
                geodesic_drift=geodesic_drift,
                clearance_margin=clearance_margin,
            )

        # 2. Check AutoHarness safety clearance margin
        if clearance_margin <= 0.0:
            return HorizonDecision(
                computed_horizon=step_idx,
                should_terminate=True,
                termination_reason=f"AutoHarness clearance margin breached (margin: {clearance_margin:.3f} <= 0)",
                current_entropy=step_entropy,
                geodesic_drift=geodesic_drift,
                clearance_margin=clearance_margin,
            )

        # 3. Check hyperbolic Poincaré geodesic drift
        if geodesic_drift >= self.max_geodesic_drift:
            return HorizonDecision(
                computed_horizon=step_idx,
                should_terminate=True,
                termination_reason=f"Hyperbolic geodesic drift exceeded bounds ({geodesic_drift:.3f} >= {self.max_geodesic_drift:.3f})",
                current_entropy=step_entropy,
                geodesic_drift=geodesic_drift,
                clearance_margin=clearance_margin,
            )

        # 4. Check step limit
        if step_idx >= max_h:
            return HorizonDecision(
                computed_horizon=step_idx,
                should_terminate=True,
                termination_reason=f"Reached maximum allocated simulation horizon ({step_idx} >= {max_h})",
                current_entropy=step_entropy,
                geodesic_drift=geodesic_drift,
                clearance_margin=clearance_margin,
            )

        # Safe to proceed to next step in imagination
        return HorizonDecision(
            computed_horizon=max_h,
            should_terminate=False,
            termination_reason="Safe within Lyapunov and entropy bounds",
            current_entropy=step_entropy,
            geodesic_drift=geodesic_drift,
            clearance_margin=clearance_margin,
        )
