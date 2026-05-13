"""Advanced Compound Orchestrator for EcoResilience.
Implements a multi-agent reflexive loop that uses the Triune Review
and HIHO Stability Guard to co-evolve a resilience strategy.
"""

from __future__ import annotations

import logging
import uuid

from pydantic import BaseModel

from cohezion.agents.specialists.ecoresilience_agent import EcoResilienceAgent
from cohezion.compound.resilience_loop import EcoResilienceCompoundLoop
from cohezion.compound.stability_guard import HIHOStabilityGuard
from cohezion.flume.manifolds.translator import ManifoldProjection


logger = logging.getLogger(__name__)


class CompoundEcoSymphony(BaseModel):
    """The final crystallized output of the compound process."""

    model_config = {"arbitrary_types_allowed": True}
    trace_id: str
    final_strategy: str
    manifold_state: ManifoldProjection
    review_consensus: float
    stability_score: float
    iterations: int
    refinement_history: list[str] = []


class EcoResilienceCompoundEngine:
    """
    The 'Compound' version of the EcoResilience loop.
    Instead of linear iteration, it implements a reflexive 'Symphony'
    where the output is refined by the adversarial Triune Review
    until a stable equilibrium is reached or the budget is exhausted.
    """

    def __init__(
        self,
        agent: EcoResilienceAgent,
        loop: EcoResilienceCompoundLoop,
        guard: HIHOStabilityGuard,
        max_depth: int = 5,
    ):
        self.agent = agent
        self.loop = loop
        self.guard = guard
        self.max_depth = max_depth

    async def compound_synthesize(self, input_text: str) -> CompoundEcoSymphony:
        """
        Runs the reflexive compound loop.
        """
        trace_id = str(uuid.uuid4())
        history = []
        iteration = 0

        # Initial run
        result = await self.loop.run_stable_simulation(input_text)
        current_strategy = result.final_strategy

        # Use the agent's current state to get the manifold projection
        last_projection = self.agent.translator.project(self.agent.translator.encoder.encode(current_strategy))

        while iteration < self.max_depth:
            iteration += 1
            logger.info(f"Compound Symphony - Iteration {iteration}/{self.max_depth}")

            # 1. Triune Review (The Adversarial Gate)
            review = await self.agent.reviewer.review(current_strategy, last_projection.coordinates)

            # 2. HIHO Stability Check (The Physical Gate)
            stability_check = await self.guard.verify(last_projection, current_strategy)

            if review.is_approved and stability_check.is_stable:
                logger.info("Symphony Converged: Both Triune and HIHO gates passed.")
                return CompoundEcoSymphony(
                    trace_id=trace_id,
                    final_strategy=current_strategy,
                    manifold_state=last_projection,
                    review_consensus=review.consensus_score,
                    stability_score=stability_check.coherence,
                    iterations=iteration,
                    refinement_history=history,
                )

            # 3. Reflexive Refinement
            critique = f"TRIUNE CRITIQUE: {review.final_critique}. STABILITY ERROR: {stability_check.suggestion}"
            history.append(critique)

            logger.warning(
                "Symphony out of tune. Refining strategy... (S: %.3f, C: %.3f)",
                stability_check.coherence,
                review.consensus_score,
            )

            # Update the input to force the agent to la-phase the correction
            refined_input = (
                f"Refine the previous strategy using these corrections: {critique}\nOriginal Request: {input_text}"
            )

            # Execute the agent cycle again
            current_strategy = await self.agent.execute_cycle(refined_input)

            # Update projection for next loop
            last_projection = self.translator_project(current_strategy)

        return CompoundEcoSymphony(
            trace_id=trace_id,
            final_strategy=current_strategy,
            manifold_state=last_projection,
            review_consensus=0.0,
            stability_score=last_projection.coherence,
            iterations=iteration,
            refinement_history=history,
        )

    def translator_project(self, text: str) -> ManifoldProjection:
        latent = self.agent.translator.encoder.encode(text)
        return self.agent.translator.project(latent)
