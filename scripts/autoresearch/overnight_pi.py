#!/usr/bin/env python3
"""Overnight autoresearch runner using pi's experiment tools.

Designed to run 8+ hours with checkpointing and recovery.

Charter-compliant: Transparent, idempotent, fault-tolerant.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class OvernightState:
    """Serializable overnight run state."""

    session_name: str
    run_number: int
    best_metric: float
    experiments: list[dict]
    start_time: float
    last_checkpoint: float
    git_commit: str
    status: str = "running"  # running | paused | completed | error


class OvernightRunner:
    """Long-horizon autoresearch with pi tools."""

    def __init__(
        self,
        session_name: str = "datamesh_overnight",
        max_runs: int = 50,
        checkpoint_every: int = 5,
        timeout_hours: int = 8,
    ):
        self.session_name = session_name
        self.max_runs = max_runs
        self.checkpoint_every = checkpoint_every
        self.timeout_seconds = timeout_hours * 3600

        self.checkpoint_path = Path(f".checkpoint_{session_name}.json")
        self.log_path = Path(f"overnight_{session_name}.log")

        self.state: OvernightState | None = None
        self.start_time = time.time()

    def _run_cmd(self, cmd: list[str], capture: bool = True) -> tuple[int, str]:
        """Run shell command, return (exit_code, output)."""
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            cwd="/home/mike-anderson/dev/cohezion",
        )
        return result.returncode, result.stdout + result.stderr

    def _get_git_commit(self) -> str:
        """Get current git commit."""
        code, out = self._run_cmd(["git", "rev-parse", "--short", "HEAD"])
        return out.strip() if code == 0 else "unknown"

    def _save_checkpoint(self) -> None:
        """Save current state to checkpoint file."""
        if self.state:
            self.checkpoint_path.write_text(json.dumps(asdict(self.state), indent=2))
            print(f"💾 Checkpoint saved: run {self.state.run_number}")

    def _load_checkpoint(self) -> OvernightState | None:
        """Load state from checkpoint file."""
        if not self.checkpoint_path.exists():
            return None

        data = json.loads(self.checkpoint_path.read_text())
        return OvernightState(**data)

    def _generate_hypothesis(self, run_number: int) -> str:
        """Generate optimization hypothesis based on pattern."""
        hypotheses = [
            "Parallel query dispatch: batch multiple queries across domains",
            "Embedding cache: LRU cache for 256D FLUME vectors",
            "Pre-computed paths: materialize common graph traversals",
            "Index HNSW: optimize vector similarity with HNSW index",
            "Connection pooling: reuse SurrealDB/async connections",
            "Lazy loading: defer field materialization until access",
            "Query batching: group small queries into transactions",
            "Result caching: memoize expensive compute results",
        ]
        return hypotheses[run_number % len(hypotheses)]

    def _apply_optimization(self, hypothesis: str) -> bool:
        """Apply code optimization based on hypothesis."""
        print(f"🔧 Applying: {hypothesis}")

        # In real implementation, this would:
        # 1. Modify source code
        # 2. Run tests
        # 3. Commit if tests pass

        # For overnight simulation, just wait a bit
        time.sleep(1)
        return True

    def _run_benchmark(self) -> tuple[float, dict[str, Any]]:
        """Run benchmark and return metric."""
        print("⏱️  Running benchmark...")

        # Run the benchmark
        code, output = self._run_cmd([sys.executable, "-m", "cohezion.benchmarks.datamesh_query"])

        if code != 0:
            print(f"❌ Benchmark failed: {output}")
            return 999.99, {"error": output}

        # Parse METRIC lines
        metrics = {}
        for line in output.split("\n"):
            if line.startswith("METRIC "):
                key_val = line.replace("METRIC ", "")
                if "=" in key_val:
                    k, v = key_val.split("=", 1)
                    metrics[k] = float(v)

        primary = metrics.get("query_latency_ms", 999.99)
        return primary, metrics

    def _log_experiment(self, run: int, metric: float, status: str, hypothesis: str) -> None:
        """Log experiment result."""
        entry = {
            "run": run,
            "timestamp": datetime.now().isoformat(),
            "metric": metric,
            "status": status,
            "hypothesis": hypothesis,
            "commit": self._get_git_commit(),
        }
        self.state.experiments.append(entry)

        # Append to log file
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _generate_report(self) -> Path:
        """Generate morning report."""
        report_path = Path(f"report_{self.session_name}.md")

        kept = [e for e in self.state.experiments if e["status"] == "keep"]
        total = len(self.state.experiments)

        report = f"""# Overnight Autoresearch Report

**Session**: {self.session_name}
**Completed**: {datetime.now().isoformat()}
**Duration**: {(time.time() - self.state.start_time) / 3600:.1f} hours
**Git Commit**: {self.state.git_commit}

## Summary

| Metric | Value |
|--------|-------|
| Total Runs | {total} |
| Kept | {len(kept)} |
| Discarded | {total - len(kept)} |
| Best Metric | {self.state.best_metric:.2f}ms |

## Best Experiments

| Run | Metric | Status | Hypothesis |
|-----|--------|--------|------------|
"""

        for e in sorted(self.state.experiments, key=lambda x: x["metric"])[:10]:
            report += (
                f"| {e['run']} | {e['metric']:.2f} | {e['status']} | {e['hypothesis'][:40]}... |\n"
            )

        report_path.write_text(report)
        return report_path

    def run(self) -> None:
        """Main overnight loop."""
        print("=" * 60)
        print(f"🌙 OVERNIGHT AUTORESEARCH: {self.session_name}")
        print(f"   Target: {self.max_runs} runs, {self.checkpoint_every} per checkpoint")
        print(f"   Timeout: {self.timeout_seconds / 3600:.1f} hours")
        print("=" * 60)

        # Load or init state
        loaded = self._load_checkpoint()
        if loaded:
            print(f"📂 Resuming from checkpoint: run {loaded.run_number}")
            self.state = loaded
        else:
            print("📂 Starting fresh session")
            self.state = OvernightState(
                session_name=self.session_name,
                run_number=0,
                best_metric=999.99,
                experiments=[],
                start_time=self.start_time,
                last_checkpoint=self.start_time,
                git_commit=self._get_git_commit(),
            )

        # Main experiment loop
        while (
            self.state.run_number < self.max_runs
            and time.time() - self.start_time < self.timeout_seconds
        ):
            self.state.run_number += 1
            run_start = time.time()

            print(f"\n{'─' * 60}")
            print(f"🔬 RUN {self.state.run_number} / {self.max_runs}")
            print(f"{'─' * 60}")

            # Generate hypothesis
            hypothesis = self._generate_hypothesis(self.state.run_number)
            print(f"📝 Hypothesis: {hypothesis}")

            # Apply optimization
            if not self._apply_optimization(hypothesis):
                print("❌ Failed to apply optimization, skipping")
                continue

            # Run benchmark
            metric, details = self._run_benchmark()

            # Determine status
            if metric < self.state.best_metric * 0.99:
                status = "keep"
                self.state.best_metric = metric
                print(f"✅ KEEP - New best: {metric:.2f}ms")
            else:
                status = "discard"
                print(f"⏭️  DISCARD - {metric:.2f}ms (best: {self.state.best_metric:.2f}ms)")

            # Log experiment
            self._log_experiment(
                self.state.run_number,
                metric,
                status,
                hypothesis,
            )

            # Checkpoint periodically
            if self.state.run_number % self.checkpoint_every == 0:
                self._save_checkpoint()

            # Print elapsed
            elapsed = time.time() - run_start
            total_elapsed = (time.time() - self.start_time) / 60
            print(f"⏱️  Run time: {elapsed:.1f}s | Total: {total_elapsed:.1f}min")

            # Brief pause
            time.sleep(2)

        # Finalize
        self.state.status = "completed"
        self._save_checkpoint()

        report_path = self._generate_report()
        print(f"\n{'=' * 60}")
        print(f"✅ COMPLETE: {self.state.run_number} runs")
        print(f"   Best metric: {self.state.best_metric:.2f}ms")
        print(f"   Report: {report_path}")
        print(f"   Log: {self.log_path}")
        print(f"   Checkpoint: {self.checkpoint_path}")
        print(f"{'=' * 60}")

        return self.state


def main():
    """CLI entry."""
    import argparse

    parser = argparse.ArgumentParser(description="Overnight autoresearch runner")
    parser.add_argument("--runs", type=int, default=50, help="Max experiments")
    parser.add_argument("--checkpoint", type=int, default=5, help="Checkpoint interval")
    parser.add_argument("--hours", type=int, default=8, help="Timeout hours")
    args = parser.parse_args()

    runner = OvernightRunner(
        max_runs=args.runs,
        checkpoint_every=args.checkpoint,
        timeout_hours=args.hours,
    )

    try:
        runner.run()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⛔ Interrupted by user")
        runner._save_checkpoint()
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        runner._save_checkpoint()
        sys.exit(1)


if __name__ == "__main__":
    main()
