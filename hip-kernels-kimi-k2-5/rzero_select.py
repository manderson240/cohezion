#!/usr/bin/env python3
"""R-Zero Selection: Select top performers from challenger pool.

Implements tournament selection and evolutionary pressure.
"""

import json
import sys
from pathlib import Path


sys.path.insert(0, "/home/mike-anderson/dev/cohezion/hip-kernels-kimi-k2-5")


def load_results(results_file: Path) -> list[dict]:
    """Load evaluation results."""
    if not results_file.exists():
        return []
    with open(results_file) as f:
        return json.load(f)


def select_top_performers(results: list[dict], kernel: str, top_percent: float = 20) -> list[dict]:
    """Select top N% performers for a kernel."""
    kernel_results = [r for r in results if r["kernel"] == kernel and r["correct"]]
    if not kernel_results:
        return []

    # Sort by speedup descending
    sorted_results = sorted(kernel_results, key=lambda x: x["speedup"], reverse=True)

    # Select top N%
    n_select = max(1, int(len(sorted_results) * top_percent / 100))
    return sorted_results[:n_select]


def select_by_tournament(results: list[dict], kernel: str, num_select: int = 4) -> list[dict]:
    """Tournament selection: randomly pair challengers, select winners."""
    import random

    kernel_results = [r for r in results if r["kernel"] == kernel and r["correct"]]
    if len(kernel_results) < 2:
        return kernel_results

    selected = []
    for _ in range(num_select):
        if len(kernel_results) < 2:
            break
        # Random tournament
        c1, c2 = random.sample(kernel_results, 2)
        winner = c1 if c1["speedup"] > c2["speedup"] else c2
        selected.append(winner)

    return selected


def get_population_stats(results: list[dict], kernel: str) -> dict:
    """Get statistics for a kernel population."""
    kernel_results = [r for r in results if r["kernel"] == kernel]
    if not kernel_results:
        return {}

    correct = [r for r in kernel_results if r["correct"]]
    speedups = [r["speedup"] for r in correct]

    return {
        "total": len(kernel_results),
        "correct": len(correct),
        "best_speedup": max(speedups) if speedups else 0,
        "avg_speedup": sum(speedups) / len(speedups) if speedups else 0,
        "median_speedup": sorted(speedups)[len(speedups) // 2] if speedups else 0,
    }


def main():
    """Run selection on evaluated challengers."""
    results_file = Path(
        "/home/mike-anderson/dev/cohezion/hip-kernels-kimi-k2-5/rzero-results/results.json"
    )

    if not results_file.exists():
        print("No results file found. Run evaluation first.")
        return

    results = load_results(results_file)

    print("R-Zero Selection Results")
    print("=" * 60)

    for kernel in ["gemm", "moe", "mla"]:
        stats = get_population_stats(results, kernel)
        if not stats:
            continue

        print(f"\n{kernel.upper()} Population:")
        print(f"  Total: {stats['total']}, Correct: {stats['correct']}")
        print(f"  Best speedup: {stats['best_speedup']:.2f}x")
        print(f"  Avg speedup: {stats['avg_speedup']:.2f}x")
        print(f"  Median speedup: {stats['median_speedup']:.2f}x")

        # Select top performers
        top = select_top_performers(results, kernel, top_percent=20)
        print(f"  Top 20% ({len(top)} challengers):")
        for i, r in enumerate(top[:5], 1):
            print(f"    {i}. {r['file']}: {r['speedup']:.2f}x")


if __name__ == "__main__":
    main()
