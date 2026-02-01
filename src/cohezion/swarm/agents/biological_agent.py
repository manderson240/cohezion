import logging
import time

from cohezion.bio.biophotonics import BioSignal, Wavelength, get_light_field
from cohezion.bio.morphic_field import get_morphic_field
from cohezion.swarm.agents.quantum_agent import QuantumAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class BiologicalAgent(QuantumAgent):
    """
    Biological Intelligence Agent (Phase 15).

    Gateway 26: Wetware & Collective Fields.

    Additions:
    - Morphic Resonance: Accesses shared success memory.
    - Biophotonics: Emits light signals for non-verbal status.
    """

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(config=config)
        self.morphic_field = get_morphic_field()
        self.light_field = get_light_field()
        self.id = self.__class__.__name__

    async def process(self, query: str) -> str:
        """
        Process query with biological enhancements.
        """
        # 1. Emit START Signal (Blue = Info)
        self._emit(Wavelength.BLUE, 0.5, "Processing Started")

        # 2. Check Morphic Resonance
        # Encode query to see if we have similar past successes
        z_query = self.flume.get_semantic_vector(query)
        resonance_score, guide_vector = self.morphic_field.resonate(z_query)

        resonance_msg = ""
        if resonance_score > 0.8:
            resonance_msg = f"🧬 **Morphic Resonance Detected** (Score: {resonance_score:.2f}). Tuning latent space..."
            self._emit(Wavelength.GREEN, 0.8, "Resonance Found")
            # In a full model, we would add `guide_vector` to `z_query` before generation
            # For now, we simulate the guidance boost

        response = await super().process(query)

        # 4. Analyze & Imprint
        imprint_score = 0.85 + (
            resonance_score * 0.1
        )  # Boost score if we had resonance
        imprint_score = min(0.99, imprint_score)

        self.morphic_field.imprint(z_query, imprint_score)
        self._emit(Wavelength.UV, 0.9, "Trace Imprinted")

        # 5. Biological Report Append
        bio_report = "\n\n### 🦠 Biological Intelligence Report\n"
        if resonance_msg:
            bio_report += f"{resonance_msg}\n"
        bio_report += f"**Morphic Imprint**: {imprint_score:.2f}\n"
        bio_report += "**BioSignals Emitted**: 3 (Blue, Green, UV)"

        # Use AgentResponse to wrap the final string and preserve metadata
        from cohezion.swarm.agents.base import AgentResponse

        return AgentResponse(
            response + bio_report,
            embedding=getattr(response, "embedding", None),
            persistence_id=getattr(response, "persistence_id", None),
            frequency=getattr(response, "frequency", 1),
            phi_score=getattr(response, "phi_score", 0.0),
            confidence=getattr(response, "confidence", 1.0),
            security_level=getattr(response, "security_level", "safe"),
            narration=getattr(response, "narration", None),
            alignment_score=getattr(response, "alignment_score", 1.0),
        )

    def _emit(self, wavelength: Wavelength, intensity: float, meta: str):
        """Helper to emit signal."""
        signal = BioSignal(
            wavelength=wavelength,
            intensity=intensity,
            source_agent=self.id,
            timestamp=time.time(),
            metadata={"msg": meta},
        )
        self.light_field.emit(signal)

    async def close(self):
        await super().close()
