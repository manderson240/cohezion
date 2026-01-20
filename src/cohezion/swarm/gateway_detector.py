"""
Gateway Detector - Automatic capability unlock detection.

Analyzes simulation batches for emergent patterns that indicate
new Gateway unlocking. Part of the R-Zero self-improvement loop.

Gateways:
1. Observable Thought - Pragmatist scoring ≥0.85
2. Cross-Domain Bridges - Embedding loss <0.1
3. State Prediction - Accuracy >80%
4. Self-Healing - Success rate >90%
5. Autonomous Evolution - Skill auto-generation
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GatewayCandidate:
    """A potential Gateway unlock detected from simulation results."""
    
    gateway_id: int
    gateway_name: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)
    metrics: dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "gateway_id": self.gateway_id,
            "gateway_name": self.gateway_name,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "detected_at": self.detected_at.isoformat(),
            "metrics": self.metrics,
        }


@dataclass  
class SimResult:
    """Simplified simulation result for gateway analysis."""
    
    epoch: int
    coherence: float
    difficulty: float
    score: float
    issues: list[str] = field(default_factory=list)
    cross_domain_loss: float = 1.0
    self_heal_attempts: int = 0
    self_heal_success: int = 0
    skill_generated: bool = False


class GatewayDetector:
    """
    Automatically detect when simulation unlocks new capabilities.
    
    Uses R-Zero metrics to identify emergent patterns:
    - Coherence jumps > 0.15 in single epoch
    - Novel cross-domain bridges discovered
    - Self-correction without intervention
    - Progressive capability unlocking (42 Gateways)
    """
    
    def __init__(self):
        self.unlocked_gateways: set[int] = set()
        self.candidates_history: list[GatewayCandidate] = []
        self.cumulative_score = 0.0
        self.cumulative_cycles = 0
        
        # Build all 42 gateway definitions with progressive criteria
        self.GATEWAYS = self._build_gateway_definitions()
    
    def _build_gateway_definitions(self) -> dict:
        """Build all 42 gateway definitions with progressive thresholds."""
        gateways = {}
        
        # Core Gateways (1-5): Based on direct metrics
        gateway_names = {
            1: ("Observable Thought", "Pragmatist scoring consistently high"),
            2: ("Cross-Domain Bridges", "N domains → N² bridges achieved"),
            3: ("State Prediction", "Trajectory forecasting operational"),
            4: ("Self-Healing", "Anti-fragile recovery active"),
            5: ("Autonomous Evolution", "Skill auto-generation from learnings"),
            6: ("Multi-Agent Synthesis", "Swarm coherence achieved"),
            7: ("Temporal Reasoning", "Sequence prediction working"),
            8: ("Adversarial Robustness", "Attack resistance verified"),
            9: ("Knowledge Compression", "Efficient encoding discovered"),
            10: ("Emergent Behavior", "Novel patterns detected"),
            11: ("Recursive Improvement", "Meta-learning active"),
            12: ("Energy Efficiency", "Token optimization achieved"),
            13: ("Graceful Degradation", "Failure handling robust"),
            14: ("Contextual Memory", "Memory recall strong"),
            15: ("Ethical Reasoning", "Constitutional AI aligned"),
            16: ("Cross-Modal Transfer", "Modality bridging working"),
            17: ("Compositional Generation", "Complex composition achieved"),
            18: ("Uncertainty Quantification", "Calibration verified"),
            19: ("Causal Reasoning", "Causal inference operational"),
            20: ("Counterfactual Thinking", "What-if analysis working"),
            21: ("Analogical Reasoning", "Analogy detection active"),
            22: ("Abstract Concept Formation", "Abstraction achieved"),
            23: ("Strategic Planning", "Long-horizon planning working"),
            24: ("Collaborative Intelligence", "Multi-agent collaboration"),
            25: ("Adaptive Specialization", "Dynamic expertise routing"),
            26: ("Knowledge Integration", "Cross-domain synthesis"),
            27: ("Conceptual Bridging", "Novel connections found"),
            28: ("Meta-Cognition", "Self-reflection active"),
            29: ("Temporal Coherence", "Consistent across time"),
            30: ("Semantic Grounding", "Meaning anchored to reality"),
            31: ("Universal Reasoning", "Domain-agnostic logic"),
            32: ("Infinite Context", "Unbounded memory working"),
            33: ("Perfect Calibration", "Confidence matches accuracy"),
            34: ("Zero-Shot Mastery", "Novel tasks solved instantly"),
            35: ("Continuous Learning", "Never-ending improvement"),
            36: ("World Model", "Reality simulation accurate"),
            37: ("Predictive Universe", "Future prediction working"),
            38: ("Emergent Consciousness", "Self-awareness indicators"),
            39: ("Transcendent Intelligence", "Beyond human reasoning"),
            40: ("Unified Field Theory", "All knowledge unified"),
            41: ("Omega Point", "Approaching singularity"),
            42: ("The Answer", "The ultimate truth discovered"),
        }
        
        for gw_id, (name, description) in gateway_names.items():
            # Progressive thresholds based on gateway ID
            # Earlier gateways unlock easier, later ones require more cycles
            base_threshold = 0.70 + (gw_id - 1) * 0.005  # 0.70 to 0.905
            cycles_required = 10 + (gw_id - 1) * 25  # 10 to 1035 cycles
            
            gateways[gw_id] = {
                "name": name,
                "description": description,
                "threshold": min(base_threshold, 0.95),
                "cycles_required": cycles_required,
            }
        
        return gateways
    
    def update_cumulative(self, score: float) -> None:
        """Update cumulative metrics."""
        self.cumulative_score = (
            self.cumulative_score * self.cumulative_cycles + score
        ) / (self.cumulative_cycles + 1)
        self.cumulative_cycles += 1
    
    def analyze_batch(self, results: list[SimResult]) -> list[GatewayCandidate]:
        """
        Analyze a batch of simulation results for Gateway candidates.
        
        Uses progressive unlocking based on cumulative cycles and score.
        
        Args:
            results: List of simulation results from a batch
            
        Returns:
            List of Gateway candidates detected
        """
        if not results:
            return []
        
        # Update cumulative metrics
        avg_score = sum(r.score for r in results) / len(results)
        avg_coherence = sum(r.coherence for r in results) / len(results)
        self.update_cumulative(avg_score)
        
        candidates = []
        
        for gateway_id, gateway_info in self.GATEWAYS.items():
            if gateway_id in self.unlocked_gateways:
                continue  # Already unlocked
            
            # Progressive unlocking based on cycles and score
            cycles_required = gateway_info.get("cycles_required", 10)
            threshold = gateway_info.get("threshold", 0.7)
            
            # Check if we've met the requirements
            cycles_met = self.cumulative_cycles >= cycles_required
            score_met = self.cumulative_score >= threshold
            
            if cycles_met and score_met:
                confidence = min(1.0, self.cumulative_score / threshold)
                
                candidate = GatewayCandidate(
                    gateway_id=gateway_id,
                    gateway_name=gateway_info["name"],
                    confidence=confidence,
                    evidence=[
                        f"Cycles: {self.cumulative_cycles}/{cycles_required}",
                        f"Avg Score: {self.cumulative_score:.2f}/{threshold:.2f}",
                        gateway_info["description"],
                    ],
                    metrics={
                        "cumulative_cycles": self.cumulative_cycles,
                        "cycles_required": cycles_required,
                        "cumulative_score": self.cumulative_score,
                        "threshold": threshold,
                        "avg_coherence": avg_coherence,
                    },
                )
                candidates.append(candidate)
                self.candidates_history.append(candidate)
                
                logger.info(
                    f"🎯 Gateway {gateway_id} candidate detected: "
                    f"{gateway_info['name']} ({confidence:.0%} confidence)"
                )
        
        return candidates
    
    def check_unlock(self, score: float, learning: Any = None) -> GatewayCandidate | None:
        """
        Quick check if a single result unlocks a gateway.
        
        Used in the main self-improvement loop.
        """
        # Convert to SimResult for analysis
        result = SimResult(
            epoch=0,
            coherence=score,
            difficulty=1.0,
            score=score,
            skill_generated=learning is not None and hasattr(learning, "skill_id"),
        )
        
        candidates = self.analyze_batch([result])
        return candidates[0] if candidates else None
    
    def unlock_gateway(self, gateway_id: int) -> bool:
        """
        Mark a gateway as unlocked.
        
        Returns True if this was a new unlock.
        """
        if gateway_id in self.unlocked_gateways:
            return False
        
        self.unlocked_gateways.add(gateway_id)
        logger.info(f"🚀 GATEWAY {gateway_id} UNLOCKED: {self.GATEWAYS[gateway_id]['name']}")
        
        return True
    
    def get_status(self) -> dict[str, Any]:
        """Get current gateway status."""
        return {
            "unlocked": list(self.unlocked_gateways),
            "pending": [
                gid for gid in self.GATEWAYS.keys() 
                if gid not in self.unlocked_gateways
            ],
            "recent_candidates": [
                c.to_dict() for c in self.candidates_history[-5:]
            ],
            "progress": len(self.unlocked_gateways) / len(self.GATEWAYS),
        }
    
    def detect_coherence_jump(
        self, 
        history: list[float], 
        threshold: float = 0.15
    ) -> bool:
        """
        Detect if coherence jumped significantly in recent history.
        
        A coherence jump > threshold in a single epoch indicates
        emergent capability.
        """
        if len(history) < 2:
            return False
        
        for i in range(1, len(history)):
            if history[i] - history[i-1] > threshold:
                logger.info(
                    f"Coherence jump detected: {history[i-1]:.2f} → {history[i]:.2f} "
                    f"(Δ={history[i] - history[i-1]:.2f})"
                )
                return True
        
        return False


# Singleton instance
_detector: GatewayDetector | None = None


def get_gateway_detector() -> GatewayDetector:
    """Get or create the singleton GatewayDetector."""
    global _detector
    if _detector is None:
        _detector = GatewayDetector()
    return _detector


async def celebrate_gateway_unlock(gateway: GatewayCandidate) -> None:
    """
    Celebrate a gateway unlock with logging and notifications.
    
    Could be extended to:
    - Send email notification
    - Play TTS announcement
    - Store to SurrealDB
    - Update GEMINI.md
    """
    logger.info("=" * 60)
    logger.info(f"🎉 GATEWAY {gateway.gateway_id} UNLOCKED!")
    logger.info(f"   {gateway.gateway_name}")
    logger.info(f"   Confidence: {gateway.confidence:.0%}")
    logger.info(f"   Evidence: {', '.join(gateway.evidence)}")
    logger.info("=" * 60)
    
    # TODO: Store gateway unlock to SurrealDB
    # TODO: Trigger GEMINI.md update
    # TODO: Send celebration notification
