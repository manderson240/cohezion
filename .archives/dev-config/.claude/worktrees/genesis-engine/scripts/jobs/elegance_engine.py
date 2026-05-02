#!/usr/bin/env python3
"""
Overnight Job: The Elegance Engine (Active Manifestation Edition)
Continuously identifies complex code, refactors it, validates via tests, and commits.
"""

import asyncio
import logging
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import trackio

from cohezion.swarm.compound_client import get_compound_client


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("EleganceManifest")


def run_command(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result


def get_complex_files():
    """Use ruff to find files with high cyclomatic complexity (C901)."""
    try:
        # Check src/cohezion
        result = run_command("ruff check src/cohezion --select C901 --format text", cwd=PROJECT_ROOT)
        files = set()
        for line in result.stdout.split("\n"):
            if "C901" in line and ":" in line:
                filepath = line.split(":")[0]
                if (PROJECT_ROOT / filepath).exists():
                    files.add(PROJECT_ROOT / filepath)
        return sorted(list(files))
    except Exception as e:
        logger.error(f"Error checking complexity: {e}")
        return []


async def manifest_elegance():
    logger.info("✨ Elegance Engine: ACTIVE MANIFESTATION phase started...")
    # Fix: Disable remote space_id to prevent interactive login in background
    trackio.init(project="cohezion-core")

    client = get_compound_client()
    proposals_dir = PROJECT_ROOT / "reports/elegance_manifestations"
    proposals_dir.mkdir(parents=True, exist_ok=True)

    end_time = time.time() + (8 * 3600)  # Run for 8 hours

    while time.time() < end_time:
        # Check system health before starting a cycle
        logger.info("Checking system vitals...")

        complex_files = get_complex_files()
        if not complex_files:
            logger.info("No complexity detected. System is elegant.")
            await asyncio.sleep(1800)
            continue

        target_file = complex_files[0]
        logger.info(f"Targeting: {target_file.relative_to(PROJECT_ROOT)}")

        code_content = target_file.read_text()
        if len(code_content) > 20000:  # Context guard
            logger.info("File too large for safe overnight refactor. Skipping.")
            await asyncio.sleep(300)
            continue

        prompt = f"""
        You are an ELEGANT_SIMPLICITY_PRIME specialist.
        REFACOR FOR MINIMALISM: {target_file.name}

        Current Code:
        ```python
        {code_content}
        ```

        Instruction:
        - Rewrite the logic to be "Elegantly Simple".
        - Focus on cyclomatic complexity reduction.
        - Output the COMPLETE refactored file content inside a single ```python ... ``` block.
        - Keep public signatures identical.
        """

        try:
            response = await client.generate(prompt, task_type="coding")

            # Extract code block
            match = re.search(r"```python\n(.*?)\n```", response, re.DOTALL)
            if not match:
                logger.warning("No code block found in response. Skipping.")
                continue

            new_code = match.group(1)

            # --- START MANIFESTATION BARRIER ---
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            branch_name = f"elegance/refactor-{target_file.stem}-{timestamp}"

            logger.info(f"Applying manifestation on branch {branch_name}...")

            # 1. Branch
            run_command(f"git checkout -b {branch_name}", cwd=PROJECT_ROOT)

            # 2. Apply
            original_code = target_file.read_text()
            target_file.write_text(new_code)

            # 3. Validate
            logger.info("Running validation (Lint + Fast Tests)...")
            lint = run_command(f"ruff check {target_file}", cwd=PROJECT_ROOT)
            # Run fast tests related to the file if possible, or just general fast tests
            test = run_command("uv run pytest -m fast --tb=short", cwd=PROJECT_ROOT)

            if lint.returncode == 0 and test.returncode == 0:
                logger.info("✅ VALIDATION PASSED. Committing manifestation.")
                run_command(f"git add {target_file}", cwd=PROJECT_ROOT)
                run_command(
                    f"git commit -m 'Elegance Manifestation: Refactored {target_file.name} for simplicity'",
                    cwd=PROJECT_ROOT,
                )
                trackio.log({"manifestations_success": 1})
            else:
                logger.error("❌ VALIDATION FAILED. Reverting changes.")
                target_file.write_text(original_code)
                run_command("git checkout main", cwd=PROJECT_ROOT)
                run_command(f"git branch -D {branch_name}", cwd=PROJECT_ROOT)
                trackio.log({"manifestations_failed": 1})

            # Always return to main
            run_command("git checkout main", cwd=PROJECT_ROOT)
            # --- END MANIFESTATION BARRIER ---

        except Exception as e:
            logger.error(f"Elegance cycle crashed: {e}")

        # Sleep 1 hour between manifestations to allow system to cool and avoid massive git drift
        logger.info("Manifestation cycle complete. Sleeping for 1 hour...")
        await asyncio.sleep(3600)

    logger.info("🌅 Overnight Elegance Manifestation complete.")
    trackio.finish()


if __name__ == "__main__":
    asyncio.run(manifest_elegance())
