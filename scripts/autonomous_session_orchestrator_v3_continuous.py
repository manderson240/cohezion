#!/usr/bin/env python3
"""
Autonomous Session Orchestrator Phase 3.5: Continuous Work Mode
=============================================================

Self-sustaining autonomous operation that continuously:
1. Discovers new work (lint errors, tests, docs)
2. Processes work items
3. Commits changes
4. Replenishes queue automatically

Usage:
    uv run python scripts/autonomous_session_orchestrator_v3_continuous.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SessionMetrics:
    """Track session performance."""

    start_time: datetime = field(default_factory=datetime.now)
    cycles_completed: int = 0
    work_items_completed: int = 0
    errors_fixed: int = 0
    commits_made: int = 0
    last_replenish: datetime = field(default_factory=datetime.now)

    def summary(self) -> dict[str, Any]:
        duration = (datetime.now() - self.start_time).total_seconds()
        return {
            "duration_hours": duration / 3600,
            "cycles_per_hour": self.cycles_completed / (duration / 3600) if duration > 0 else 0,
            "work_items": self.work_items_completed,
            "errors_fixed": self.errors_fixed,
            "commits": self.commits_made,
        }


class WorkDiscovery:
    """Continuously discover new work items."""

    def __init__(self):
        self.discovery_interval = timedelta(minutes=5)
        self.last_discovery = datetime.now() - timedelta(hours=1)  # Force first discovery

    async def should_discover(self) -> bool:
        """Check if it's time to discover new work."""
        return datetime.now() - self.last_discovery > self.discovery_interval

    async def discover_work(self) -> list[dict]:
        """Discover available work items."""
        work_items = []

        # 1. Lint errors by category
        categories = [
            ("E501", "line-too-long"),
            ("RUF059", "unused-variables"),
            ("F401", "unused-imports"),
            ("I001", "import-sorting"),
            ("N806", "variable-naming"),
        ]

        for code, desc in categories:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "ruff",
                    "check",
                    ".",
                    "--select",
                    code,
                    "--output-format",
                    "json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)

                if stdout:
                    errors = json.loads(stdout)
                    if len(errors) > 0:
                        work_items.append(
                            {
                                "id": f"{code}_{datetime.now().strftime('%H%M%S')}",
                                "type": "lint_batch",
                                "category": code,
                                "description": f"Fix {desc} ({len(errors)} errors)",
                                "command": ["ruff", "check", ".", "--select", code, "--fix"],
                                "estimated_count": len(errors),
                                "priority": "high"
                                if code in ["E722", "F821", "S607"]
                                else "medium",
                            }
                        )
            except Exception as e:
                logger.warning(f"Discovery failed for {code}: {e}")

        # 2. Test discovery
        try:
            proc = await asyncio.create_subprocess_exec(
                "uv",
                "run",
                "pytest",
                "--collect-only",
                "-q",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            test_count = len([l for l in stdout.decode().split("\n") if "test_" in l])

            if test_count > 0:
                work_items.append(
                    {
                        "id": f"test_run_{datetime.now().strftime('%H%M%S')}",
                        "type": "test_run",
                        "description": f"Run test suite ({test_count} tests)",
                        "command": ["uv", "run", "pytest", "-x", "-q"],
                        "estimated_count": test_count,
                        "priority": "low",
                    }
                )
        except Exception:
            pass

        self.last_discovery = datetime.now()
        logger.info(f"🔍 Discovered {len(work_items)} work items")
        return work_items


class RealWorkProcessor:
    """Process actual work with git integration."""

    def __init__(self):
        self.work_queue: list[dict] = []
        self.completed: list[dict] = []
        self.discovery = WorkDiscovery()

    async def ensure_work_available(self) -> bool:
        """Ensure queue has work, discover if empty."""
        if not self.work_queue and await self.discovery.should_discover():
            new_items = await self.discovery.discover_work()
            self.work_queue.extend(new_items)
        return len(self.work_queue) > 0

    async def process_next_item(self) -> dict | None:
        """Process next work item."""
        if not await self.ensure_work_available():
            return None

        item = self.work_queue.pop(0)
        logger.info(f"🔧 Processing: {item['description']}")

        try:
            # Execute work
            proc = await asyncio.create_subprocess_exec(
                *item["command"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=180.0,  # 3 minute timeout
            )

            result = {
                "status": "completed" if proc.returncode == 0 else "partial",
                "returncode": proc.returncode,
                "stdout": stdout.decode()[:1000] if stdout else "",
            }

            # Commit if there are changes
            await self._try_commit(item["description"])

            self.completed.append({"item": item, "result": result})
            return {"item": item, "result": result}

        except asyncio.TimeoutError:
            logger.error(f"⏱️ Timeout: {item['description']}")
            return {"item": item, "result": {"status": "timeout"}}
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return {"item": item, "result": {"status": "error", "error": str(e)}}

    async def _try_commit(self, description: str) -> bool:
        """Try to commit any changes."""
        try:
            # Check if there are changes
            proc = await asyncio.create_subprocess_exec(
                "git",
                "status",
                "--porcelain",
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)

            if not stdout.strip():
                return False

            # Stage and commit
            await asyncio.create_subprocess_exec("git", "add", "-A")

            safe_desc = description[:50]  # Truncate for commit message
            proc = await asyncio.create_subprocess_exec(
                "git",
                "commit",
                "-m",
                f"autonomous: {safe_desc}",
                stdout=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.wait(), timeout=60.0)

            return proc.returncode == 0

        except Exception as e:
            logger.warning(f"Commit failed: {e}")
            return False


class AutonomousOrchestratorV3Continuous:
    """Phase 3.5: Self-sustaining continuous operation."""

    def __init__(self):
        self.processor = RealWorkProcessor()
        self.metrics = SessionMetrics()
        self.running = True

    async def run_cycle(self) -> dict[str, Any]:
        """Run one autonomous cycle."""
        self.metrics.cycles_completed += 1
        cycle = self.metrics.cycles_completed

        logger.info(f"\n{'=' * 60}")
        logger.info(f"🚀 CYCLE #{cycle} | {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"{'=' * 60}")

        cycle_data = {
            "cycle": cycle,
            "timestamp": datetime.now().isoformat(),
        }

        # Process work
        result = await self.processor.process_next_item()
        if result:
            self.metrics.work_items_completed += 1
            cycle_data["work"] = result

            if result["result"].get("status") == "completed":
                self.metrics.commits_made += 1

        # Periodic stats every 10 cycles
        if cycle % 10 == 0:
            stats = self.metrics.summary()
            logger.info(f"\n📊 STATS (Cycle {cycle}):")
            for key, value in stats.items():
                logger.info(
                    f"  {key}: {value:.2f}" if isinstance(value, float) else f"  {key}: {value}"
                )

        # Save cycle data
        cycle_path = Path("_bmad/_config/traceability/cycles_continuous")
        cycle_path.mkdir(parents=True, exist_ok=True)
        cycle_file = cycle_path / f"cycle_{cycle:05d}.json"
        cycle_file.write_text(json.dumps(cycle_data, indent=2))

        return cycle_data

    async def run_continuous(self):
        """Run continuous autonomous operation."""
        logger.info("\n" + "=" * 60)
        logger.info("🤖 PHASE 3.5: CONTINUOUS AUTONOMOUS OPERATION")
        logger.info("=" * 60)
        logger.info("Features:")
        logger.info("  • Self-discovering work items")
        logger.info("  • Auto-replenishing queue")
        logger.info("  • Real lint fixing with ruff")
        logger.info("  • Automatic git commits")
        logger.info("  • Stats every 10 cycles")
        logger.info("=" * 60 + "\n")

        try:
            while self.running:
                await self.run_cycle()

                # Adaptive sleep: fast when busy, slow when idle
                has_work = await self.processor.ensure_work_available()
                if has_work:
                    await asyncio.sleep(2)
                else:
                    logger.info("⏳ No work available, waiting 60s...")
                    await asyncio.sleep(60)

        except KeyboardInterrupt:
            logger.info("\n🛑 Stopped by user")
            self.running = False

        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 FINAL SUMMARY")
        logger.info("=" * 60)
        stats = self.metrics.summary()
        for key, value in stats.items():
            logger.info(
                f"  {key}: {value:.2f}" if isinstance(value, float) else f"  {key}: {value}"
            )


async def main():
    orchestrator = AutonomousOrchestratorV3Continuous()
    await orchestrator.run_continuous()


if __name__ == "__main__":
    asyncio.run(main())
