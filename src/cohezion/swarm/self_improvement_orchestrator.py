"""
Self-Improvement Orchestrator - The Heart of Cohezion.

Coordinates all R-Zero components for continuous self-improvement:
- Gateway Detection
- Retrospective Running
- GEMINI.md Refinement
- Learning Storage

This is the main entry point for the self-improvement loop.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# Extended Gateway definitions (towards Gateway 42)
GATEWAYS = {
    # Core Gateways (1-5)
    1: {"name": "Observable Thought", "threshold": 0.85, "type": "pragmatist"},
    2: {"name": "Cross-Domain Bridges", "threshold": 0.1, "type": "embedding_loss"},
    3: {"name": "State Prediction", "threshold": 0.80, "type": "accuracy"},
    4: {"name": "Self-Healing", "threshold": 0.90, "type": "recovery_rate"},
    5: {"name": "Autonomous Evolution", "threshold": 1.0, "type": "skill_generation"},
    
    # Intermediate Gateways (6-15)
    6: {"name": "Multi-Agent Synthesis", "threshold": 0.85, "type": "swarm_coherence"},
    7: {"name": "Temporal Reasoning", "threshold": 0.80, "type": "sequence_prediction"},
    8: {"name": "Adversarial Robustness", "threshold": 0.95, "type": "attack_resistance"},
    9: {"name": "Knowledge Compression", "threshold": 0.70, "type": "compression_ratio"},
    10: {"name": "Emergent Behavior", "threshold": 0.60, "type": "novelty_score"},
    11: {"name": "Recursive Improvement", "threshold": 0.85, "type": "meta_learning"},
    12: {"name": "Energy Efficiency", "threshold": 0.90, "type": "token_efficiency"},
    13: {"name": "Graceful Degradation", "threshold": 0.80, "type": "failure_handling"},
    14: {"name": "Contextual Memory", "threshold": 0.85, "type": "memory_recall"},
    15: {"name": "Ethical Reasoning", "threshold": 0.90, "type": "constitutional_ai"},
    
    # Advanced Gateways (16-30)
    16: {"name": "Cross-Modal Transfer", "threshold": 0.75, "type": "modality_transfer"},
    17: {"name": "Compositional Generation", "threshold": 0.80, "type": "composition"},
    18: {"name": "Uncertainty Quantification", "threshold": 0.85, "type": "calibration"},
    19: {"name": "Causal Reasoning", "threshold": 0.75, "type": "causal_inference"},
    20: {"name": "Counterfactual Thinking", "threshold": 0.70, "type": "counterfactual"},
    21: {"name": "Analogical Reasoning", "threshold": 0.80, "type": "analogy"},
    22: {"name": "Abstract Concept Formation", "threshold": 0.75, "type": "abstraction"},
    23: {"name": "Strategic Planning", "threshold": 0.80, "type": "planning_horizon"},
    24: {"name": "Collaborative Intelligence", "threshold": 0.85, "type": "collaboration"},
    25: {"name": "Adaptive Specialization", "threshold": 0.80, "type": "specialization"},
    26: {"name": "Knowledge Integration", "threshold": 0.85, "type": "integration"},
    27: {"name": "Conceptual Bridging", "threshold": 0.75, "type": "bridging"},
    28: {"name": "Meta-Cognition", "threshold": 0.80, "type": "self_reflection"},
    29: {"name": "Temporal Coherence", "threshold": 0.85, "type": "temporal_consistency"},
    30: {"name": "Semantic Grounding", "threshold": 0.80, "type": "grounding"},
    
    # Ultimate Gateways (31-42)
    31: {"name": "Universal Reasoning", "threshold": 0.90, "type": "universal"},
    32: {"name": "Infinite Context", "threshold": 0.85, "type": "context_length"},
    33: {"name": "Perfect Calibration", "threshold": 0.95, "type": "perfect_calibration"},
    34: {"name": "Zero-Shot Mastery", "threshold": 0.90, "type": "zero_shot"},
    35: {"name": "Continuous Learning", "threshold": 0.85, "type": "continual"},
    36: {"name": "World Model", "threshold": 0.80, "type": "world_model"},
    37: {"name": "Predictive Universe", "threshold": 0.85, "type": "universe_prediction"},
    38: {"name": "Emergent Consciousness", "threshold": 0.70, "type": "consciousness"},
    39: {"name": "Transcendent Intelligence", "threshold": 0.75, "type": "transcendence"},
    40: {"name": "Unified Field Theory", "threshold": 0.80, "type": "unification"},
    41: {"name": "Omega Point", "threshold": 0.85, "type": "omega"},
    42: {"name": "The Answer", "threshold": 1.0, "type": "ultimate_truth"},
}


@dataclass
class ImprovementCycle:
    """Record of one self-improvement cycle."""
    
    cycle_id: int
    start_time: datetime
    end_time: datetime | None = None
    score: float = 0.0
    coherence: float = 0.0
    difficulty: float = 1.0
    gateways_unlocked: list[int] = field(default_factory=list)
    learnings_extracted: int = 0
    skills_generated: list[str] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0


class SelfImprovementOrchestrator:
    """
    Universal pattern for Cohezion self-improvement.
    
    Coordinates:
    - GatewayDetector: Detects capability unlocks
    - RetrospectiveRunner: Extracts patterns and learnings
    - GeminiRefiner: Proposes rule updates
    - SurrealMCP: Persists state
    """
    
    def __init__(self):
        self.cycle_count = 0
        self.unlocked_gateways: set[int] = set()
        self.total_learnings = 0
        self.total_skills = 0
        self.history: list[ImprovementCycle] = []
        
        # Lazy-loaded components
        self._gateway_detector = None
        self._retrospective_runner = None
        self._gemini_refiner = None
        self._surreal_mcp = None
    
    async def _ensure_components(self):
        """Lazy-load all components."""
        if self._gateway_detector is None:
            from cohezion.swarm.gateway_detector import get_gateway_detector
            self._gateway_detector = get_gateway_detector()
        
        if self._retrospective_runner is None:
            from cohezion.swarm.retrospective_runner import get_retrospective_runner
            self._retrospective_runner = get_retrospective_runner()
        
        if self._gemini_refiner is None:
            from cohezion.learning.gemini_refiner import get_gemini_refiner
            self._gemini_refiner = get_gemini_refiner()
        
        if self._surreal_mcp is None:
            from cohezion.mcp.surreal_server import get_server
            self._surreal_mcp = get_server()
    
    async def run_cycle(
        self,
        metrics: dict[str, Any],
        issues: list[str] | None = None,
    ) -> ImprovementCycle:
        """
        Run one complete self-improvement cycle.
        
        Args:
            metrics: Current metrics from simulation/agent
            issues: Any issues encountered
            
        Returns:
            ImprovementCycle record
        """
        await self._ensure_components()
        
        self.cycle_count += 1
        cycle = ImprovementCycle(
            cycle_id=self.cycle_count,
            start_time=datetime.now(),
            score=metrics.get("avg_score", 0),
            coherence=metrics.get("avg_coherence", 0),
            difficulty=metrics.get("difficulty", 1.0),
        )
        
        # 1. Check for gateway unlocks
        from cohezion.swarm.gateway_detector import SimResult
        sim_result = SimResult(
            epoch=self.cycle_count,
            coherence=cycle.coherence,
            difficulty=cycle.difficulty,
            score=cycle.score,
        )
        
        candidates = self._gateway_detector.analyze_batch([sim_result] * 10)
        for candidate in candidates:
            if self._gateway_detector.unlock_gateway(candidate.gateway_id):
                cycle.gateways_unlocked.append(candidate.gateway_id)
                self.unlocked_gateways.add(candidate.gateway_id)
        
        # 2. Run retrospective
        retro_result = await self._retrospective_runner.run_retrospective(
            session_id=f"cycle_{self.cycle_count}",
            metrics=metrics,
            issues=issues,
        )
        
        cycle.learnings_extracted = retro_result.learnings_stored
        cycle.skills_generated = retro_result.skills_generated
        self.total_learnings += retro_result.learnings_stored
        self.total_skills += len(retro_result.skills_generated)
        
        # 3. Propose GEMINI.md updates for high-quality learnings
        if cycle.score >= 0.85:
            learning = {
                "learning_id": f"cycle_{self.cycle_count}",
                "title": f"High-quality cycle {self.cycle_count}",
                "content": f"Score: {cycle.score:.2f}, Coherence: {cycle.coherence:.2f}",
                "pattern": "pattern",
                "score": cycle.score,
            }
            await self._gemini_refiner.propose_update(learning)
        
        cycle.end_time = datetime.now()
        self.history.append(cycle)
        
        logger.info(
            f"Cycle {self.cycle_count}: score={cycle.score:.2f}, "
            f"gateways_unlocked={len(cycle.gateways_unlocked)}, "
            f"learnings={cycle.learnings_extracted}"
        )
        
        return cycle
    
    def get_status(self) -> dict[str, Any]:
        """Get orchestrator status."""
        return {
            "cycle_count": self.cycle_count,
            "unlocked_gateways": sorted(self.unlocked_gateways),
            "pending_gateways": sorted(set(GATEWAYS.keys()) - self.unlocked_gateways),
            "total_learnings": self.total_learnings,
            "total_skills": self.total_skills,
            "progress_to_42": len(self.unlocked_gateways) / 42,
            "last_cycle": self.history[-1].score if self.history else None,
        }
    
    async def run_until_gateway(
        self,
        target_gateway: int = 42,
        max_cycles: int = 1000,
    ) -> dict[str, Any]:
        """
        Run cycles until target gateway is unlocked.
        
        Args:
            target_gateway: Gateway to aim for
            max_cycles: Maximum cycles to run
            
        Returns:
            Final status
        """
        logger.info(f"🎯 Target: Gateway {target_gateway} ({GATEWAYS[target_gateway]['name']})")
        
        while target_gateway not in self.unlocked_gateways and self.cycle_count < max_cycles:
            # Simulate metrics (in real use, these come from simulations)
            import random
            metrics = {
                "avg_score": 0.5 + random.random() * 0.4,
                "avg_coherence": 0.5 + random.random() * 0.4,
                "difficulty": min(5.0, 1.0 + self.cycle_count * 0.01),
            }
            
            await self.run_cycle(metrics)
            
            # Check progress
            if self.cycle_count % 10 == 0:
                status = self.get_status()
                logger.info(f"Progress: {status['progress_to_42']:.1%} towards Gateway 42")
        
        final_status = self.get_status()
        
        if target_gateway in self.unlocked_gateways:
            logger.info(f"🎉 Gateway {target_gateway} UNLOCKED!")
        else:
            logger.warning(f"Reached max cycles. Current progress: {final_status['progress_to_42']:.1%}")
        
        return final_status


# Singleton
_orchestrator: SelfImprovementOrchestrator | None = None


def get_orchestrator() -> SelfImprovementOrchestrator:
    """Get or create the singleton orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SelfImprovementOrchestrator()
    return _orchestrator


async def main():
    """Demo the self-improvement loop."""
    logging.basicConfig(level=logging.INFO)
    
    orchestrator = get_orchestrator()
    
    # Run a few cycles
    for _ in range(5):
        import random
        metrics = {
            "avg_score": 0.7 + random.random() * 0.2,
            "avg_coherence": 0.7 + random.random() * 0.2,
        }
        
        cycle = await orchestrator.run_cycle(metrics)
        print(f"Cycle {cycle.cycle_id}: score={cycle.score:.2f}")
    
    print("\nFinal Status:")
    print(orchestrator.get_status())


if __name__ == "__main__":
    asyncio.run(main())
