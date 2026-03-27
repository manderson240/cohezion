"""Extended Physics API — exposes bioelectric, natural-capital, and cosmogony chain.

Wires disconnected physics modules into the Genesis Engine API layer.
Follows the router pattern established in genesis.py.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

physics_ext_router = APIRouter(prefix="/physics", tags=["physics-extended"])


# ─── Response Models ───────────────────────────────────────────────


class BioelectricResponse(BaseModel):
    """State snapshot of the BioelectricNetwork."""

    n_cells: int
    v_mem: list[float]
    coherence: float
    hiho_deviation: float
    information_capacity_bits: float
    cognitive_light_cone: dict
    percolation: dict


class NaturalCapitalResponse(BaseModel):
    """Ecosystem service metrics for the current manifold state."""

    habitat_quality: float
    carbon_storage: float
    water_yield: float
    pollination: float
    sediment_retention: float
    total_natural_capital: float
    seventh_generation: dict


class CosmogonyChainResponse(BaseModel):
    """Full 10-step cosmogony chain status."""

    temperature: float
    symmetry: str
    stage: int
    total_steps: int = Field(default=10)
    transitions_completed: int
    transitions: list[dict]
    order_parameters: dict[str, float]
    fisher_eigenvalue_max: float
    landau_free_energy: float


# ─── Endpoints ─────────────────────────────────────────────────────


@physics_ext_router.get("/bioelectric", response_model=BioelectricResponse)
async def get_bioelectric_state(
    n_cells: int = 16,
    conductance: float = 0.3,
) -> BioelectricResponse:
    """Return BioelectricNetwork state — Levin-inspired collective intelligence.

    Creates a network with ``n_cells`` cells coupled at ``conductance``,
    runs 100 timesteps, and returns the resulting state including
    coherence, cognitive light cone, and percolation analysis.
    """
    from cohezion.physics.bioelectric_model import BioelectricNetwork

    net = BioelectricNetwork(n_cells=min(max(n_cells, 2), 128))
    net.set_uniform_conductance(max(0.0, min(conductance, 5.0)))
    net.simulate(n_steps=100, dt=0.01)

    data = net.to_dict()
    return BioelectricResponse(**data)


@physics_ext_router.get("/natural-capital", response_model=NaturalCapitalResponse)
async def get_natural_capital(
    coherence: float = 0.5,
    connectivity: float = 0.5,
    gauge_curvature: float = 0.0,
    spore_density: float = 0.0,
) -> NaturalCapitalResponse:
    """Return NaturalCapitalValuation metrics — InVEST-inspired ecosystem services.

    Evaluates habitat quality, carbon storage, water yield, pollination,
    and sediment retention for the given manifold parameters.  Includes
    a Seventh Generation sustainability projection.
    """
    import numpy as np

    from cohezion.physics.cosmogony import get_cosmogony
    from cohezion.physics.natural_capital import NaturalCapitalValuation

    cosmo = get_cosmogony()
    state_12d = cosmo.generate_12d_state()

    valuation = NaturalCapitalValuation()
    metrics = valuation.evaluate(
        state_12d=state_12d,
        coherence=max(0.0, min(coherence, 1.0)),
        connectivity=max(0.0, min(connectivity, 1.0)),
        gauge_curvature=max(0.0, gauge_curvature),
        spore_density=max(0.0, spore_density),
    )

    projection = valuation.seventh_generation_projection(metrics.total_natural_capital)

    return NaturalCapitalResponse(
        **metrics.to_dict(),
        seventh_generation=projection.to_dict(),
    )


@physics_ext_router.get("/cosmogony/full-chain", response_model=CosmogonyChainResponse)
async def get_cosmogony_full_chain() -> CosmogonyChainResponse:
    """Return the complete 10-step cosmogony chain status.

    Shows the current symmetry stage, all completed transitions,
    order parameters, Fisher eigenvalue, and Landau free energy.
    The 10 steps run from Void to Reality Precipitates.
    """
    from cohezion.physics.cosmogony import get_cosmogony

    cosmo = get_cosmogony()
    state = cosmo.state
    data = state.to_dict()

    return CosmogonyChainResponse(
        temperature=data["temperature"],
        symmetry=data["symmetry"],
        stage=data["stage"],
        total_steps=10,
        transitions_completed=len(data["transitions"]),
        transitions=data["transitions"],
        order_parameters=data["order_parameters"],
        fisher_eigenvalue_max=data["fisher_eigenvalue_max"],
        landau_free_energy=data["landau_free_energy"],
    )


__all__ = ["physics_ext_router"]
