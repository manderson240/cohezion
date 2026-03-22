"""
Phase 2: Full-Codebase Static Scan
Performs zero-token AST analysis on all files to identify High Interest targets.
Enforces Safe Mode cooldowns and resource guards.
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


async def main():
    # 1. Initialize Infrastructure
    client = SurrealClient()
    repo = PatternRepository(client, buffer_path="cache/full_scan_buffer.json")

    # 2. Initialize Swarm Orchestrator
    swarm = CodeReviewSwarm(
        repository=repo,
        target_dir="src/cohezion",
        batch_size=10,  # Moderate batches for static-only scan
        complexity_threshold=15,
    )

    print("\n--- 🚀 Starting Phase 2: Full-Codebase Static Scan (Safe Mode) ---")
    print(f"Target: {swarm.target_dir}")
    print("----------------------------------------------------------------\n")

    # Run the full scan
    # Note: run_full_scan handles Phase 1 (static) and Phase 2 (semantic) internally.
    # We want to run ONLY the static part first for the user gate.

    all_files = list(Path("src/cohezion").rglob("*.py"))
    findings = []
    high_complexity = []

    scanned = 0
    for i in range(0, len(all_files), swarm.batch_size):
        batch = all_files[i : i + swarm.batch_size]
        for file_path in batch:
            # Resource Check
            await swarm.static_scout.guard.wait_for_stability()

            # Static Scan
            f = await swarm.static_scout.scan_file(file_path)
            findings.extend(f)

            # Complexity Check
            ast_sum = swarm.static_scout._parse_python_ast(file_path)
            if ast_sum and ast_sum.complexity_score >= swarm.complexity_threshold:
                high_complexity.append(
                    {
                        "path": str(file_path),
                        "complexity": ast_sum.complexity_score,
                        "loc": ast_sum.loc,
                    }
                )

            scanned += 1

        logging.info(f"Progress: {scanned}/{len(all_files)} files static-scanned...")

    # 3. Generate High Complexity Report
    report_path = Path(
        "/home/mike-anderson/.gemini/antigravity/brain/42233b97-45f7-4a48-bd44-7a7be04e48c9/high_complexity_targets.md"
    )

    # Sort by complexity DESC
    high_complexity.sort(key=lambda x: x["complexity"], reverse=True)

    with open(report_path, "w") as rf:
        rf.write("# 🧠 High Complexity & High Interest Targets\n\n")
        rf.write(
            "The following files have been identified via static analysis as high-value targets for deep semantic (LLM) review.\n\n"
        )
        rf.write("| File Path | Complexity | LoC | Reason |\n")
        rf.write("|-----------|------------|-----|--------|\n")
        for h in high_complexity:
            reason = "High Complexity" if h["complexity"] >= 15 else "Large File"
            rf.write(
                f"| [`{h['path']}`](file://{Path(h['path']).absolute()}) | {h['complexity']} | {h['loc']} | {reason} |\n"
            )

    print(f"\n✅ Phase 2 Static Scan Complete. Found {len(high_complexity)} targets.")
    print(f"Report generated at: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
