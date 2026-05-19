"""Compound loop telemetry dashboard.

Visualizes pipeline execution metrics from .telemetry/ directory.

Usage:
    uv run python src/cohezion/scripts/telemetry_dashboard.py
    uv run python src/cohezion/scripts/telemetry_dashboard.py --last 10
    uv run python src/cohezion/scripts/telemetry_dashboard.py --request abc-123
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean, median
from typing import Any


TELEMETRY_DIR = Path(".telemetry")


def load_metrics(pattern: str = "*.json") -> list[dict[str, Any]]:
    """Load all telemetry metrics."""
    if not TELEMETRY_DIR.exists():
        print(f"Telemetry directory not found: {TELEMETRY_DIR}")
        return []

    files = sorted(TELEMETRY_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

    metrics = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            metrics.append(data)
        except Exception as _e:
            print(f"Warning: skipping {f}: {_e}", file=sys.stderr)
            continue

    return metrics


def print_dashboard(metrics: list[dict[str, Any]], limit: int = 20) -> None:
    """Print formatted dashboard."""
    if not metrics:
        print("No telemetry data found.")
        print("Run: make test-smoke && .telemetry/ will be populated")
        return

    recent = metrics[:limit]

    print("=" * 80)
    print("COMPOUND LOOP TELEMETRY DASHBOARD")
    print("=" * 80)
    print(f"\nRecent Pipelines (last {len(recent)}):")
    print("-" * 80)
    print(
        f"{'Request ID':<20} {'Skill':<25} {'Status':<8} {'Latency':<10} {'Tokens':<12} {'Steps'}"
    )
    print("-" * 80)

    for m in recent:
        status = "✓" if m.get("success") else "✗"
        latency = f"{m.get('total_latency_ms', 0):.0f}ms"
        tokens = m.get("total_tokens_in", 0) + m.get("total_tokens_out", 0)
        tokens_str = f"{tokens:,}" if tokens else "N/A"
        skill = m.get("skill_name", "")[:24]
        steps = f"{m.get('steps_count', 0)}/11"

        print(
            f"{m['request_id']:<20} {skill:<25} {status:<8} {latency:<10} {tokens_str:<12} {steps}"
        )

    # Aggregates
    successful = [m for m in metrics if m.get("success")]
    if successful:
        latencies = [m.get("total_latency_ms", 0) for m in successful]
        token_counts = [
            m.get("total_tokens_in", 0) + m.get("total_tokens_out", 0) for m in successful
        ]

        print("\n" + "=" * 80)
        print(f"AGGREGATES (last {len(successful)} successful runs)")
        print("-" * 80)
        print(
            f"Total successful runs: {len(successful)}/{len(metrics)} ({100 * len(successful) // len(metrics)}%)"
        )
        print(f"Latency - Mean: {mean(latencies):.0f}ms, Median: {median(latencies):.0f}ms")
        print(f"Tokens  - Mean: {mean(token_counts):,.0f}, Median: {median(token_counts):,.0f}")
        print(f"Total tokens consumed: {sum(token_counts):,}")

    # Step breakdown
    print("\n" + "=" * 80)
    print("STEP PERFORMANCE (averages)")
    print("-" * 80)

    step_latencies: dict[str, list[float]] = {}
    for m in successful:
        for step in m.get("steps", []):
            name = step.get("step_name", "unknown")
            step_latencies.setdefault(name, []).append(step.get("latency_ms", 0))

    if step_latencies:
        for name, latencies in sorted(step_latencies.items()):
            avg = mean(latencies)
            count = len(latencies)
            print(f"  {name:<25} {avg:>8.1f}ms  ({count} runs)")

    print("=" * 80)


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Compound Loop Telemetry Dashboard")
    parser.add_argument("--last", type=int, default=20, help="Show last N pipelines")
    parser.add_argument("--request", type=str, help="Show details for specific request ID")
    args = parser.parse_args()

    if args.request:
        metrics = load_metrics(f"*{args.request}*.json")
        if not metrics:
            print(f"No metrics found for request: {args.request}")
            return 1
        # Print detailed view
        m = metrics[0]
        print(json.dumps(m, indent=2))
    else:
        metrics = load_metrics()
        print_dashboard(metrics, limit=args.last)

    return 0


if __name__ == "__main__":
    sys.exit(main())
