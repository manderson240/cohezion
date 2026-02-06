"""
Lattice Orchestrator (CSL) - The Cohezion Swarm Lattice.
A robust, self-evolving orchestration layer.
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from cohezion.agents.model_wrangler_agent import ModelWrangler
from cohezion.agents.surreal_dba_agent import SurrealDBDBA
from cohezion.core.persistence.surreal_client import SurrealClient, UniverseNode
from cohezion.reliability.monitor import ResourceMonitor
from cohezion.swarm.journey_narrator import JourneyNarrator
from cohezion.swarm.journey_tracker import JourneyTracker
from cohezion.swarm.swarm_types import Perspective, SwarmConfig, ThoughtVector

logger = logging.getLogger(__name__)


class LatticeState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()).replace("-", "_"))
    query: str
    context: dict[str, Any] = Field(default_factory=dict)
    urgency: Literal["low", "medium", "high"] = "medium"
    step_history: list[dict[str, Any]] = Field(default_factory=list)
    depth: int = 0
    max_depth: int = 5
    expert_responses: dict[str, Any] = Field(default_factory=dict)
    final_synthesis: str | None = None
    consensus_score: float = 0.0
    spi_score: float = 1.0
    routing_strategy: str = "consensus_fanout"
    degraded_mode: bool = False
    vram_pressure: float = 0.0

    class Config:
        arbitrary_types_allowed = True


class LatticeOrchestrator:
    def __init__(
        self, db_client: SurrealClient | None = None, config: SwarmConfig | None = None
    ):
        self.db = db_client or SurrealClient()
        self.config = config or SwarmConfig()
        self.monitor = ResourceMonitor()
        self.dba = SurrealDBDBA(config=self.config)
        self.wrangler = ModelWrangler(config=self.config)
        self.tracker = JourneyTracker()
        self.narrator = JourneyNarrator()

    async def ignite(
        self, query: str, context: dict | None = None, urgency: str = "medium"
    ) -> LatticeState:
        state = LatticeState(
            query=query,
            context=context or {},
            urgency=urgency,
            degraded_mode=self.config.degraded_mode,
        )
        journey_id = self.tracker.start_journey(query)
        logger.info(f"🚀 Lattice Journey Started: {journey_id}")
        await self._checkpoint(state)
        try:
            state = await self._run_logic(state)
        except Exception as e:
            logger.error(f"Lattice Logic FAIL: {e}", exc_info=True)
            state.step_history.append({"error": str(e), "timestamp": time.time()})
        await self._checkpoint(state)
        await self.tracker.end_journey(
            final_response=state.final_synthesis or "Consensus Pending",
            final_confidence=state.consensus_score,
        )
        logger.info("🏁 Lattice Journey Completed.")
        return state

    async def _run_logic(self, state: LatticeState) -> LatticeState:
        vitals = self.monitor.get_vitals()
        state.vram_pressure = vitals.get("vram_percent", 0.0)
        state = await self._dispatch_edl(state)
        state = await self._synthesize_consensus(state)
        return state

    async def _dispatch_edl(self, state: LatticeState) -> LatticeState:
        experts = ["architect", "engineer", "biologist", "quantum_hw", "quantum_algo"]
        tasks = [self._poll_expert(state, expert) for expert in experts]
        results = await asyncio.gather(*tasks)

        # In Pydantic, we assign a new dict to ensure validation/tracking
        new_responses = {}
        for expert, response in zip(experts, results):
            if response:
                new_responses[expert] = response
        state.expert_responses = new_responses
        return state

    async def _poll_expert(
        self, state: LatticeState, expert: str
    ) -> ThoughtVector | None:
        await asyncio.sleep(0.01)  # Ensure async switching
        return ThoughtVector(
            perspective=Perspective.TECHNICAL,
            content=f"[{expert.upper()}] Strategy Insight",
            confidence=0.85,
        )

    async def _synthesize_consensus(self, state: LatticeState) -> LatticeState:
        if not state.expert_responses:
            state.final_synthesis = "Incomplete consensus."
            return state
        synthesis = "FINAL SYNTHESIS:\n" + "\n".join(
            [f"- {k}: {v.content}" for k, v in state.expert_responses.items()]
        )
        state.final_synthesis = synthesis
        state.consensus_score = sum(
            v.confidence for v in state.expert_responses.values()
        ) / len(state.expert_responses)
        return state

    async def _checkpoint(self, state: LatticeState):
        try:
            node = UniverseNode(
                id=f"lattice_{state.session_id}_{state.depth}",
                content=state.model_dump_json(),
                node_type="lattice_state",
            )
            await self.db.store_node(node)
        except Exception as e:
            logger.error(f"Checkpoint failed: {e}")
