import asyncio
import logging

from cohezion.swarm.agents.universe_sim_agent import UniverseSimulationAgent

from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.core.persistence.surreal_client import UniverseNode as DBNode


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HealingTest")


async def test_healing():
    # 1. Setup
    agent = UniverseSimulationAgent()
    agent.initialize_cosmos(galaxies=1, systems_per_galaxy=1, agents_per_system=2)

    # Force High Entropy
    for node in agent.nodes.values():
        if node.type == "Agent":
            node.entropy = 0.9

    logger.info(f"Initial Entropy: {agent.nodes['AGENT_0_0_0'].entropy}")

    # 2. Simulate "Nexus" Completing a Mission
    # We manually inject a COMPLETED mission because running the real Daemon is too slow for a unit test
    db = SurrealClient()
    cure_node = DBNode(
        id="mission_test_cure",
        node_type="mission",
        content="Solution found.",
        metadata={"topic": "Test Cure", "status": "COMPLETED", "applied": False},
    )
    await db.store_node(cure_node)
    logger.info("💉 Injected CURE into DB.")

    # 3. Run Sim Step
    # It should:
    # a) Detect High Entropy (Trigger Request - we ignore this for now)
    # b) Detect CURE (Apply Stabilization)
    await agent.run_physics_step()

    # 4. Check Results
    final_entropy = agent.nodes["AGENT_0_0_0"].entropy
    logger.info(f"Final Entropy: {final_entropy}")

    if final_entropy < 0.5:
        logger.info("✅ System Healed Successfully!")
    else:
        logger.error("❌ System did not heal.")


if __name__ == "__main__":
    asyncio.run(test_healing())
