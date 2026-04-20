#!/usr/bin/env python3
"""
Hourly Job: Autonomic Merger
Closes the loop between skill refinement proposals and the codebase.
"""

import asyncio
import logging
import subprocess
from pathlib import Path


PROJECT_ROOT = Path("/home/mike-anderson/dev/cohezion")
PATCH_DIR = PROJECT_ROOT / "src/cohezion/skills/patches"
SKILLS_DIR = PROJECT_ROOT / "src/cohezion/skills"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AutonomicMerger")


def run_command(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        logger.error(f"Command failed: {cmd}\nError: {result.stderr}")
    return result


async def main():
    logger.info("🤖 Starting Autonomic Merger...")

    # 1. Sense: Check for new patches
    patches = sorted(PATCH_DIR.glob("refinement_*.md"))
    if not patches:
        logger.info("No patches to merge.")
        return

    for patch_file in patches:
        # 2. Extract: Identify target skill (Simplification: assuming one patch per file)
        # In production, we'd use LLM to identify the target from the patch content.
        target_skill = SKILLS_DIR / "DEPENDENCY_AUTOMATION_PRIME.md"

        # 3. Apply: Surgical commit
        branch_name = f"autonomic-evolution/{patch_file.stem}"
        logger.info(f"Creating branch {branch_name}...")

        run_command(f"git checkout -b {branch_name}", cwd=PROJECT_ROOT)

        # Manifest: Overwrite skill with refined content
        # Note: In production, this would be a surgical replace, not a full overwrite.
        with open(target_skill, "w") as f:
            f.write(patch_file.read_text())

        # 4. Validate: Run Ruff/Lint
        logger.info("Validating refinement...")
        lint_result = run_command(f"ruff check {target_skill}", cwd=PROJECT_ROOT)

        if lint_result.returncode == 0:
            logger.info("✅ Refinement valid. Committing...")
            run_command(f"git add {target_skill}", cwd=PROJECT_ROOT)
            run_command(
                f"git commit -m 'Autonomic refinement: {patch_file.name}'", cwd=PROJECT_ROOT
            )
            # In production: run_command(f"git push origin {branch_name}")
            # Then: gh pr create ...
        else:
            logger.error("❌ Refinement invalid. Reverting...")
            run_command("git checkout main", cwd=PROJECT_ROOT)
            run_command(f"git branch -D {branch_name}", cwd=PROJECT_ROOT)
            patch_file.rename(patch_file.with_suffix(".invalid"))

        # Cleanup
        run_command("git checkout main", cwd=PROJECT_ROOT)
        if patch_file.exists():
            patch_file.unlink()


if __name__ == "__main__":
    asyncio.run(main())
