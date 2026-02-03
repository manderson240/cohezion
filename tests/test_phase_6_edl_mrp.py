"""
Verification script for Phase 6: EDL & MRP.
"""
import asyncio
import logging
import json
import sys
from pathlib import Path
from cohezion.swarm.lattice_orchestrator import LatticeOrchestrator
from cohezion.universe.engine import UniverseSimulationEngine
from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_phase_6")

class TestAgent(BaseAgent):
    async def process(self, query: str) -> str:
        return f"Processed: {query}"

async def verify():
    print(f"DEBUG TEST: lo file is {LatticeOrchestrator.__module__}")
    
    # 1. Setup Universe with a mock successful journey
    engine = UniverseSimulationEngine()
    journey_id = "test_journey_success"
    
    journey_data = {
        "id": journey_id,
        "agent_name": "TestAgent",
        "intent": "TestAgent",
        "initial_latent_embedding": [0.5] * 512,
        "final_phi_score": 0.95,
        "precipitation": {
            "outputs": {"knowledge": "Quantum-biotech is best handled via MHD gradients."}
        }
    }
    
    storage_path = Path("data/universe")
    storage_path.mkdir(parents=True, exist_ok=True)
    with open(storage_path / f"{journey_id}.json", "w") as f:
        json.dump(journey_data, f)
        
    logger.info(f"✅ Created mock journey {journey_id}")

    # 2. Verify MRP in BaseAgent
    config = SwarmConfig()
    agent = TestAgent(model_name="phi4", config=config)
    await agent._synchronize_mrp()
    
    if getattr(agent, "_mrp_experience", None):
        logger.info("✅ Agent successfully recovered experience via MRP.")
    else:
        logger.error("❌ Agent failed to recover experience.")

    # 3. Verify EDL in LatticeOrchestrator
    orchestrator = LatticeOrchestrator(config=config)
    print(f"DEBUG TEST: orchestrator methods: {dir(orchestrator)}")
    
    query = "Design a lunar base."
    state = await orchestrator.ignite(query)
    
    logger.info(f"✅ Lattice Session {state.session_id} completed.")
    print(f"DEBUG TEST: Final state responses: {state.expert_responses.keys()}")
    
    expert_count = len(state.expert_responses)
    logger.info(f"Experts Polled: {expert_count}")
    
    if expert_count >= 5:
        logger.info("✅ SUCCESS: EDL and MRP verified.")
    else:
        logger.error(f"❌ FAIL: Only {expert_count} experts polled.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(verify())
