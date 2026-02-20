import asyncio
import logging

from cohezion.swarm.agents.universe_sim_agent import (
    UniverseNode,
    UniverseSimulationAgent,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HypercubeTest")


async def test_hypercube():
    agent = UniverseSimulationAgent()
    agent.nodes = {}

    # 1. Setup Agent
    node = UniverseNode(id="traveler", type="Agent")
    # Force W coordinate to 0.0
    node.state_vector.values = [0.0] * 512
    agent.nodes["traveler"] = node

    logger.info(f"Initial W: {node.w_coordinate}")

    # 2. Force Drift to Ghost Mode
    node.drift_4d(1.5)
    logger.info(f"Drifted W: {node.w_coordinate}")

    # 3. Run Step
    await agent.run_physics_step()

    # 4. Verify Ghost Mode
    is_ghost = node.metadata.get("ghost_mode", False)
    if is_ghost:
        logger.info("✅ Agent entered Ghost Mode (Invisible).")
    else:
        logger.error("❌ Agent is still visible despite high W drift.")

    # 5. Return to Reality
    node.state_vector.values[3] = 0.0
    await agent.run_physics_step()

    is_ghost = node.metadata.get("ghost_mode", False)
    if not is_ghost:
        logger.info("✅ Agent returned to Reality.")
    else:
        logger.error("❌ Agent stuck in Ghost Mode.")


if __name__ == "__main__":
    asyncio.run(test_hypercube())
