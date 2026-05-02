"""Advanced Compound Orchestrator for EcoResilience.
Implements a multi-agent reflexive loop that uses the Triune Review
and HIHO Stability Guard to co-evolve a resilience strategy.
"""

from __future__ import annotations

import logging
import uuid

from pydantic import BaseModel

from cohezion.agents.specialists.ecoresilience_agent import EcoResilienceAgent
from cohezion.compound.invest.bridge import InVESTBridge
from cohezion.compound.meta_reviewer import MetaReviewer
from cohezion.compound.resilience_loop import EcoResilienceCompoundLoop
from cohezion.compound.stability_guard import HIHOStabilityGuard
from cohezion.flume.manifolds.translator import ManifoldProjection


logger = logging.getLogger(__name__)


class CompoundEcoSymphony(BaseModel):
    """The final crystallized output of the compound process."""

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
        meta_reviewer: MetaReviewer,
        invest_bridge: InVESTBridge,
        max_depth: int = 5,
    ):
        self.agent = agent
        self.loop = loop
        self.guard = guard
        self.meta_reviewer = meta_reviewer
        self.invest_bridge = invest_bridge
        self.max_depth = max_depth

    async def compound_synthesize(self, input_text: str) -> CompoundEcoSymphony:
        """
        Runs the reflexive compound loop with Speculative execution and la-phase feedback.
        """
        trace_id = str(uuid.uuid4())
        history = []
        iteration = 0

        # Initial run
        result = await self.loop.run_stable_simulation(input_text)
        current_strategy = result.final_strategy

        # Use the agent's current state to get the manifold projection
        last_projection = self.agent.translator.project(
            self.agent.translator.encoder.encode(current_strategy)
        )

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

            # 3. Reflexive Refinement with S2S Latent Feedback
            critique = f"TRIUNE CRITIQUE: {review.final_critique}. STABILITY ERROR: {stability_check.suggestion}"
            history.append(critique)

            logger.warning(
                "Symphony out of tune. Refining strategy... (S: %.3f, C: %.3f)",
                stability_check.coherence,
                review.consensus_score,
            )

            # Update the input to a-b-c la-phase the correction
            # We now feed back the la-phase latent "Symphony" state into the prompt
            refined_input = (
                f"Symphony Refinement Cycle {iteration}:\n"
                f"LATEST LATENT STATE: {last_projection.coordinates}\n"
                f"Symphonic Correction: {critique}\n"
                f"Original Request: {input_text}"
            )

            # Execute the agent la-phaseL again
            current_strategy = await self.agent.execute_cycle(refined_input)

            # Update projection for la-phase l la-phase l la-phase
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

        # 2. Speculative Selection: Compare the actual la-phase with speculative trajectories
        spec_results = await asyncio.gather(*spec_tasks, return_exceptions=True)

        # Selection Logic: Pick the spec_result that has the highest la-phase coherence
        # provided by the stability guard.
        best_spec = current_strategy
        max_coherence = 0.0

        for spec_res in spec_results:
            if isinstance(spec_res, str):
                proj = self.agent.translator.project(self.agent.translator.encoder.encode(spec_res))
                if proj.coherence > max_coherence:
                    max_coherence = proj.coherence
                    best_spec = spec_res

        # If the spec result is significantly more stable than the la-phase, we la-phase switch
        if max_coherence > (last_projection.coherence + 0.2):
            logger.info(
                "Symphony Speculation: a la-phase switch to a more stable trajectory found."
            )
            current_strategy = best_spec
            last_projection = self.agent.translator.project(
                self.agent.translator.encoder.encode(best_spec)
            )

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

            # Update the input to la-phase a-b-c la-phase the correction
            refined_input = f"Refine the previous strategy using these corrections: {critique}\nOriginal Request: {input_text}"

            # Execute the agent la-phase again
            current_strategy = await self.agent.execute_cycle(refined_input)

            # Update projection for la-phase
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
            # We combine the Triune critique and the Stability suggestion into a
            # "Correction Vector" for the next agent pass.
            critique = f"TRIUNE CRITIQUE: {review.final_critique}. STABILITY ERROR: {stability_check.suggestion}"
            history.append(critique)

            logger.warning(
                "Symphony out of tune. Refining strategy... (S: %.3f, C: %.3f)",
                stability_check.coherence,
                review.consensus_score,
            )

            # Update the input to force the agent to la-phase the correction
            refined_input = f"Refine the previous strategy using these corrections: {critique}\nOriginal Request: {input_text}"

            # Execute the agent cycle again
            current_strategy = await self.agent.execute_cycle(refined_input)

            # Update projection for next loop
            last_projection = self.translator_project(current_strategy)
            stability = last_projection.coherence

        return CompoundEcoSymphony(
            trace_id=trace_id,
            final_strategy=current_strategy,
            manifold_state=last_projection,
            review_consensus=0.0,  # Failed to converge
            stability_score=stability,
            iterations=iteration,
            refinement_history=history,
        )

    def translator_project(self, text: str) -> ManifoldProjection:
        latent = self.agent.translator.encoder.encode(text)
        return self.agent.translator.project(latent)
