#!/usr/bin/env python3
"""
Hourly Job: Mycelium Test Generation
Closes the loop between skill refinement and verification.
"""

import asyncio
import logging

# Add src to path
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cohezion.swarm.compound_client import get_compound_client


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MyceliumTestGen")


async def main():
    logger.info("🍄 Starting Mycelium Test Generation...")

    # 1. Sense: Check for recent patches
    patch_dir = PROJECT_ROOT / "src/cohezion/skills/patches"
    patches = sorted(patch_dir.glob("refinement_*.md"))

    if not patches:
        logger.info("No new refinements to test.")
        return

    latest_patch = patches[-1].read_text()

    # 2. Distill: Delegate test synthesis to qwen2.5-coder
    client = get_compound_client()
    prompt = f"""
    You are an AUTONOMIC_EVOLUTION_PRIME specialist.
    A new skill refinement has been proposed:
    
    Refinement: {latest_patch}
    
    Instruction:
    - Generate a Python test case (pytest) that verifies the new guardrail.
    - Example: If the refinement adds a regex guard, write a test that tries to bypass it.
    - Return ONLY the code block.
    """

    test_code = await client.generate(prompt, task_type="coding")

    # 3. Manifest: Save to tests/autonomic/
    test_dir = PROJECT_ROOT / "tests/autonomic"
    test_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H")
    test_file = test_dir / f"test_refinement_{timestamp}.py"

    with open(test_file, "w") as f:
        f.write(test_code)

    logger.info(f"✅ Mycelium Test Generated: {test_file}")


if __name__ == "__main__":
    asyncio.run(main())
