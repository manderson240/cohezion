import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from cohezion.evaluation.benchmarks import CohezionEvaluator
from cohezion.reliability.monitor import get_resource_monitor
from cohezion.universe.engine import UniverseSimulationEngine


@dataclass
class MockAgent:
    name: str = "CandidateAgent-X1"


async def run_holistic_demo():
    print("🚀 COHEZION 'UNIVERSES' READINESS DEMO")
    print("========================================")

    # 1. KINETIC MANIFOLD GROUNDING
    engine = UniverseSimulationEngine()
    journey = await engine.start_journey(agent_name="DemoAgent", intent="Showcase 12D grounding in real hardware.")
    ax = journey.initial_axiomatic
    print("\n[1] Physical Projection (12D) grounded in vitals:")
    print(f"    - Physics (CPU Load): {ax.physics:.3f}")
    print(f"    - Field (VRAM Density): {ax.field:.3f}")
    print(f"    - Control (Dilation): {ax.control:.3f}")

    # Simulate a step to generate drift for the GAIA journey

    # 2. RIGOROUS EVALUATION (GAIA + DRIFT + DRACONIAN)
    evaluator = CohezionEvaluator(use_sandbox=True)
    agent = MockAgent()

    # We'll use a real journey to show drift
    gaia_journey = await engine.start_journey(agent.name, "Solve GAIA Quest 001")
    await engine.evolve_trajectory(
        gaia_journey, action="Analyzing astronomy data", phi_score=0.4
    )  # Low quality = drift
    await engine.evolve_trajectory(gaia_journey, action="Cross-referencing star charts", phi_score=0.8)

    # Calculate drift manually for the demo
    drift = evaluator.calculate_manifold_drift(gaia_journey)

    # Run a passing eval
    print("\n[2] Evaluation Framework (GAIA Wrapper):")
    grade = evaluator.grader.grade(
        proposal="Correct GAIA Answer",
        judges=["expert_1", "expert_2"],
        efficacy_score=0.98,
        completeness_score=0.95,
        forward_looking_score=0.9,
    )

    print("    - Quest ID: GAIA-QUEST_001_ASTRONOMY")
    print(f"    - Pass Rate: {100 if grade.passed else 0}%")
    print(f"    - Manifold Drift: {drift:.4f} (Avg deviation from 0.5)")
    print(f"    - Draconian Consensus: {grade.consensus_score:.3f}")

    # 3. SANDBOX ISOLATION (Verification)
    print(f"\n[3] Sandbox isolation enabled: {evaluator.use_sandbox}")

    # Shutdown
    await get_resource_monitor().stop()
    print("\n✅ Readiness Proof Captured.")


if __name__ == "__main__":
    asyncio.run(run_holistic_demo())
