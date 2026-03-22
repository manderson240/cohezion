import asyncio
import logging
import sys
from pathlib import Path

from cohezion.swarm.agents.introspect_agent import IntrospectAgent
from cohezion.swarm.swarm_types import SwarmConfig


# Add src to path
sys.path.append(str(Path.cwd() / "src"))


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("IntrospectVerify")

    config = SwarmConfig()
    agent = IntrospectAgent(config=config)

    print("\n--- 🧘 Test 1: Baseline Meditation ---")
    response_1 = await agent.process("Contemplate the void.")
    if "Daily Reflection" in response_1:
        print("✅ PASS: Reflection Generated.")
    else:
        print("❌ FAIL: No Reflection.")

    print("\n--- ⚠️ Test 2: Karmic Disturbance (TODO Bomb) ---")
    # PLANT A BOMB (of TODOs)
    bomb_path = Path("src/cohezion/todo_bomb.py")
    bomb_path.write_text("\n".join(["# TODO: Fix me"] * 60))

    try:
        response_2 = await agent.process("Scan the horizon.")
        print(response_2[-400:])

        if "Disturbance Detected" in response_2:
            print("✅ PASS: High Debt Detected.")
        else:
            print("❌ FAIL: Debt Missed.")

        # Check if artifact was written
        if Path("daily_reflection.md").exists():
            print("✅ PASS: Daily Reflection Artifact Written.")
        else:
            print("❌ FAIL: Artifact missing.")

    finally:
        # Cleanup
        if bomb_path.exists():
            bomb_path.unlink()

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
