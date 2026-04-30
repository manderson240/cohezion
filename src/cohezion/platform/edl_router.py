"""
Expert Domain Lattice routing for complex decisions.
Charter requirement: "All complex problems must route through five specialized streams"
"""

import asyncio
import json
from enum import StrEnum

from pydantic import BaseModel

from cohezion.platform.coherence_tracker import get_coherence_tracker
from cohezion.swarm.compound_client import get_compound_client


class ExpertStream(StrEnum):
    """Five expert streams per Charter."""

    ARCHITECT = "architect"  # Design decisions
    ENGINEER = "engineer"  # Physics/implementation
    BIOLOGIST = "biologist"  # Life/organic systems
    QUANTUM_HW = "quantum_hw"  # Hardware/physical layer
    QUANTUM_ALGO = "quantum_algo"  # Compute/algorithms


class StreamRecommendation(BaseModel):
    """Single expert stream's recommendation."""

    stream: ExpertStream
    recommendation: str
    confidence: float
    coherence: float  # This stream's coherence with proposal
    rationale: str


class EDLConsensus(BaseModel):
    """Consensus across expert streams."""

    decision: str
    coherence: float  # Average coherence across streams
    hiho_stable: bool  # Within 0.4-0.6
    consensus_strength: float  # 1.0 = perfect HIHO alignment
    stream_recommendations: list[StreamRecommendation]
    requires_human_review: bool
    reasoning: str


class ExpertDomainRouter:
    """Route complex decisions through Expert Domain Lattice."""

    def __init__(self):
        self.client = get_compound_client()
        self.coherence_tracker = get_coherence_tracker()

    async def route_decision(self, decision_type: str, context: str, proposal: str) -> EDLConsensus:
        """
        Route decision through appropriate expert streams.

        Decision types:
        - 'architecture': Architect + Engineer
        - 'security': Engineer + Quantum HW
        - 'performance': Engineer + Quantum Algo
        - 'integration': Architect + Engineer + Biologist
        - 'algorithm': Quantum Algo + Engineer
        """

        # Determine which streams to consult
        streams = self._select_streams(decision_type)

        # Consult each stream in parallel
        recommendations = await asyncio.gather(
            *[self._consult_stream(stream, context, proposal) for stream in streams]
        )

        # Stabilize consensus (Charter requirement: 0.5 coherence)
        consensus = self._stabilize_consensus(recommendations)

        return consensus

    def _select_streams(self, decision_type: str) -> list[ExpertStream]:
        """Select appropriate expert streams for decision type."""
        stream_map = {
            "architecture": [ExpertStream.ARCHITECT, ExpertStream.ENGINEER],
            "security": [ExpertStream.ENGINEER, ExpertStream.QUANTUM_HW],
            "performance": [ExpertStream.ENGINEER, ExpertStream.QUANTUM_ALGO],
            "integration": [
                ExpertStream.ARCHITECT,
                ExpertStream.ENGINEER,
                ExpertStream.BIOLOGIST,
            ],
            "algorithm": [ExpertStream.QUANTUM_ALGO, ExpertStream.ENGINEER],
            "hardware": [ExpertStream.QUANTUM_HW, ExpertStream.ENGINEER],
            "research": [ExpertStream.ARCHITECT, ExpertStream.BIOLOGIST],
        }

        return stream_map.get(decision_type, [ExpertStream.ARCHITECT])

    async def _consult_stream(
        self, stream: ExpertStream, context: str, proposal: str
    ) -> StreamRecommendation:
        """Consult a single expert stream."""

        # Construct prompt for expert stream
        prompt = f"""You are the {stream.value} expert in the Expert Domain Lattice.

Context: {context}

Proposal: {proposal}

Provide your expert recommendation:
1. Do you approve this proposal? (yes/no/conditional)
2. What is your confidence? (0-1)
3. What is your coherence assessment? (How well does this align with the system? 0-1)
4. Rationale for your recommendation

Respond in JSON format:
{{
  "approve": "yes|no|conditional",
  "recommendation": "your recommendation",
  "confidence": 0.0-1.0,
  "coherence": 0.0-1.0,
  "rationale": "your reasoning"
}}
"""

        # Query expert stream (using appropriate model)
        model = self._get_stream_model(stream)
        result = await self.client.execute(
            prompt=prompt,
            model=model,
            temperature=0.3,  # Lower for consistency
        )

        # Parse response
        try:
            response = json.loads(result["result"])
        except Exception:
            # Fallback if JSON parsing fails
            response = {
                "approve": "conditional",
                "recommendation": result["result"],
                "confidence": 0.5,
                "coherence": 0.5,
                "rationale": "Expert stream response",
            }

        return StreamRecommendation(
            stream=stream,
            recommendation=response["recommendation"],
            confidence=response["confidence"],
            coherence=response["coherence"],
            rationale=response["rationale"],
        )

    def _get_stream_model(self, stream: ExpertStream) -> str:
        """Get appropriate model for expert stream."""
        # Route to different models based on expertise
        model_map = {
            ExpertStream.ARCHITECT: "deepseek-r1:70b",  # Reasoning for design
            ExpertStream.ENGINEER: "qwen3-coder:30b",  # Code/implementation
            ExpertStream.BIOLOGIST: "deepseek-r1:70b",  # Complex systems
            ExpertStream.QUANTUM_HW: "qwen3-coder:30b",  # Hardware
            ExpertStream.QUANTUM_ALGO: "deepseek-r1:70b",  # Algorithms
        }
        return model_map.get(stream, "phi3:mini")

    def _stabilize_consensus(self, recommendations: list[StreamRecommendation]) -> EDLConsensus:
        """
        Stabilize consensus using 0.5 coherence rule.

        Charter: "Trajectories are stable when consensus reached
        across MDL, adhering to 0.5 Coherence Rule"
        """

        # Average coherence across streams
        avg_coherence = sum(r.coherence for r in recommendations) / len(recommendations)

        # HIHO stability check
        hiho_stable = 0.4 <= avg_coherence <= 0.6

        # Consensus strength (1.0 at perfect 0.5 HIHO)
        hiho_delta = abs(avg_coherence - 0.5)
        consensus_strength = max(0.0, 1.0 - (hiho_delta * 2))

        # Merge recommendations
        merged_decision = self._merge_recommendations(recommendations)

        # Requires human review if:
        # 1. Consensus strength < 0.7 (outside HIHO)
        # 2. Any stream has confidence < 0.5
        # 3. Any stream explicitly rejects
        requires_review = (
            consensus_strength < 0.7
            or any(r.confidence < 0.5 for r in recommendations)
            or any("no" in r.recommendation.lower() for r in recommendations)
        )

        # Generate reasoning
        reasoning = self._generate_consensus_reasoning(
            recommendations, avg_coherence, hiho_stable, consensus_strength
        )

        return EDLConsensus(
            decision=merged_decision,
            coherence=avg_coherence,
            hiho_stable=hiho_stable,
            consensus_strength=consensus_strength,
            stream_recommendations=recommendations,
            requires_human_review=requires_review,
            reasoning=reasoning,
        )

    def _merge_recommendations(self, recommendations: list[StreamRecommendation]) -> str:
        """Merge recommendations from multiple streams."""
        # Weighted by confidence
        weighted_recs = []
        for rec in recommendations:
            weighted_recs.append(f"{rec.stream.value} ({rec.confidence:.2f}): {rec.recommendation}")

        return "\n".join(weighted_recs)

    def _generate_consensus_reasoning(
        self,
        recommendations: list[StreamRecommendation],
        coherence: float,
        hiho_stable: bool,
        consensus_strength: float,
    ) -> str:
        """Generate human-readable consensus reasoning."""

        reasoning = "EDL Consensus Analysis:\n"
        reasoning += (
            f"- Coherence: {coherence:.3f} "
            f"({'HIHO Stable ✅' if hiho_stable else 'Outside HIHO ⚠️'})\n"
        )
        reasoning += f"- Consensus Strength: {consensus_strength:.3f}\n"
        reasoning += f"- Expert Streams Consulted: {len(recommendations)}\n\n"

        for rec in recommendations:
            reasoning += f"{rec.stream.value.upper()}:\n"
            reasoning += f"  Confidence: {rec.confidence:.2f}\n"
            reasoning += f"  Coherence: {rec.coherence:.2f}\n"
            reasoning += f"  Rationale: {rec.rationale}\n\n"

        return reasoning


# Singleton accessor
_edl_router = None


def get_edl_router() -> ExpertDomainRouter:
    """Get global EDL router instance."""
    global _edl_router
    if _edl_router is None:
        _edl_router = ExpertDomainRouter()
    return _edl_router


def reset_edl_router():
    """Reset global EDL router (for testing)."""
    global _edl_router
    _edl_router = None
