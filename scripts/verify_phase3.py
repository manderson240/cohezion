import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__name__).parent / "src"))

from cohezion.core.time_keeper import get_time_keeper
from cohezion.swarm.agents.chronicle_agent import ChronicleAgent
from cohezion.swarm.agents.healer_agent import HealerAgent
from cohezion.swarm.swarm_types import SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("Phase3Verification")

    tk = get_time_keeper()
    config = SwarmConfig()

    # 1. Mission Start
    mission_id = await tk.start_mission("Phase 3 Integration", "Testing Healing and Synthesis.")
    await tk.start_session(mission_id)

    # 2. Test Quality Rubrics (phi_score)
    print("\n--- 1. Testing Native Quality Rubrics ---")
    healer = HealerAgent(config=config)
    # This will trigger call_ollama which now does self-evaluation
    response = await healer._call_ollama("Test prompt for phi-score evaluation.")
    print(f"Response Phi-Score: {getattr(response, 'phi_score', 'Missing')}")

    # 3. Test Sandbox Healing
    print("\n--- 2. Testing Sandbox Healing ---")
    # Mock an audit report finding
    report = "Audit Finding: Blocking call at `src/cohezion/core/time_keeper.py:1`"
    # Actually, we'll point it at a safer test file if needed, but for now we'll see if it extracts
    result = await healer.process(report)
    print(result)

    # 4. Test Chronicle Synthesis
    print("\n--- 3. Testing Chronicle Synthesis ---")
    chronicle = ChronicleAgent(config=config)
    summary = await chronicle.process(mission_id)
    print(summary)

    await healer.close()
    await chronicle.close()


if __name__ == "__main__":
    asyncio.run(main())
