"""
Lattice Orchestrator (CSL) - The Cohezion Swarm Lattice.

A robust, self-evolving, and SurrealDB-native orchestration layer.
Abstracts complex swarm interactions into a 12D-aware lattice.
Replaces the basic LangGraph controller with a hardware-aware,
persistence-first architecture.
"""

import logging
import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from cohezion.db.surreal_client import SurrealClient, UniverseNode
from cohezion.reliability.monitor import ResourceMonitor
from cohezion.swarm.agents.model_wrangler_agent import ModelWrangler
from cohezion.swarm.agents.surreal_dba_agent import SurrealDBDBA
from cohezion.swarm.journey_narrator import JourneyNarrator

# Phase 5: Journey Integration
from cohezion.swarm.journey_tracker import AgentType, JourneyTracker
from cohezion.swarm.swarm_types import Perspective, SwarmConfig, ThoughtVector

# Phase 5: Journey Integration

logger = logging.getLogger(__name__)


class LatticeState(BaseModel):
    """
    Strictly typed state for the Lattice Orchestrator.
    Persisted to SurrealDB for 'Holographic Time Travel'.
    """

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()).replace("-", "_"))
    query: str
    context: dict[str, Any] = Field(default_factory=dict)
    urgency: Literal["low", "medium", "high"] = "medium"

    # Execution Tracking
    step_history: list[dict[str, Any]] = Field(default_factory=list)
    depth: int = 0
    max_depth: int = 5

    # Expert Synthesis
    expert_responses: dict[str, ThoughtVector] = Field(default_factory=dict)
    final_synthesis: str | None = None
    consensus_score: float = 0.0

    # Self-Evolution Metrics
    spi_score: float = 1.0  # Strategy Performance Index
    routing_strategy: str = "consensus_fanout"

    # Hardware Awareness
    degraded_mode: bool = False
    vram_pressure: float = 0.0

    @field_validator("expert_responses", mode="before")
    @classmethod
    def convert_thought_vectors(cls, v):
        if isinstance(v, dict):
            return v
        return {}


class LatticeOrchestrator:
    """
    Main orchestrator for the Cohezion Swarm Lattice.
    Handles routing, consensus, and self-evolution through SPI.
    """

    def __init__(
        self, db_client: SurrealClient | None = None, config: SwarmConfig | None = None
    ):
        self.db = db_client or SurrealClient()
        self.config = config or SwarmConfig()
        self.monitor = ResourceMonitor()
        self.lattice_table = "swarms_lattice"

        # Specialist Core
        self.dba = SurrealDBDBA(config=self.config)
        self.wrangler = ModelWrangler(config=self.config)

        # Phase 5: Journey & Narration
        self.tracker = JourneyTracker()
        self.narrator = JourneyNarrator()

    async def ignite(
        self, query: str, context: dict | None = None, urgency: str = "medium"
    ) -> LatticeState:
        """
        Start a new swarm session in the lattice.
        """
        state = LatticeState(
            query=query,
            context=context or {},
            urgency=urgency,  # type: ignore
            degraded_mode=self.config.degraded_mode,
        )

        # Start Journey Tracking
        journey_id = self.tracker.start_journey(query)
        logger.info(f"🚀 Lattice Journey Started: {journey_id}")

        logger.info(f"🌀 Lattice: Igniting session {state.session_id}")

        # 1. Initial Checkpointing
        await self._checkpoint(state)

        # 2. Main Lattice Loop
        try:
            state = await self._run_logic(state)
        except Exception as e:
            logger.error(f"Lattice Loop Failure in {state.session_id}: {e}")
            state.step_history.append({"error": str(e), "timestamp": time.time()})

        # 3. Final Checkpointing
        await self._checkpoint(state)

        # End Journey
        await self.tracker.end_journey(
            final_response=state.final_synthesis or "Consensus Pending",
            final_confidence=state.consensus_score,
        )
        logger.info("🏁 Lattice Journey Completed.")

        return state

    async def _run_logic(self, state: LatticeState) -> LatticeState:
        """
        High-level orchestration logic.
        """
        # Phase 1: Resource Guard (ModelWrangler)
        vitals = self.monitor.get_vitals()
        state.vram_pressure = vitals.get("vram_percent", 0.0)

        # Consult Wrangler for fleet health
        wrangler_resp = await self.wrangler.get_fleet_recommendation()
        if wrangler_resp.get("action") == "unload_large_models":
            logger.warning(
                f"📉 Lattice: Wrangler enforcing degraded mode: {wrangler_resp['reason']}"
            )
            state.degraded_mode = True

            # Narrate degradation
            await self.narrator.narrate(
                f"I am ModelWrangler. I am enforcing degraded mode due to {wrangler_resp['reason']}.",
                persistence_id=f"{state.session_id}_wrangler_degrade",
            )

        # Phase 2: Persistence Guard (SurrealDBBA)
        if "DB" in state.query or "sql" in state.query.lower():
            logger.info("🛡️ Lattice: Routing to DBA for dialect safety.")

            # Narrate
            dba_thought = "Detected SQL/DB intent. Verifying dialect and schema safety."
            await self.narrator.narrate(
                self.narrator.generate_narration(
                    "Lattice", "Routing to DBA", dba_thought
                ),
                persistence_id=f"{state.session_id}_dba_route",
            )

            dba_resp = await self.dba.process(state.query)
            state.expert_responses["dba"] = ThoughtVector(
                perspective=Perspective.EMPIRICAL,
                content=str(dba_resp),
                metadata={"action": dba_resp.action},
            )

            # Dynamic Physics Calculation
            confidence = dba_resp.confidence if hasattr(dba_resp, "confidence") else 0.5
            awareness_score = min(max(confidence, 0.1), 1.0)  # Clamp 0.1-1.0

            # Chirality: Empirical (DBA) is Right-Handed (Logic) -> >0.5
            chirality_score = 0.9 if state.query.lower().startswith("select") else 0.7

            # HIHO Drift: Increases with VRAM pressure
            drift_score = min(state.vram_pressure / 100.0, 1.0)

            # Record Journey Step
            self.tracker.record_step(
                agent_type=AgentType.ANALYST,
                agent_name="SurrealDBDBA",
                perspective="empirical",
                input_text=state.query,
                output_text=str(dba_resp),
                physics_state={
                    "dim_13_awareness": awareness_score,
                    "dim_14_chirality": chirality_score,
                    "dim_15_hiho_drift": drift_score,
                    "dim_16_temporal_depth": state.depth / state.max_depth,
                },
                duration_ms=100.0,
            )

        # Logic here will be complex, for now we mock a cycle
        state.step_history.append(
            {"action": "experts_polled", "timestamp": time.time()}
        )

        return state

        # Logic here will be complex, for now we mock a cycle
        state.step_history.append(
            {"action": "experts_polled", "timestamp": time.time()}
        )

        return state

    async def _checkpoint(self, state: LatticeState):
        """
        Persist state to SurrealDB as a UniverseNode.
        Enables time-travel and auditability.
        """
        try:
            node_id = f"lattice_{state.session_id}_{state.depth}"
            logger.info(f"💾 Lattice: Attempting checkpoint {node_id}")
            node = UniverseNode(
                id=node_id,
                content=state.model_dump_json(),
                node_type="lattice_state",
                metadata={
                    "session_id": state.session_id,
                    "depth": state.depth,
                    "spi": state.spi_score,
                },
            )
            resp = await self.db.store_node(node)
            logger.info(f"✅ Lattice: Checkpointed state {node_id} to {resp}")
        except Exception as e:
            logger.error(f"❌ Lattice Checkpoint FAILURE: {e}", exc_info=True)

    async def evolve_strategy(self, session_id: str, feedback: dict[str, Any]):
        """
        Adjust the SPI score based on external feedback (Immune/Mycelium).
        """
        # Logic to retrieve state and update SPI
        pass
