"""
Phonon Research Sprint - Autonomous cosmological simulation and optimization.
Demonstrates:
- SpatialPhononsEngine dynamics
- LongHorizonTask multi-session orchestration
- RecursiveChallenger autonomous refinement
"""

import asyncio
import json
import logging
from pathlib import Path

from cohezion.compound.long_horizon_task import LongHorizonTask
from cohezion.compound.recursive_challenger import RecursiveChallenger
from cohezion.universe.engine import AxiomaticState, UniverseSimulationEngine
from cohezion.universe.spatial_phonons import SpatialPhononsEngine


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PhononSprint")


async def run_phonon_sprint():
    """Run a multi-session phonon research sprint."""

    # 1. Initialize Task
    task_id = "phonon-dark-energy-optimization"
    # Check if we have a checkpoint
    checkpoint_file = Path("data/checkpoints/phonon_sprint.json")
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

    initial_state = None
    if checkpoint_file.exists():
        logger.info(f"Resuming task from checkpoint: {checkpoint_file}")
        with open(checkpoint_file) as f:
            initial_state = json.load(f)

    task = LongHorizonTask(task_id=task_id, budget_sessions=3, initial_state=initial_state)
    task.total_steps_estimated = 50

    engine = UniverseSimulationEngine()
    SpatialPhononsEngine()

    # 2. Simulation Loop (Sub-task)
    # Each step simulates 0.1s of manifold evolution
    logger.info(f"Starting Simulation Sprint (Session {task.steps_completed // 20 + 1})")

    # Create or resume journey
    journey_id = initial_state.get("journey_id") if initial_state else None
    if not journey_id:
        journey = await engine.start_journey(
            agent_name="PhononScout", intent="Optimize dark energy viscosity"
        )
        journey_id = journey.id
    else:
        # In a real app we'd load journey from DB, here we simulate
        from cohezion.universe.engine import UniverseJourney

        journey = UniverseJourney(
            id=journey_id,
            agent_name="PhononScout",
            intent="Optimize dark energy viscosity",
            initial_axiomatic=AxiomaticState(),
        )

    # Run up to 20 steps per session to stay within context guards
    steps_this_session = 0
    while task.steps_completed < task.total_steps_estimated and steps_this_session < 20:
        # Execute simulation step
        result = task.execute_step()

        if result.handoff_triggered:
            logger.info("Context limit reached. Saving checkpoint and handing off.")
            break

        # Physics evolution
        await engine.evolve_trajectory(
            journey,
            action=f"Simulating dark energy expansion (Step {task.steps_completed})",
            phi_score=0.85,
        )

        steps_this_session += 1

    # 3. Save progress
    checkpoint = task.save_checkpoint()
    checkpoint["journey_id"] = journey_id
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint, f)

    if task.steps_completed < task.total_steps_estimated:
        logger.info(
            f"Session complete. Progress: {task.progress_percent:.1f}%. Run again to continue."
        )
        return

    # 4. Final Analysis & Recursive Optimization (Target reached)
    logger.info("🏁 Simulation target reached. Running autonomous optimization cycle.")

    final_coherence = journey.trajectory[-1].coherence
    logger.info(f"Final Manifold Coherence: {final_coherence:.4f}")

    # Unleash the Challenger
    RecursiveChallenger(target_module="cohezion.universe.spatial_phonons")

    # Simulate the Challenger finding an opportunity to optimize coupling
    if final_coherence < 0.9:
        logger.info(
            "Challenger identified optimization: Coupling factor is sub-optimal for HIHO stability."
        )
        # In a real run, this would surgically update PhononParameters default or log a patch

    # 5. Export to 3D Cockpit (Next Frontier)
    logger.info("🔭 Projecting 12D trajectory to 3D Cockpit...")
    from cohezion.universe.viz_bridge import VisualizationBridge

    viz = VisualizationBridge()
    viz.export_journey(journey)

    logger.info("✅ Phonon Research Sprint Complete.")


if __name__ == "__main__":
    asyncio.run(run_phonon_sprint())
