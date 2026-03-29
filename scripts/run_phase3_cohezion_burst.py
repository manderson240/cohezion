"""
Phase 3: Targeted Cohezion Burst
Focuses semantic analysis on the Top 7 architectural anchors.
Enforces Safe Mode v3 (sequential, throttled).
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


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Core Cohezion Targets
COHEZION_TARGETS = [
    "src/cohezion/core/persistence/surreal_client.py",
    "src/cohezion/skills/cohezion_mcp.py",
    "src/cohezion/api/__init__.py",
    "src/cohezion/reliability/quantum_performance_monitor.py",
    "src/cohezion/compound/executor.py",
    "src/cohezion/sandbox/rollback.py",
    "src/cohezion/agents/base.py",
    "src/cohezion/__main__.py",
    "src/cohezion/compound/request_alignment_analyzer.py",
    "src/cohezion/registry/capability_registry.py",
]


async def main():
    client = SurrealClient()
    repo = PatternRepository(client, buffer_path="cache/cohezion_burst_buffer.json")

    swarm = CodeReviewSwarm(repository=repo, target_dir="src/cohezion", batch_size=1)

    print("\n--- ⚡ Starting PHASE 3: COHEZION BURST (Semantic Scan) ---")
    print(f"Targeting {len(COHEZION_TARGETS)} Core Architectural Anchors.")
    print("------------------------------------------------------------\n")

    for path in COHEZION_TARGETS:
        file_path = Path(path)
        if not file_path.exists():
            logging.warning(f"Target not found: {path}")
            continue

        logging.info(f"🧠 Analyzing COHEZION ANCHOR: {path}")

        # Sequentially run ALL three semantic scouts: Architecture, Pattern, AntiPattern
        for scout in swarm.llm_scouts:
            try:
                # BaseScout handles sequential LLM lock and ResourceGuard internaly
                findings = await scout.scan_file(file_path)
                for f in findings:
                    await swarm._persist_finding(f)
            except Exception as e:
                logging.error(f"Failed analysis of {path} with {scout.__class__.__name__}: {e}")

        logging.info(f"✅ Completed analysis for {path}")
        await asyncio.sleep(10.0)  # Extended cooldown between architectural pillars

    print("\n🚀 Cohezion Burst Complete. Check cache/cohezion_burst_buffer.json.")


if __name__ == "__main__":
    asyncio.run(main())
