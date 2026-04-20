import logging

import torch

from cohezion.persistence.obsidian_mcp import ObsidianMemoryMCP
from cohezion.persistence.surreal_logger import SurrealTrajectoryLogger
from cohezion.universe.triune_manifold import (
    TriuneState,
    calculate_hiho_coherence,
    compute_restoring_force,
)


logger = logging.getLogger(__name__)


class TriuneSimulationEngine:
    """
    Core engine for simulating state transitions within the Triune Manifold.

    Binds the TriuneState to SurrealDB and Obsidian persistence layers.
    """

    def __init__(
        self,
        state: TriuneState,
        surreal_logger: SurrealTrajectoryLogger,
        obsidian_mcp: ObsidianMemoryMCP,
    ):
        """
        Initializes the engine with initial state and persistence clients.

        Args:
            state: The starting TriuneState.
            surreal_logger: Client for trajectory indexing.
            obsidian_mcp: Client for semantic memory updates.
        """
        self.state = state
        self.surreal_logger = surreal_logger
        self.obsidian_mcp = obsidian_mcp

    async def step(self, dt: float, environment: torch.Tensor, trajectory_id: str) -> None:
        """
        Applies a single simulation step.

        1. Calculates HIHO coherence.
        2. Applies restoring forces to the 'Doer' layer.
        3. Persists the new state to SurrealDB and Obsidian.

        Args:
            dt: Time delta.
            environment: Current environment tensor (12D).
            trajectory_id: ID for this simulation journey.
        """
        # 1. Calculate Coherence
        coherence = calculate_hiho_coherence(self.state.doer, environment)

        # 2. Update State (Conceptual 'Doer' movement)
        # In this scaffold, we simply apply a small shift toward the environment
        # weighted by the restoring force.
        force = compute_restoring_force(coherence)

        # Simple Euler integration for demonstration
        # We nudge the doer toward the environment state
        self.state.doer = self.state.doer + (environment - self.state.doer) * force * dt

        # 3. Persistence
        try:
            await self.surreal_logger.log_trajectory(
                trajectory_id=trajectory_id, state=self.state, coherence=coherence
            )

            await self.obsidian_mcp.store_state_summary(
                trajectory_id=trajectory_id, state=self.state, coherence=coherence
            )

            logger.info(f"Engine step complete for {trajectory_id}. Coherence: {coherence:.4f}")
        except Exception as e:
            logger.error(f"Engine persistence failure: {e}")
            raise
