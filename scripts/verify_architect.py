import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__name__).parent / "src"))

from cohezion.swarm.agents.architect_agent import ArchitectAgent
from cohezion.swarm.swarm_types import SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("ArchitectVerification")

    config = SwarmConfig()
    architect = ArchitectAgent(config=config)

    # Complex multi-component request
    request = "Develop a high-performance image processing pipeline that uses Moondream for visual analysis and stores results in SurrealDB, accessible via a Marimo dashboard."

    print("\n--- Testing Compositional Decomposition ---")
    print(f"Request: {request}")

    # 1. Test raw decomposition
    tasks = await architect.decompose(request)
    print(f"\nDecomposed Tasks ({len(tasks)} found):")
    for task in tasks:
        print(f" - [{task.get('id')}] {task.get('title')} (Agent: {task.get('suggested_agent')})")
        if task.get("depends_on"):
            print(f"   Depends on: {task.get('depends_on')}")

    # 2. Test full report generation
    print("\n--- Final Architecture Report ---")
    report = await architect.process(request)
    print(report)

    # Simple validation: Check if tasks were found
    if tasks and len(tasks) >= 3:
        print(
            f"\n✅ PASS: Architect successfully decomposed complex request into {len(tasks)} tasks."
        )
    else:
        print(
            f"\n❌ FAIL: Architect failed to produce a valid task breakdown (Found: {len(tasks)})."
        )

    await architect.close()


if __name__ == "__main__":
    asyncio.run(main())
