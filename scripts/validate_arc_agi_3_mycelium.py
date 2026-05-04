"""Mycelium Harness for ARC-AGI-3 Agentic Validation.
Uses the Mycelium CoverageLoop to iteratively refine and verify
the agentic interaction logic.
"""

import asyncio

from cohezion.mycelium.loop import CoverageLoop
from cohezion.mycelium.scripter import ShadowScripter
from cohezion.swarm.compound_client import get_compound_client


async def run_mycelium_validation():
    print("Initializing Mycelium ARC-AGI-3 Validation Loop...")

    # 1. Setup Mycelium Components
    client = get_compound_client()
    scripter = ShadowScripter(client)
    loop = CoverageLoop(scripter, root_dir=".", test_output_dir="tests/mycelium")

    # 2. Target File for Validation
    target_file = "src/cohezion/swarm/agents/arc_agi_3_wrapper.py"

    # 3. Read Code Context
    with open(target_file) as f:
        code_context = f.read()

    # 4. Execute Iterative Synthesis Loop
    # This will generate tests, check coverage, and refine until target met
    print(f"Starting Mycelium Synthesis for {target_file}...")
    final_coverage = await loop.execute(
        file_path=target_file, code_context=code_context, target_coverage=90.0, max_iterations=2
    )

    print(f"Mycelium Validation Complete. Final Coverage: {final_coverage}%")


if __name__ == "__main__":
    asyncio.run(run_mycelium_validation())
