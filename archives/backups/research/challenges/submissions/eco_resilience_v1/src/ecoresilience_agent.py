"""Specialist agent for the Gemma 4 Good hackathon.
Bridges Traditional Ecological Knowledge (TEK) with Unified Physics (12D Manifolds).
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from cohezion.agents.base import BaseAgent
from cohezion.swarm.providers.gemma4_provider import Gemma4Provider
from cohezion.flume.manifolds.translator import ManifoldTranslator, ManifoldProjection
from cohezion.compound.triune_reviewer import TriuneReviewer
from cohezion.compound.copernicus_bridge import CopernicusState
from cohezion.flume.spectral_encoder import SpectralEncoder

logger = logging.getLogger(__name__)


class ResilienceState(BaseModel):
    """State of the ecosystem resilience simulation."""

    model_config = {"arbitrary_types_allowed": True}
    tek_insights: List[str] = []
    manifold_coords: Optional[np.ndarray] = None
    stability_score: float = 0.0
    proposed_strategy: str = ""
    is_stable: bool = False


class EcoResilienceAgent(BaseAgent):
    """
    EcoResilienceAgent implements a 4-regime cycle:
    SENSING -> CALCULATION -> SYNTHESIS -> STEERING.
    """

    def __init__(
        self,
        provider: Gemma4Provider,
        translator: ManifoldTranslator,
        spectral_encoder: SpectralEncoder,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.provider = provider
        self.translator = translator
        self.spectral_encoder = spectral_encoder
        self.reviewer = TriuneReviewer(provider)
        self.state = ResilienceState()

    async def process(self, input_text: str, **kwargs) -> str:
        """Implementation of the base agent process method.
        Routes to the internal 4-regime execute_cycle.
        """
        return await self.execute_cycle(input_text)

    async def execute_cycle(
        self, input_text: str, copernicus_state: Optional[CopernicusState] = None, **kwargs
    ) -> str:
        """Runs the full EcoResilience loop with integrated Triune Review and Live Sensing.

        Tiers: Sensing -> Calculation -> Synthesis -> [Triune Review] -> Steering.
        """
        # 1. SENSING PHASE (Local 2B/4B + Copernicus)
        satellite_context = ""
        spectral_latent = None
        if copernicus_state:
            indices = copernicus_state.spectral_indices
            satellite_context = (
                f"SATELLITE DATA: NDVI={indices.get('NDVI', 'N/A')}, "
                f"NDWI={indices.get('NDWI', 'N/A')}, SALI={indices.get('SALI', 'N/A')}. "
                f"Cloud cover: {copernicus_state.cloud_cover}%."
            )
            # Direct la-phase: map spectral data to FLUME latent space
            spectral_latent = self.spectral_encoder.encode_spectral_state(copernicus_state)

        sensing_prompt = (
            f"Sensing Task: Extract ecological interconnectedness and systemic balance. "
            f"SATELLITE CONTEXT: {satellite_context}\n"
            f"FIELD REPORT: {input_text}"
        )
        res_sensing = await self.provider.generate(
            model="gemma4:2b", prompt=sensing_prompt, regime="SENSING"
        )
        self.state.tek_insights.append(res_sensing.response)

        # Vectorize using FLUME
        text_latent = self.translator.encoder.encode(res_sensing.response)

        # SYMPHONY FUSION: Fuse textual TEK with spectral ground truth
        if spectral_latent is not None:
            latent = self.spectral_encoder.integrate_with_text(text_latent, spectral_latent)
        else:
            latent = text_latent

        # 2. CALCULATION PHASE (Cloud 31B)
        projection = self.translator.project(latent)
        self.state.manifold_coords = projection.coordinates
        self.state.stability_score = projection.coherence
        self.state.is_stable = projection.stability

        calc_prompt = (
            f"Project the following TEK insights onto a 12D physics manifold. "
            f"Current Projection: {projection.coordinates}. "
            f"Coherence: {projection.coherence}. "
            f"SATELLITE GROUND TRUTH: {satellite_context}. "
            f"Analyze for HIHO stability and potential equilibrium points. "
            f"Insights: {res_sensing.response}"
        )
        res_calc = await self.provider.generate(
            model="gemma4:31b-cloud", prompt=calc_prompt, regime="CALCULATION"
        )

        # 3. SYNTHESIS PHASE (Local 26B MoE)
        synth_prompt = (
            f"Synthesize a resilience strategy. "
            f"TEK Insights: {res_sensing.response}. "
            f"Physics Manifold Analysis: {res_calc.response}. "
            f"SATELLITE GROUND TRUTH: {satellite_context}. "
            f"Goal: Create a sustainable ecosystem state based on Unified Physics."
        )
        res_synth = await self.provider.generate(
            model="gemma4:26b-moe", prompt=synth_prompt, regime="SYNTHESIS"
        )

        # --- Triune Review Gate ---
        review_result = await self.reviewer.review(res_synth.response, projection.coordinates)

        if not review_result.is_approved:
            logger.warning(
                "Triune Review rejected synthesis (%.2f). Integrating critique into steering.",
                review_result.consensus_score,
            )
            res_synth.response = (
                f"{res_synth.response}\n\nREVIEW CRITIQUE: {review_result.final_critique}"
            )

        self.state.proposed_strategy = res_synth.response

        # 4. STEERING PHASE (Local 4B)
        steering_prompt = f"Refine the following strategy for immediate local implementation: {res_synth.response}"
        res_steer = await self.provider.generate(
            model="gemma4:4b", prompt=steering_prompt, regime="STEERING"
        )

        return res_steer.response

    def get_current_status(self) -> Dict[str, Any]:
        """Returns the agent's state for traceability."""
        return {
            "stability": self.state.stability_score,
            "is_stable": self.state.is_stable,
            "coords": self.state.manifold_coords.tolist()
            if self.state.manifold_coords is not None
            else None,
            "strategy": self.state.proposed_strategy,
        }
