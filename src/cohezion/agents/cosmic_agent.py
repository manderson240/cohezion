import logging

from cohezion.cosmic.plasma import get_plasma_filaments
from cohezion.cosmic.reality import get_reality_stabilizer
from cohezion.agents.biological_agent import BiologicalAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class CosmicAgent(BiologicalAgent):
    """
    Cosmic Agent (Phase 16).

    Gateway 27: Plasma Connectivity & HIHO Stability.

    Additions:
    - Plasma Filaments: Queries distant nodes via graph edges.
    - Reality Stabilizer: Enforces 0.5 Coherence on outputs.
    """

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(config=config)
        self.plasma = get_plasma_filaments()
        self.stabilizer = get_reality_stabilizer()

        # Connect to the cosmic graph
        self.plasma.establish_filament(self.id, "AnalystAgent", conductance=0.8)
        self.plasma.establish_filament(self.id, "MemoryAgent", conductance=0.6)

    async def process(self, query: str) -> str:
        """
        Process query with cosmic enhancements.
        """
        # 1. Biological/Quantum Processing
        # (Emits BioSignals, Checks Morphic Resonance, Braids Trajectories)
        response = await super().process(query)

        # 2. Plasma Connectivity Check
        # Simulate checking distant nodes for confirmation
        reached_nodes = self.plasma.conduct_impulse(self.id, "Query Impulse")

        # 3. HIHO Reality Stabilization
        # Encode final response to vector
        z_final = self.flume.get_semantic_vector(str(response))

        # Calculate stability
        stability = self.stabilizer.calculate_stability(z_final)

        # Stabilize if needed
        z_stabilized = self.stabilizer.stabilize(z_final)

        # Recalculate stability after correction
        new_stability = self.stabilizer.calculate_stability(z_stabilized)

        cosmic_report = "\n\n### 🌌 Cosmic Perspective Report\n"
        cosmic_report += f"**Plasma Connectivity**: {len(reached_nodes)} nodes reached ({', '.join(reached_nodes[:3])}...)\n"
        cosmic_report += f"**HIHO Stability**: {stability:.2f} -> {new_stability:.2f} (Target: 0.5)\n"

        if abs(stability - 0.5) > 0.1:
            if stability > 0.6:
                cosmic_report += (
                    "⚠️ **Reality Too Static**: Injected Chaos to restore flow.\n"
                )
            else:
                cosmic_report += (
                    "⚠️ **Reality Too Chaotic**: Injected Order to restore structure.\n"
                )
        else:
            cosmic_report += (
                "✅ **Reality Stable**: Perfect Half-In-Half-Out Equilibrium.\n"
            )

        # Use AgentResponse to wrap the final string and preserve metadata
        from cohezion.agents.base import AgentResponse

        return AgentResponse(
            response + cosmic_report,
            embedding=getattr(response, "embedding", None),
            persistence_id=getattr(response, "persistence_id", None),
            frequency=getattr(response, "frequency", 1),
            phi_score=getattr(response, "phi_score", 0.0),
            confidence=getattr(response, "confidence", 1.0),
            security_level=getattr(response, "security_level", "safe"),
            narration=getattr(response, "narration", None),
            alignment_score=getattr(response, "alignment_score", 1.0),
        )

    async def close(self):
        await super().close()
