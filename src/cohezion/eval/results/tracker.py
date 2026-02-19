"""Results tracker for all benchmark evaluations.

Tracks benchmark performance over time across SWE-bench, HumanEval, AgentBench.
Provides dashboard and trend analysis.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


class BenchmarkTracker:
    """Tracks benchmark results over time.

    Maintains historical data across:
    - SWE-bench (resolution rate)
    - HumanEval (pass@k)
    - AgentBench (success rate per environment)

    Provides trend analysis and dashboard generation.
    """

    def __init__(self, data_dir: str = "data/eval/results"):
        """Initialize tracker.

        Args:
            data_dir: Directory for benchmark history
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "benchmark_history.json"

        self._history: dict[str, Any] | None = None

    def _load_history(self) -> dict[str, Any]:
        """Load historical benchmark data."""
        if self._history is not None:
            return self._history

        if self.history_file.exists():
            with open(self.history_file) as f:
                self._history = json.load(f)
        else:
            self._history = {
                "swebench": [],
                "humaneval": [],
                "agentbench": [],
                "created_at": datetime.now().isoformat(),
            }

        return self._history

    def _save_history(self) -> None:
        """Save benchmark history."""
        with open(self.history_file, "w") as f:
            json.dump(self._history, f, indent=2)

    def record_swebench(
        self,
        model_name: str,
        resolution_rate: float,
        dataset: str,
        details: dict[str, Any],
    ) -> None:
        """Record SWE-bench results.

        Args:
            model_name: Model identifier
            resolution_rate: Fraction of issues resolved
            dataset: Dataset name (lite, verified, full)
            details: Additional result details
        """
        history = self._load_history()

        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "resolution_rate": resolution_rate,
            "dataset": dataset,
            "details": details,
        }

        history["swebench"].append(entry)
        self._save_history()

        logger.info(f"SWE-bench: {model_name} - {resolution_rate:.1%} on {dataset}")

    def record_humaneval(
        self,
        model_name: str,
        pass_at_k: dict[str, float],
        details: dict[str, Any],
    ) -> None:
        """Record HumanEval results.

        Args:
            model_name: Model identifier
            pass_at_k: Dict with pass@1, pass@10, pass@100
            details: Additional result details
        """
        history = self._load_history()

        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "pass_at_k": pass_at_k,
            "details": details,
        }

        history["humaneval"].append(entry)
        self._save_history()

        logger.info(
            f"HumanEval: {model_name} - "
            f"pass@1: {pass_at_k.get('pass@1', 0):.1%}, "
            f"pass@10: {pass_at_k.get('pass@10', 0):.1%}"
        )

    def record_agentbench(
        self,
        model_name: str,
        overall_rate: float,
        per_environment: dict[str, float],
        details: dict[str, Any],
    ) -> None:
        """Record AgentBench results.

        Args:
            model_name: Model identifier
            overall_rate: Overall success rate
            per_environment: Per-environment success rates
            details: Additional result details
        """
        history = self._load_history()

        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "overall_rate": overall_rate,
            "per_environment": per_environment,
            "details": details,
        }

        history["agentbench"].append(entry)
        self._save_history()

        logger.info(f"AgentBench: {model_name} - {overall_rate:.1%} overall")

    def get_trends(self, benchmark: str, days: int = 30) -> dict[str, Any]:
        """Get performance trends over time.

        Args:
            benchmark: 'swebench', 'humaneval', or 'agentbench'
            days: Number of days to analyze

        Returns:
            Trend analysis with improvement metrics
        """
        history = self._load_history()
        entries = history.get(benchmark, [])

        if not entries:
            return {"error": f"No data for {benchmark}"}

        # Filter to recent entries
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        recent = [
            e
            for e in entries
            if datetime.fromisoformat(e["timestamp"]).timestamp() > cutoff
        ]

        if len(recent) < 2:
            return {"error": "Not enough data for trend analysis"}

        # Calculate trends based on benchmark type
        if benchmark == "swebench":
            rates = [e["resolution_rate"] for e in recent]
            metric_name = "resolution_rate"
        elif benchmark == "humaneval":
            rates = [e["pass_at_k"]["pass@1"] for e in recent]
            metric_name = "pass@1"
        else:  # agentbench
            rates = [e["overall_rate"] for e in recent]
            metric_name = "overall_rate"

        return {
            "benchmark": benchmark,
            "metric": metric_name,
            "data_points": len(rates),
            "latest": rates[-1],
            "earliest": rates[0],
            "improvement": rates[-1] - rates[0],
            "mean": np.mean(rates),
            "std": np.std(rates),
            "trend": "improving" if rates[-1] > rates[0] else "declining",
        }

    def compare_with_baselines(self, model_name: str) -> dict[str, Any]:
        """Compare current results with published baselines.

        Args:
            model_name: Model to compare

        Returns:
            Comparison results
        """
        history = self._load_history()

        # Get latest results for this model
        comparisons = {}

        # SWE-bench comparison
        swebench_entries = [
            e for e in history.get("swebench", []) if e["model"] == model_name
        ]
        if swebench_entries:
            latest = swebench_entries[-1]
            comparisons["swebench"] = {
                "our_result": latest["resolution_rate"],
                "baseline_gpt4": 0.20,  # Approximate
                "baseline_claude": 0.18,  # Approximate
                "comparison": "above" if latest["resolution_rate"] > 0.15 else "below",
            }

        # HumanEval comparison
        humaneval_entries = [
            e for e in history.get("humaneval", []) if e["model"] == model_name
        ]
        if humaneval_entries:
            latest = humaneval_entries[-1]
            pass_1 = latest["pass_at_k"].get("pass@1", 0)
            comparisons["humaneval"] = {
                "our_result": pass_1,
                "baseline_codex": 0.288,
                "baseline_gpt4": 0.88,
                "comparison": "above_codex" if pass_1 > 0.288 else "below",
            }

        return comparisons

    def generate_dashboard(self) -> str:
        """Generate markdown dashboard of benchmark results.

        Returns:
            Markdown content
        """
        history = self._load_history()

        dashboard = """# Cohezion Benchmark Dashboard

## Overview

This dashboard tracks benchmark performance over time.

## SWE-bench

| Model | Dataset | Resolution Rate | Date |
|-------|---------|----------------|------|
"""

        for entry in history.get("swebench", [])[-10:]:  # Last 10
            dashboard += (
                f"| {entry['model']} | {entry['dataset']} | "
                f"{entry['resolution_rate']:.1%} | "
                f"{entry['timestamp'][:10]} |\n"
            )

        dashboard += """
## HumanEval

| Model | pass@1 | pass@10 | pass@100 | Date |
|-------|--------|---------|----------|------|
"""

        for entry in history.get("humaneval", [])[-10:]:
            pak = entry["pass_at_k"]
            dashboard += (
                f"| {entry['model']} | "
                f"{pak.get('pass@1', 0):.1%} | "
                f"{pak.get('pass@10', 0):.1%} | "
                f"{pak.get('pass@100', 0):.1%} | "
                f"{entry['timestamp'][:10]} |\n"
            )

        dashboard += """
## AgentBench

| Model | Overall | OS | DB | Web | Date |
|-------|---------|----|----|-----|------|
"""

        for entry in history.get("agentbench", [])[-10:]:
            per_env = entry.get("per_environment", {})
            dashboard += (
                f"| {entry['model']} | "
                f"{entry['overall_rate']:.1%} | "
                f"{per_env.get('os', 0):.1%} | "
                f"{per_env.get('db', 0):.1%} | "
                f"{per_env.get('ws', 0):.1%} | "
                f"{entry['timestamp'][:10]} |\n"
            )

        dashboard += """
## Trends

"""

        for benchmark in ["swebench", "humaneval", "agentbench"]:
            trends = self.get_trends(benchmark, days=30)
            if "error" not in trends:
                dashboard += (
                    f"### {benchmark.upper()}\n"
                    f"- Latest: {trends['latest']:.1%}\n"
                    f"- Trend: {trends['trend']}\n"
                    f"- Improvement: {trends['improvement']:+.1%}\n\n"
                )

        # Save dashboard
        dashboard_path = self.data_dir / "benchmark_dashboard.md"
        with open(dashboard_path, "w") as f:
            f.write(dashboard)

        return dashboard

    def get_summary(self) -> dict[str, Any]:
        """Get quick summary of all benchmarks."""
        history = self._load_history()

        return {
            "total_runs": (
                len(history.get("swebench", []))
                + len(history.get("humaneval", []))
                + len(history.get("agentbench", []))
            ),
            "swebench_runs": len(history.get("swebench", [])),
            "humaneval_runs": len(history.get("humaneval", [])),
            "agentbench_runs": len(history.get("agentbench", [])),
            "latest_update": max(
                [e["timestamp"] for e in history.get("swebench", [])]
                + [e["timestamp"] for e in history.get("humaneval", [])]
                + [e["timestamp"] for e in history.get("agentbench", [])],
                default=None,
            ),
        }
