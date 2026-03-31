#!/usr/bin/env python3
"""
Autonomous Session Orchestrator Phase 2
======================================

Refined version based on 893 cycles of learnings:
- Async git operations with retry
- Checkpoint recovery every 100 cycles
- Adaptive sleep based on work queue
- Log rotation to prevent bloat
- Better error handling

Usage:
    uv run python scripts/autonomous_session_orchestrator_v2.py --mode continuous
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Session state tracking."""

    cycle_count: int = 0
    token_count: int = 0
    commit_count: int = 0
    skills_captured: list[str] = field(default_factory=list)
    errors_fixed: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    checkpoint_cycle: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_count": self.cycle_count,
            "token_count": self.token_count,
            "commit_count": self.commit_count,
            "skills_captured": self.skills_captured,
            "errors_fixed": self.errors_fixed,
            "start_time": self.start_time.isoformat(),
            "duration_minutes": (datetime.now() - self.start_time).seconds // 60,
            "checkpoint_cycle": self.checkpoint_cycle,
        }


class AsyncGitManager:
    """Async git operations with retry logic."""

    def __init__(self, timeout: float = 60.0, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries

    async def commit(self, message: str) -> bool:
        """Async commit with exponential backoff retry."""
        for attempt in range(self.max_retries):
            try:
                # Stage files
                proc = await asyncio.create_subprocess_exec(
                    "git",
                    "add",
                    "-A",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(proc.wait(), timeout=self.timeout)

                # Commit
                proc = await asyncio.create_subprocess_exec(
                    "git",
                    "commit",
                    "-m",
                    message,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(proc.wait(), timeout=self.timeout)

                if proc.returncode == 0:
                    return True

            except asyncio.TimeoutError:
                logger.warning(f"Git commit timeout (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"Git commit error: {e}")

        return False


class CheckpointManager:
    """Periodic state checkpointing."""

    def __init__(self, checkpoint_interval: int = 100):
        self.checkpoint_interval = checkpoint_interval
        self.last_checkpoint = 0

    async def should_checkpoint(self, cycle: int) -> bool:
        """Check if we should checkpoint now."""
        return cycle > 0 and cycle % self.checkpoint_interval == 0

    async def save_checkpoint(self, context: SessionContext, tree: dict) -> Path:
        """Save state checkpoint."""
        checkpoint = {
            "cycle": context.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "context": context.to_dict(),
            "tree_snapshot": tree.get("nodes", {}),
        }

        checkpoint_path = Path(f"_bmad/_config/traceability/checkpoints")
        checkpoint_path.mkdir(parents=True, exist_ok=True)

        checkpoint_file = checkpoint_path / f"checkpoint_{context.cycle_count:04d}.json"
        checkpoint_file.write_text(json.dumps(checkpoint, indent=2))

        self.last_checkpoint = context.cycle_count
        logger.info(f"💾 Checkpoint saved: {checkpoint_file.name}")

        return checkpoint_file


class LogRotator:
    """Rotate logs to prevent bloat."""

    def __init__(self, max_size_mb: int = 10, max_files: int = 5):
        self.max_size_mb = max_size_mb
        self.max_files = max_files
        self.log_file = Path("autonomous_session.log")

    async def check_and_rotate(self) -> bool:
        """Check log size and rotate if needed."""
        if not self.log_file.exists():
            return False

        size_mb = self.log_file.stat().st_size / (1024 * 1024)

        if size_mb > self.max_size_mb:
            # Rotate: rename current to .1, .1 to .2, etc.
            for i in range(self.max_files - 1, 0, -1):
                old_file = self.log_file.parent / f"{self.log_file.name}.{i}"
                new_file = self.log_file.parent / f"{self.log_file.name}.{i + 1}"
                if old_file.exists():
                    old_file.rename(new_file)

            # Rename current log
            self.log_file.rename(self.log_file.parent / f"{self.log_file.name}.1")
            logger.info(f"🔄 Log rotated (size: {size_mb:.1f}MB)")
            return True

        return False


class WorkQueue:
    """Actual work items to process."""

    def __init__(self):
        self.queue: list[dict] = []
        self.completed: list[dict] = []

    def has_work(self) -> bool:
        """Check if there's work to do."""
        return len(self.queue) > 0

    def get_next_item(self) -> dict | None:
        """Get next work item."""
        if self.queue:
            return self.queue.pop(0)
        return None

    def add_item(self, item: dict):
        """Add work item."""
        self.queue.append(item)

    def complete_item(self, item: dict, result: dict):
        """Mark item complete."""
        self.completed.append({"item": item, "result": result})


class AutonomousOrchestratorV2:
    """Phase 2: Refined based on 893 cycles of learnings."""

    def __init__(self):
        self.context = SessionContext()
        self.git = AsyncGitManager(timeout=60.0, max_retries=3)
        self.checkpoint = CheckpointManager(checkpoint_interval=100)
        self.log_rotator = LogRotator(max_size_mb=10, max_files=5)
        self.work_queue = WorkQueue()

    async def run_cycle(self) -> dict[str, Any]:
        """Run one autonomous cycle with Phase 2 improvements."""
        self.context.cycle_count += 1
        cycle = self.context.cycle_count

        logger.info(f"\n{'=' * 60}")
        logger.info(f"🚀 AUTONOMOUS CYCLE #{cycle} (Phase 2)")
        logger.info(f"{'=' * 60}\n")

        cycle_data = {
            "cycle": cycle,
            "timestamp": datetime.now().isoformat(),
        }

        # 1. Log rotation check
        if await self.log_rotator.check_and_rotate():
            cycle_data["log_rotated"] = True

        # 2. Checkpoint if needed
        if await self.checkpoint.should_checkpoint(cycle):
            checkpoint_file = await self.checkpoint.save_checkpoint(self.context, {"nodes": {}})
            cycle_data["checkpoint"] = str(checkpoint_file)

        # 3. Process work queue if items exist
        work_item = self.work_queue.get_next_item()
        if work_item:
            result = await self._process_work_item(work_item)
            cycle_data["work_processed"] = result

        # 4. Async commit with retry
        commit_success = await self.git.commit(f"autonomous: cycle #{cycle} - Phase 2 operation")
        cycle_data["commit_success"] = commit_success

        if commit_success:
            self.context.commit_count += 1
            logger.info(f"💾 Committed cycle #{cycle}")

        # 5. Save cycle data
        cycle_path = Path("_bmad/_config/traceability/cycles_v2")
        cycle_path.mkdir(parents=True, exist_ok=True)
        cycle_file = cycle_path / f"cycle_{cycle:04d}.json"
        cycle_file.write_text(json.dumps(cycle_data, indent=2))

        logger.info(f"✅ Cycle #{cycle} complete")

        return cycle_data

    async def _process_work_item(self, item: dict) -> dict:
        """Process actual work item."""
        logger.info(f"🔧 Processing work item: {item.get('type', 'unknown')}")

        # Placeholder - would process actual tasks
        result = {"status": "processed", "item": item}
        self.work_queue.complete_item(item, result)

        return result

    async def run_continuous(self):
        """Run continuous with Phase 2 improvements."""
        logger.info("\n" + "=" * 60)
        logger.info("🤖 AUTONOMOUS ORCHESTRATOR V2 ACTIVATED")
        logger.info("=" * 60)
        logger.info("Phase 2 Improvements:")
        logger.info("  • Async git with retry (60s timeout)")
        logger.info("  • Checkpoint every 100 cycles")
        logger.info("  • Log rotation at 10MB")
        logger.info("  • Work queue processing")
        logger.info("  • Better error handling")
        logger.info("=" * 60 + "\n")

        try:
            while True:
                await self.run_cycle()

                # Adaptive sleep: short if work, long if idle
                if self.work_queue.has_work():
                    await asyncio.sleep(1)
                else:
                    await asyncio.sleep(30)  # Wait for work

        except KeyboardInterrupt:
            logger.info("\n🛑 Stopped by user")

        # Final checkpoint
        await self.checkpoint.save_checkpoint(self.context, {"nodes": {}})

        logger.info("\n" + "=" * 60)
        logger.info("📊 SESSION SUMMARY")
        logger.info("=" * 60)
        summary = self.context.to_dict()
        for key, value in summary.items():
            logger.info(f"  {key}: {value}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["continuous", "single"], default="single")
    args = parser.parse_args()

    orchestrator = AutonomousOrchestratorV2()

    if args.mode == "continuous":
        await orchestrator.run_continuous()
    else:
        result = await orchestrator.run_cycle()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
