#!/usr/bin/env python3
"""Overnight autoresearch runner with checkpointing and recovery.

Runs continuous optimization experiments overnight with:
- Periodic checkpointing (every 10 runs)
- Resume capability on failure
- Progress logging to file + stdout
- Automatic metric tracking
- Graceful shutdown on SIGTERM

Charter: Transparent operation, resume on failure, no data loss.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("overnight_autoresearch.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("overnight_runner")


@dataclass
class Checkpoint:
    """Autoresearch checkpoint state."""
    
    session_name: str
    run_count: int
    best_metric: float
    current_phase: str
    timestamp: str
    git_commit: str
    experiments_completed: list[int] = field(default_factory=list)
    
    def save(self, path: Path) -> None:
        """Save checkpoint to disk."""
        path.write_text(json.dumps(self.__dict__, indent=2, default=str))
        logger.info(f"Checkpoint saved: {path}")
    
    @classmethod
    def load(cls, path: Path) -> Optional[Checkpoint]:
        """Load checkpoint from disk."""
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return cls(**data)


class OvernightRunner:
    """Manage overnight autoresearch experiments.
    
    Strategy:
    1. Load checkpoint or start fresh
    2. Run experiments until max_runs or time limit
    3. Checkpoint every N runs
    4. On interrupt: save state, cleanup, exit gracefully
    """
    
    def __init__(
        self,
        session_name: str = "overnight_datamesh",
        max_runs: int = 50,
        checkpoint_interval: int = 5,
        time_limit_hours: int = 8,
    ):
        self.session_name = session_name
        self.max_runs = max_runs
        self.checkpoint_interval = checkpoint_interval
        self.time_limit_seconds = time_limit_hours * 3600
        
        self.checkpoint_path = Path(f".autoresearch_checkpoint_{session_name}.json")
        self.start_time = time.time()
        self._shutdown_requested = False
        self._current_run = 0
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, requesting shutdown...")
        self._shutdown_requested = True
    
    def _get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Could not get git commit: {e}")
            return "unknown"
    
    def _run_benchmark(self) -> tuple[float, dict[str, Any]]:
        """Run the benchmark and return metric + metadata.
        
        This should be customized for the specific optimization target.
        """
        # Example: Datamesh query latency benchmark
        try:
            start = time.time()
            
            # Run your benchmark command here
            result = subprocess.run(
                ["python", "-m", "cohezion.benchmarks.datamesh_query"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            # Parse metric from output
            # Expected format: "METRIC query_latency_ms=XX.XX"
            metric = 999.0  # Placeholder - would parse from output
            metadata = {}
            
            elapsed = (time.time() - start) * 1000
            logger.info(f"Benchmark complete in {elapsed:.1f}ms")
            
            return metric, metadata
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            return float("inf"), {"error": str(e)}
    
    def _run_experiment(self, description: str, hypothesis: str) -> dict[str, Any]:
        """Run a single experiment using pi's run_experiment API."""
        # This would integrate with the actual pi autoresearch system
        # For now, return a mock result
        return {
            "run": self._current_run,
            "commit": self._get_git_commit(),
            "metric": 100.0 + (self._current_run * 0.5),  # Mock
            "status": "keep" if self._current_run % 3 == 0 else "discard",
            "description": description,
            "asi": {"hypothesis": hypothesis},
        }
    
    def _checkpoint(self) -> None:
        """Save current state to checkpoint file."""
        checkpoint = Checkpoint(
            session_name=self.session_name,
            run_count=self._current_run,
            best_metric=0.0,  # Would track actual best
            current_phase="running",
            timestamp=datetime.now().isoformat(),
            git_commit=self._get_git_commit(),
            experiments_completed=list(range(1, self._current_run + 1)),
        )
        checkpoint.save(self.checkpoint_path)
    
    async def run(self) -> Checkpoint:
        """Main overnight run loop.
        
        Returns final checkpoint state.
        """
        logger.info("=" * 60)
        logger.info(f"Starting overnight autoresearch: {self.session_name}")
        logger.info(f"Target: {self.max_runs} runs, {self.checkpoint_interval} per checkpoint")
        logger.info(f"Time limit: {self.time_limit_seconds / 3600:.1f} hours")
        logger.info("=" * 60)
        
        # Load checkpoint if exists
        checkpoint = Checkpoint.load(self.checkpoint_path)
        if checkpoint:
            logger.info(f"Resuming from checkpoint: run {checkpoint.run_count}")
            self._current_run = checkpoint.run_count
        else:
            logger.info("Starting fresh session")
            self._current_run = 0
        
        results = []
        
        while (
            self._current_run < self.max_runs and
            time.time() - self.start_time < self.time_limit_seconds and
            not self._shutdown_requested
        ):
            self._current_run += 1
            run_start = time.time()
            
            logger.info(f"\n--- Run {self._current_run}/{self.max_runs} ---")
            
            # Generate experiment from previous learnings
            # This would use the kg_search to find patterns
            hypothesis = f"Optimization attempt {self._current_run}"
            description = f"Auto-generated experiment based on prior results"
            
            try:
                result = self._run_experiment(description, hypothesis)
                results.append(result)
                
                # Log result
                status = result.get("status", "unknown")
                metric = result.get("metric", 0)
                logger.info(f"Status: {status}, Metric: {metric:.4f}")
                
                # Checkpoint every N runs
                if self._current_run % self.checkpoint_interval == 0:
                    self._checkpoint()
                    
            except Exception as e:
                logger.error(f"Experiment failed: {e}")
                self._checkpoint()  # Save state on failure
                raise
            
            run_elapsed = time.time() - run_start
            logger.info(f"Run completed in {run_elapsed:.1f}s")
            
            # Brief pause between runs
            await asyncio.sleep(1)
        
        # Final checkpoint
        final_checkpoint = Checkpoint(
            session_name=self.session_name,
            run_count=self._current_run,
            best_metric=min([r["metric"] for r in results]) if results else 0,
            current_phase="completed" if self._current_run >= self.max_runs else "interrupted",
            timestamp=datetime.now().isoformat(),
            git_commit=self._get_git_commit(),
            experiments_completed=[r["run"] for r in results],
        )
        final_checkpoint.save(self.checkpoint_path)
        
        # Generate summary report
        self._generate_report(results)
        
        return final_checkpoint
    
    def _generate_report(self, results: list[dict]) -> None:
        """Generate morning report."""
        report_path = Path(f"overnight_report_{self.session_name}_{datetime.now():%Y%m%d}.md")
        
        report = f"""# Overnight Autoresearch Report

**Session**: {self.session_name}  
**Date**: {datetime.now().isoformat()}  
**Runs Completed**: {len(results)}

## Summary

| Metric | Value |
|--------|-------|
| Total Runs | {len(results)} |
| Successful | {len([r for r in results if r.get("status") == "keep"])} |
| Failed | {len([r for r in results if r.get("status") == "crash"])} |
| Best Metric | {min([r["metric"] for r in results]) if results else "N/A"} |

## Experiments

| Run | Status | Metric | Description |
|-----|--------|--------|-------------|
"""
        
        for r in results:
            report += f"| {r['run']} | {r['status']} | {r['metric']:.4f} | {r['description'][:50]}... |\n"
        
        report_path.write_text(report)
        logger.info(f"Report saved: {report_path}")


def main():
    """CLI entry point."""
    runner = OvernightRunner(
        session_name="datamesh_overnight",
        max_runs=50,
        checkpoint_interval=5,
        time_limit_hours=8,
    )
    
    try:
        checkpoint = asyncio.run(runner.run())
        logger.info(f"Complete. Checkpoint at run {checkpoint.run_count}")
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
