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
from cohezion.protocols.stitch.composer import stitch_composer, StitchSkillDefinition
from cohezion.protocols.agent_protocols.handoffs import handoff_manager, AgentHandoff
from cohezion.protocols.sovereignty.filter import sovereignty_filter

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

        # STITCH-SKILLS: Register indigenous-physics skills
        self._register_stitch_skills()

    def _register_stitch_skills(self):
        """Registers the EcoResilience la-phase skills in the Stitch composer."""
        skills = [
            StitchSkillDefinition(
                skill_id="eco_sensing",
                name="Eco-Sensing",
                description="Extracts ecological interconnectedness and systemic balance.",
                regime="SENSING",
            ),
            StitchSkillDefinition(
                skill_id="manifold_calc",
                name="Manifold Calculation",
                description="Projects TEK insights onto 12D physics manifold.",
                regime="CALCULATION",
            ),
            StitchSkillDefinition(
                skill_id="resilience_synth",
                name="Resilience Synthesis",
                description="Synthesizes a resilience strategy based on Unified Physics.",
                regime="SYNTHESIS",
            ),
            StitchSkillDefinition(
                skill_id="steering_refine",
                name="Steering Refinement",
                description="Refines strategy for immediate local implementation.",
                regime="STEERING",
            ),
        ]
        for skill in skills:
            stitch_composer.register_skill(skill)

    async def process(self, input_text: str, **kwargs) -> str:
        """Implementation of the base agent process method.
        Routes to the internal 4-regime execute_cycle.
        """
        return await self.execute_cycle(input_text, **kwargs)

    async def execute_cycle(
        self, input_text: str, copernicus_state: Optional[CopernicusState] = None, **kwargs
    ) -> str:
        """Runs the full EcoResilience loop with integrated Triune Review and Live Sensing.

        Symphony-Enhanced: Utilizes Stitch-Skills for dynamic composition and
        Agent Protocols for standardized handoffs.
        """
        # 1. SENSING PHASE (Local 2B/4B + Copernicus)
        # Create a handoff from the external environment (Sourcing) -> Agent
        env_handoff = handoff_manager.create_handoff(
            source="ENVIRONMENT",
            target=self.__class__.__name__,
            payload={"input_text": input_text, "copernicus_state": copernicus_state},
            summary="Initial sensing request with biophysical ground truth.",
        )

        payload = handoff_manager.resolve_handoff(env_handoff)

        satellite_context = ""
        spectral_latent = None
        if payload.get("copernicus_state"):
            indices = payload["copernicus_state"].spectral_indices
            s_state = payload["copernicus_state"]
            satellite_context = (
                f"SATELLITE DATA: NDVI={indices.get('NDVI', 'N/A')}, "
                f"NDWI={indices.get('NDWI', 'N/A')}, SALI={indices.get('SALI', 'N/A')}. "
                f"Cloud cover: {s_state.cloud_cover}%. "
            )
            spectral_latent = self.spectral_encoder.encode_spectral_state(s_state)

        sensing_prompt = (
            f"Sensing Task: Extract ecological interconnectedness and systemic balance. "
            f"SATELLITE CONTEXT: {satellite_context}\n"
            f"FIELD REPORT: {input_text}"
        )
        res_sensing = await self.provider.generate(
            model=self.model_name, prompt=sensing_prompt, regime="SENSING"
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

        # SOVEREIGNTY-GUARD: Scrub TEK descriptors before sending to Cloud 31B
        # The prompt is the 'leakage boundary'
        prompt_raw = (
            f"Project the following TEK insights onto a 12D physics manifold. "
            f"Current Projection: {projection.coordinates}. "
            f"Coherence: {projection.coherence}. "
            f"SATELLITE GROUND TRUTH: {satellite_context}. "
            f"Analyze for HIHO stability and potential equilibrium points. "
            f"Insights: {res_sensing.response}"
        )
        cleaned_prompt, scrubbed = sovereignty_filter.scrub(prompt_raw)

        if scrubbed:
            logger.info(
                f"Sovereignty Filter active: scrubbed {len(scrubbed)} terms from cloud payload."
            )

        calc_prompt = cleaned_prompt
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
            model=self.model_name, prompt=steering_prompt, regime="STEERING"
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
