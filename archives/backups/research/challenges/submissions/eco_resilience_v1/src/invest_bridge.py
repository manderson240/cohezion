"""Bridge for integrating InVEST (Integrated Valuation of Ecosystem Services and Tradeoffs)
into the EcoResilience swarm.

Handles the ingestion of spatially-explicit biophysical data and
converts it into FLUME-compatible latent representations for
Symphonic reasoning.
"""

from __future__ import annotations

import logging

import numpy as np
from pydantic import BaseModel, Field

from cohezion.flume.vae_encoder import FlumeVAEEncoder


logger = logging.getLogger(__name__)


class InvestState(BaseModel):
    """Represents a snapshot of InVEST model outputs for a specific region."""

    model_name: str  # e.g., "Coastal Blue Carbon", "Shedding", "Sabu-Sabu-Sensing"
    biophysical_value: float = Field(
        ..., description="Quantified service value (e.g., tons of C/ha)"
    )
    spatial_resolution: str
    metrics: dict[str, float] = Field(default_factory=dict)
    tradeoff_index: float = 0.0  # 0.0 (extreme conflict) to 1.0 (perfect synergy)


class InVESTBridge:
    """
    Bridges InVEST quantitative outputs with the FLUME latent space.
    This allows the swarm to 'sense' biophysical ground truth.
    """

    def __init__(self, encoder: FlumeVAEEncoder):
        self.encoder = encoder

    def quantify_to_latent(self, state: InvestState) -> np.ndarray:
        """
        Converts an InVEST state snapshot into a FLUME latent vector.

        L_latent = Encoder(Textual Representation of Quantified Metrics)
        """
        # Create a descriptive string of the biophysical state
        # This 'grounds' the quantitative data in a way the LLM and VAE understand
        state_description = (
            f"InVEST Model: {state.model_name}. "
            f"Biophysical Value: {state.biophysical_value}. "
            f"Tradeoff Index: {state.tradeoff_index}. "
            f"Metrics: {state.metrics}"
        )

        # Use the FLUME encoder to move from quantitative text to 256D latent space
        return self.encoder.encode(state_description)

    def analyze_tradeoff(self, state_a: InvestState, state_b: InvestState) -> float:
        """
        Calculates the tension between two competing natural capital services.
        Example: Carbon Sequestration (A) vs. Local Fishing Access (B).
        """
        # Simplified tradeoff analysis: Normalized difference in value vs. overlap
        # In a real system, this would use InVEST's specific tradeoff indices.
        val_a = state_a.biophysical_value
        val_b = state_b.biophysical_value

        # Higher difference in value often indicates higher tension/tradeoff
        tension = abs(val_a - val_b) / (max(val_a, val_b) + 1e-6)
        return 1.0 - tension  # Returns synergy score (1.0 = high synergy, 0.0 = high conflict)

    async def get_invest_metrics(self, region: str, model: str) -> InvestState:
        """
        Simulates fetching data from an InVEST project file or API.
        """
        # Mocking InVEST output for simulation
        # In production, this would read GeoTIFF/CSV outputs from InVEST
        return InvestState(
            model_name=model,
            biophysical_value=np.random.uniform(10.0, 100.0),
            spatial_resolution="30m",
            metrics={
                "carbon_density": np.random.uniform(0.1, 0.5),
                "salinity": np.random.uniform(0, 1),
            },
            tradeoff_index=np.random.uniform(0, 1),
        )
