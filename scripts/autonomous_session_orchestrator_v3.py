#!/usr/bin/env python3
"""
Autonomous Session Orchestrator Phase 3: Real Work Integration
=============================================================

Connects autonomous cycles to actual lint fixing work.
Processes real ruff --fix batches instead of mock work.

Usage:
    uv run python scripts/autonomous_session_orchestrator_v3.py --mode continuous
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WorkItem:
    """Actual work item to process."""

    id: str
    type: str  # "lint_batch", "test_run", "doc_update"
    description: str
    command: list[str]
    expected_outcome: str
    status: str = "pending"
    result: dict | None = None


class RealWorkProcessor:
    """Process actual lint fixes and optimizations."""

    def __init__(self):
        self.work_queue: list[WorkItem] = []
        self.completed: list[WorkItem] = []
        self.errors_fixed = 0

    def populate_lint_queue(self) -> int:
        """Populate queue with lint error batches."""

        # Get current error counts
        batches = [
            WorkItem(
                id="e501_batch_1",
                type="lint_batch",
                description="Fix E501 line too long errors (first 100)",
                command=[
                    "ruff",
                    "check",
                    ".",
                    "--select",
                    "E501",
                    "--fix",
                    "--output-format=concise",
                ],
                expected_outcome="~100 line length errors fixed",
            ),
            WorkItem(
                id="ruf059_batch_1",
                type="lint_batch",
                description="Fix RUF059 unused variable errors (first 100)",
                command=[
                    "ruff",
                    "check",
                    ".",
                    "--select",
                    "RUF059",
                    "--fix",
                    "--output-format=concise",
                ],
                expected_outcome="~100 unused variables fixed",
            ),
            WorkItem(
                id="f401_batch_1",
                type="lint_batch",
                description="Fix F401 unused import errors (first 100)",
                command=[
                    "ruff",
                    "check",
                    ".",
                    "--select",
                    "F401",
                    "--fix",
                    "--output-format=concise",
                ],
                expected_outcome="~100 unused imports fixed",
            ),
            WorkItem(
                id="i001_batch_1",
                type="lint_batch",
                description="Fix I001 import sorting",
                command=[
                    "ruff",
                    "check",
                    ".",
                    "--select",
                    "I001",
                    "--fix",
                    "--output-format=concise",
                ],
                expected_outcome="Import sorting applied",
            ),
        ]

        for batch in batches:
            self.work_queue.append(batch)

        logger.info(f"✅ Populated work queue with {len(batches)} lint batches")
        return len(batches)

    async def process_next_item(self) -> WorkItem | None:
        """Process next work item."""
        if not self.work_queue:
            return None

        item = self.work_queue.pop(0)
        item.status = "processing"

        logger.info(f"🔧 Processing: {item.description}")

        try:
            # Execute ruff fix
            proc = await asyncio.create_subprocess_exec(
                *item.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)

            # Parse results
            output = stdout.decode() if stdout else ""
            error_count = output.count("E501") + output.count("RUF059") + output.count("F401")

            item.result = {
                "returncode": proc.returncode,
                "stdout": output[:500] if output else "",  # Truncate
                "stderr": stderr.decode()[:500] if stderr else "",
                "errors_fixed_approx": error_count,
            }

            if proc.returncode == 0 or "fixed" in output.lower():
                item.status = "completed"
                self.errors_fixed += error_count
                logger.info(f"✅ Completed: {item.description}")
            else:
                item.status = "failed"
                logger.warning(f"⚠️  Failed: {item.description}")

        except asyncio.TimeoutError:
            item.status = "timeout"
            item.result = {"error": "Timeout after 120s"}
            logger.error(f"⏱️ Timeout: {item.description}")

        except Exception as e:
            item.status = "error"
            item.result = {"error": str(e)}
            logger.error(f"❌ Error: {e}")

        self.completed.append(item)
        return item

    def has_work(self) -> bool:
        """Check if there's work remaining."""
        return len(self.work_queue) > 0

    def get_stats(self) -> dict:
        """Get work statistics."""
        completed = len([i for i in self.completed if i.status == "completed"])
        failed = len([i for i in self.completed if i.status in ["failed", "error", "timeout"]])

        return {
            "queue_remaining": len(self.work_queue),
            "completed": completed,
            "failed": failed,
            "total": completed + failed + len(self.work_queue),
            "errors_fixed": self.errors_fixed,
        }


class AutonomousOrchestratorV3:
    """Phase 3: Real work integration."""

    def __init__(self):
        self.processor = RealWorkProcessor()
        self.cycle_count = 0
        self.start_time = datetime.now()

    async def run_cycle(self) -> dict[str, Any]:
        """Run one cycle with real work."""
        self.cycle_count += 1
        cycle = self.cycle_count

        logger.info(f"\n{'=' * 60}")
        logger.info(f"🚀 AUTONOMOUS CYCLE #{cycle} (Phase 3: Real Work)")
        logger.info(f"{'=' * 60}\n")

        cycle_data = {
            "cycle": cycle,
            "timestamp": datetime.now().isoformat(),
        }

        # Step 1: Populate work queue if empty
        if not self.processor.has_work():
            count = self.processor.populate_lint_queue()
            cycle_data["queue_populated"] = count

        # Step 2: Process next work item
        if self.processor.has_work():
            item = await self.processor.process_next_item()
            if item:
                cycle_data["work_item"] = {
                    "id": item.id,
                    "type": item.type,
                    "description": item.description,
                    "status": item.status,
                    "result": item.result,
                }

        # Step 3: Commit if files changed
        commit_success = await self._commit_work(cycle)
        cycle_data["commit_success"] = commit_success

        # Step 4: Save cycle data
        cycle_path = Path("_bmad/_config/traceability/cycles_v3")
        cycle_path.mkdir(parents=True, exist_ok=True)
        cycle_file = cycle_path / f"cycle_{cycle:04d}.json"
        cycle_file.write_text(json.dumps(cycle_data, indent=2))

        # Step 5: Log stats
        stats = self.processor.get_stats()
        logger.info(
            f"📊 Stats: {stats['completed']}/{stats['total']} complete, {stats['errors_fixed']} errors fixed"
        )

        logger.info(f"✅ Cycle #{cycle} complete")

        return cycle_data

    async def _commit_work(self, cycle: int) -> bool:
        """Commit any changes."""
        try:
            # Check for changes
            proc = await asyncio.create_subprocess_exec(
                "git",
                "status",
                "--porcelain",
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)

            if not stdout.strip():
                return False  # No changes

            # Stage and commit
            await asyncio.create_subprocess_exec("git", "add", "-A")

            commit_msg = f"autonomous: cycle #{cycle} - fix lint errors via ruff"
            proc = await asyncio.create_subprocess_exec(
                "git",
                "commit",
                "-m",
                commit_msg,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            await asyncio.wait_for(proc.wait(), timeout=60.0)

            if proc.returncode == 0:
                logger.info(f"💾 Committed: {commit_msg}")
                return True

        except Exception as e:
            logger.warning(f"Commit failed: {e}")

        return False

    async def run_continuous(self):
        """Run continuous with real work."""
        logger.info("\n" + "=" * 60)
        logger.info("🤖 AUTONOMOUS ORCHESTRATOR V3 ACTIVATED")
        logger.info("=" * 60)
        logger.info("Phase 3: Real Work Integration")
        logger.info("  • Auto-fixes lint errors with ruff")
        logger.info("  • Commits changes every cycle")
        logger.info("  • Tracks errors fixed")
        logger.info("=" * 60 + "\n")

        # Initial population
        self.processor.populate_lint_queue()

        try:
            while self.processor.has_work():
                await self.run_cycle()

                # Brief pause between cycles
                await asyncio.sleep(2)

        except KeyboardInterrupt:
            logger.info("\n🛑 Stopped by user")

        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 FINAL SUMMARY")
        logger.info("=" * 60)
        stats = self.processor.get_stats()
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")

        duration = (datetime.now() - self.start_time).seconds // 60
        logger.info(f"  duration_minutes: {duration}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["continuous", "single"], default="single")
    args = parser.parse_args()

    orchestrator = AutonomousOrchestratorV3()

    if args.mode == "continuous":
        await orchestrator.run_continuous()
    else:
        result = await orchestrator.run_cycle()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
