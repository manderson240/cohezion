"""Natural Capital Valuation — InVEST-inspired ecosystem services on the 12D manifold.

Maps Stanford's InVEST framework (22 models, 1000+ peer-reviewed papers) onto
the Genesis Engine manifold, treating the agentic universe as an ecosystem where
HIHO proximity IS habitat quality and compound engineering IS natural capital growth.

Five ecosystem services adapted from InVEST's most-used models:
  1. Habitat Quality  — H = 1 - 2|δ| where δ = coherence - 0.5
  2. Carbon Storage   — information density integrated over manifold region
  3. Water Yield      — energy flow along gauge field connections
  4. Pollination      — knowledge transfer (KnowledgeSpore paths)
  5. Sediment Retention — structural integrity (gauge curvature flatness)

The Seventh Generation projection (from Haudenosaunee Great Law) forecasts natural
capital 175 ticks forward to assess sustainability of current agent decisions.

References:
  - Sharp et al. (2020): InVEST User Guide, Stanford Natural Capital Project
  - Haudenosaunee Confederacy: Great Law of Peace (Seventh Generation Principle)
  - ~/vaults/cohezion-vault/scripts/drivers/invest_research_swarm.py (original)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np


logger = logging.getLogger(__name__)

# Haudenosaunee: decisions must consider impact 7 generations ahead
# At ~25 years per generation = 175 years. In simulation ticks, we use 175.
SEVENTH_GENERATION_HORIZON = 175


@dataclass
class EcosystemServiceMetrics:
    """Natural capital valuation for a manifold region."""

    habitat_quality: float  # [0, 1] — HIHO proximity
    carbon_storage: float  # Information density
    water_yield: float  # Energy flow
    pollination: float  # Knowledge transfer density
    sediment_retention: float  # Structural integrity (gauge flatness)
    total_natural_capital: float  # Weighted aggregate

    def to_dict(self) -> dict:
        return {
            "habitat_quality": self.habitat_quality,
            "carbon_storage": self.carbon_storage,
            "water_yield": self.water_yield,
            "pollination": self.pollination,
            "sediment_retention": self.sediment_retention,
            "total_natural_capital": self.total_natural_capital,
        }


@dataclass
class SeventhGenerationProjection:
    """Sustainability forecast using the Haudenosaunee Seventh Generation principle."""

    current_capital: float
    projected_capital: float  # Capital at +175 ticks
    growth_rate: float  # Compound growth rate per tick
    is_sustainable: bool  # True if projected ≥ current
    generations_until_depletion: int | None  # None if sustainable

    def to_dict(self) -> dict:
        return {
            "current_capital": self.current_capital,
            "projected_capital": self.projected_capital,
            "growth_rate": self.growth_rate,
            "is_sustainable": self.is_sustainable,
            "generations_until_depletion": self.generations_until_depletion,
        }


class NaturalCapitalValuation:
    """InVEST-inspired ecosystem services valuation for the 12D manifold.

    Treats the agentic universe as an ecosystem where coherent structures
    (EVOs, agents) ARE natural capital — valuable because they reduce entropy,
    maintain HIHO stability, and enable future work.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.weights = weights or {
            "habitat_quality": 0.3,
            "carbon_storage": 0.2,
            "water_yield": 0.2,
            "pollination": 0.15,
            "sediment_retention": 0.15,
        }
        self._capital_history: list[float] = []

    def evaluate(
        self,
        state_12d: np.ndarray,
        coherence: float,
        connectivity: float = 0.5,
        gauge_curvature: float = 0.0,
        spore_density: float = 0.0,
    ) -> EcosystemServiceMetrics:
        """Evaluate ecosystem services for a manifold state.

        Parameters
        ----------
        state_12d : np.ndarray
            12D axiomatic state vector.
        coherence : float
            Current HIHO coherence [0, 1].
        connectivity : float
            Network connectivity (normalized gauge coupling).
        gauge_curvature : float
            Gauge field curvature magnitude (0 = flat = healthy).
        spore_density : float
            KnowledgeSpore paths through this region.
        """
        # 1. Habitat Quality: H = 1 - 2|δ| where δ = coherence - 0.5
        delta = abs(coherence - 0.5)
        habitat_quality = max(0.0, 1.0 - 2.0 * delta)

        # 2. Carbon Storage: information density = mean(|state|)
        carbon_storage = float(np.mean(np.abs(state_12d)))

        # 3. Water Yield: energy flow = connectivity × stability
        stability = 1.0 - np.std(state_12d)
        water_yield = connectivity * max(0.0, stability)

        # 4. Pollination: knowledge transfer density
        pollination = min(1.0, spore_density)

        # 5. Sediment Retention: inverse of gauge curvature (flat = high retention)
        sediment_retention = 1.0 / (1.0 + gauge_curvature)

        # Weighted aggregate
        total = (
            self.weights["habitat_quality"] * habitat_quality
            + self.weights["carbon_storage"] * carbon_storage
            + self.weights["water_yield"] * water_yield
            + self.weights["pollination"] * pollination
            + self.weights["sediment_retention"] * sediment_retention
        )

        metrics = EcosystemServiceMetrics(
            habitat_quality=habitat_quality,
            carbon_storage=carbon_storage,
            water_yield=water_yield,
            pollination=pollination,
            sediment_retention=sediment_retention,
            total_natural_capital=total,
        )

        self._capital_history.append(total)
        return metrics

    def seventh_generation_projection(
        self,
        current_capital: float | None = None,
    ) -> SeventhGenerationProjection:
        """Project natural capital forward using the Seventh Generation principle.

        Uses the historical growth rate to forecast whether current decisions
        are sustainable across 175 ticks (7 generations × 25 ticks/generation).
        """
        if current_capital is None:
            if not self._capital_history:
                return SeventhGenerationProjection(
                    current_capital=0.0,
                    projected_capital=0.0,
                    growth_rate=0.0,
                    is_sustainable=False,
                    generations_until_depletion=0,
                )
            current_capital = self._capital_history[-1]

        # Compute growth rate from history (if available)
        if len(self._capital_history) >= 2:
            recent = self._capital_history[-10:]  # Last 10 evaluations
            if recent[0] > 0:
                growth_rate = (recent[-1] / recent[0]) ** (1.0 / len(recent)) - 1.0
            else:
                growth_rate = 0.0
        else:
            growth_rate = 0.0

        # Project forward
        projected = current_capital * (1.0 + growth_rate) ** SEVENTH_GENERATION_HORIZON

        is_sustainable = projected >= current_capital

        # Estimate depletion time (if declining)
        depletion = None
        if growth_rate < 0 and current_capital > 0:
            # Solve: capital × (1 + r)^t = 0 → t = -ln(capital) / ln(1+r)
            depletion = int(-np.log(0.01) / abs(np.log(1.0 + growth_rate)))

        return SeventhGenerationProjection(
            current_capital=current_capital,
            projected_capital=projected,
            growth_rate=growth_rate,
            is_sustainable=is_sustainable,
            generations_until_depletion=depletion,
        )

    @property
    def capital_history(self) -> list[float]:
        return list(self._capital_history)


__all__ = [
    "EcosystemServiceMetrics",
    "NaturalCapitalValuation",
    "SeventhGenerationProjection",
    "SEVENTH_GENERATION_HORIZON",
]
