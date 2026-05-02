#!/usr/bin/env python3
"""
Hourly Job: Autonomic Skill Refinement
Showcases SKILL: AUTONOMIC_EVOLUTION_PRIME
Delegate: qwen2.5-coder:7b (Synthesis)
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cohezion.swarm.compound_client import get_compound_client


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SkillRefiner")


async def main():
    logger.info("🧬 Starting Hourly Skill Refinement...")

    # 1. Sense: Check for recent bug hunt findings (Mocked for demonstration)
    bug_findings = {
        "vulnerability": "ReDoS in minimatch",
        "root_cause": "Exponential backtracking in nested quantifiers",
        "affected_skill": "DEPENDENCY_AUTOMATION_PRIME",
    }

    # 2. Distill: Delegate skill CURATION to qwen2.5-coder:7b
    client = get_compound_client()
    prompt = f"""
    You are an AUTONOMIC_EVOLUTION_PRIME specialist.
    Research (L137) shows that curated, concise skills perform +51.9pp better than generated ones.
    
    Finding: {bug_findings}
    
    Instruction:
    - Prune and refine 'src/cohezion/skills/DEPENDENCY_AUTOMATION_PRIME.md'.
    - DO NOT just add data. Remove ambiguity and redundant steps.
    - Add a single, sharp guardrail for 'nested quantifiers'.
    - Ensure the final skill is <150 lines.
    """

    response = await client.generate(prompt, task_type="coding")

    # 3. Manifest: Save patch proposal to a staging area
    patch_dir = Path("src/cohezion/skills/patches")
    patch_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H")
    patch_file = patch_dir / f"refinement_{timestamp}.md"

    with open(patch_file, "w") as f:
        f.write(response)

    logger.info(f"✅ Skill refinement proposal generated: {patch_file}")


if __name__ == "__main__":
    asyncio.run(main())
