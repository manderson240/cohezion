"""Compound orchestrator for the EcoResilience simulation.
Implements the la-phase loop with a HIHO Stability Guard and
 experience persistence mapping to SurrealDB.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from cohezion.agents.specialists.ecoresilience_agent import EcoResilienceAgent
from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.stability_guard import HIHOStabilityGuard
from cohezion.flume.manifolds.translator import ManifoldProjection


logger = logging.getLogger(__name__)


class ResilienceExecutionResult(BaseModel):
    """Final outcome of a compound resilience loop."""

    final_strategy: str
    stability_score: float
    is_stable: bool
    iterations: int
    trace_id: str


class EcoResilienceCompoundLoop:
    """
    Compound Engineering loop for EcoResilience.
    Sensing -> Calculation -> Synthesis -> [Stability Guard] -> Steering.
    """

    def __init__(
        self,
        agent: EcoResilienceAgent,
        executor: CompoundExecutor,
        guard: HIHOStabilityGuard,
    ):
        self.agent = agent
        self.executor = executor
        self.guard = guard

    async def run_stable_simulation(
        self, input_text: str, max_retries: int = 3
    ) -> ResilienceExecutionResult:
        """
        Executes the EcoResilience loop with a stability-driven refinement cycle.
        """
        iteration = 0
        current_strategy = ""
        last_projection: ManifoldProjection | None = None

        while iteration < max_retries:
            iteration += 1
            logger.info("EcoResilience Loop Iteration %d...", iteration)

            # 1. execute the agent's internal 4-regime cycle
            # Note: We can't easily split the agent's internal execute_cycle
            # without modifying the agent, but we can verify the result.
            current_strategy = await self.agent.execute_cycle(input_text)

            # Retrieve the current manifold projection from the agent's state
            # This is where the 'Fluid Latent' state lives.
            last_projection = self.agent.translator.project(
                self.agent.translator.encoder.encode(current_strategy)
            )

            # 2. HIHO Stability Guard Verification
            check = await self.guard.verify(last_projection, current_strategy)

            if not self.guard.should_refine(check):
                logger.info("HIHO Stability verified (%.3f). Loop exiting.", check.coherence)
                return ResilienceExecutionResult(
                    final_strategy=current_strategy,
                    stability_score=check.coherence,
                    is_stable=True,
                    iterations=iteration,
                    trace_id=str(id(current_strategy)),
                )

            logger.warning(
                "Instability detected (%.3f). Triggering refinement... %s",
                check.coherence,
                check.suggestion,
            )

            # 3. Compound Refinement: update input for the next iteration to fix instability
            input_text = (
                f"Refine the previous strategy: {current_strategy}. Suggestion: {check.suggestion}"
            )

        return ResilienceExecutionResult(
            final_strategy=current_strategy,
            stability_score=last_projection.coherence if last_projection else 0.0,
            is_stable=False,
            iterations=iteration,
            trace_id=str(id(current_strategy)),
        )


# Singleton factory for the loop
_loop_instance: EcoResilienceCompoundLoop | None = None


def get_resilience_loop(
    agent: EcoResilienceAgent, executor: CompoundExecutor, guard: HIHOStabilityGuard
) -> EcoResilienceCompoundLoop:
    global _loop_instance
    if _loop_instance is None:
        _loop_instance = EcoResilienceCompoundLoop(agent, executor, guard)
    return _loop_instance
