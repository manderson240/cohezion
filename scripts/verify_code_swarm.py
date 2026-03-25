"""
Verification Script - Runs the Code Review Swarm on a subset of files.
Verifies Safe Mode (sequential calls, cooldowns, resource guarding).
"""

import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from cohezion.core.persistence.repositories.pattern_repository import PatternRepository
from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.swarm.agents.code_review_swarm import CodeReviewSwarm


# Configure logging to see the 'Throttling' messages
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def main():
    # 1. Initialize DB Client (will fallback to InMemory if offline)
    client = SurrealClient()

    # 2. Initialize Repository
    repo = PatternRepository(client, buffer_path="cache/test_pattern_buffer.json")

    # 3. Initialize Swarm
    # We'll scan src/cohezion/core/persistence as it's a small, important folder
    swarm = CodeReviewSwarm(
        repository=repo,
        target_dir="src/cohezion/core/persistence",
        batch_size=2,  # Tiny batches for verification
        complexity_threshold=10,  # Low threshold to trigger LLM scouts
    )

    print("\n--- 🛡️ Starting SAFE MODE Code Review Swarm Verification ---")
    print(f"Target: {swarm.target_dir}")
    print("-----------------------------------------------------------\n")

    # Run the scan
    report = await swarm.run_full_scan()

    print("\n--- 📊 Final Report ---")
    print(f"Total Files: {report.total_files}")
    print(f"Scanned Files: {report.scanned_files}")
    print(f"High Complexity Files: {len(report.high_complexity_files)}")
    print(f"Total Findings: {len(report.findings)}")

    if report.high_complexity_files:
        print("\nHigh Complexity Targets Found:")
        for f in report.high_complexity_files:
            print(f"  - {f}")

    print("\nCheck cache/test_pattern_buffer.json for persisted findings.")


if __name__ == "__main__":
    asyncio.run(main())
