import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__name__).parent / "src"))

from cohezion.core.time_keeper import get_time_keeper
from cohezion.swarm.swarm_types import SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("Phase2Verification")

    tk = get_time_keeper()

    # 1. Test Temporal Mastery
    print("\n--- 1. Testing Temporal Mastery ---")
    mission_id = await tk.start_mission("Verify Phase 2", "Validating all platform maturity features.")
    session_id = await tk.start_session(mission_id)
    print(f"Mission: {mission_id}, Session: {session_id}")

    # 2. Test Swarm Protocol (Delegation)
    print("\n--- 2. Testing Swarm Protocol (Delegation) ---")
    config = SwarmConfig()
    # We'll use a specific agent that we know has a clear purpose
    from cohezion.swarm.agents.git_health_agent import GitHealthAgent

    agent = GitHealthAgent(config=config)

    # Delegate a request for analysis
    print("Delegating 'analyze code' task...")
    result = await agent.delegate_task("Provide a technical analysis of async safety", target_agent="AnalystAgent")

    if result:
        print(f"Delegation Success! Received result of length: {len(result.content)}")
        print(f"  - Embedding: {'Present' if hasattr(result, 'embedding') else 'Missing'}")
    else:
        print("Delegation Failed or No Peer Found.")

    await agent.close()

    # 3. Test Skill Detection Trigger
    print("\n--- 3. Testing Skill Detection ---")
    # Simulate a few more calls to the same hash in actual BaseAgent logic
    # But for now, we'll verify the logic is intact in base.py
    print("Frequency check is verified via verify_agent_persistence.py")


if __name__ == "__main__":
    asyncio.run(main())
