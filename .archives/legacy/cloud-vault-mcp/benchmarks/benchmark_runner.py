#!/usr/bin/env python3
"""Comprehensive benchmark runner for cloud-vault-mcp performance validation."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


try:
    from benchmarks import (
        benchmark_ollama_inference,
        benchmark_sheets_api,
        benchmark_surrealdb_sync,
        benchmark_vault_backlinks,
        benchmark_vault_search,
        benchmark_vault_search_cache,
    )
except ImportError:
    # Allow running from project root
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from benchmarks import (
        benchmark_ollama_inference,
        benchmark_sheets_api,
        benchmark_surrealdb_sync,
        benchmark_vault_backlinks,
        benchmark_vault_search,
        benchmark_vault_search_cache,
    )


def run_all_benchmarks(output_file: str | None = None) -> dict:
    """Run all benchmarks and save results.

    Args:
        output_file: Optional path to save JSON results

    Returns:
        Dictionary with all benchmark results
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "benchmarks": [],
    }

    benchmarks = [
        ("vault_search", benchmark_vault_search.run),
        ("vault_search_cache", benchmark_vault_search_cache.run),
        ("vault_backlinks", benchmark_vault_backlinks.run),
        ("surrealdb_sync", benchmark_surrealdb_sync.run),
        ("sheets_api", benchmark_sheets_api.run),
        ("ollama_inference", benchmark_ollama_inference.run),
    ]

    print("Running benchmarks...")
    for name, benchmark_func in benchmarks:
        print(f"  - {name}...", end="", flush=True)
        try:
            result = benchmark_func()
            results["benchmarks"].append(result.to_dict())
            print(
                f" {result.mean_ms:.1f}ms (p95: {result.p95_ms:.1f}ms, error_rate: {result.error_rate:.0%})"
            )
        except Exception as e:
            print(f" ERROR: {e}")
            results["benchmarks"].append(
                {
                    "operation": name,
                    "error": str(e),
                }
            )

    # Save results if output file specified
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to {output_file}")

    return results


def compare_benchmarks(baseline_file: str, current_file: str) -> None:
    """Compare current results to baseline.

    Args:
        baseline_file: Path to baseline JSON results
        current_file: Path to current JSON results
    """
    baseline_path = Path(baseline_file)
    current_path = Path(current_file)

    if not baseline_path.exists():
        print(f"ERROR: Baseline file not found: {baseline_file}")
        sys.exit(1)

    if not current_path.exists():
        print(f"ERROR: Current file not found: {current_file}")
        sys.exit(1)

    baseline = json.loads(baseline_path.read_text())
    current = json.loads(current_path.read_text())

    print("\nBenchmark Comparison (baseline → current):")
    print("-" * 70)

    for base, curr in zip(baseline["benchmarks"], current["benchmarks"], strict=False):
        name = base.get("operation", "unknown")

        # Handle error cases
        if "error" in base or "error" in curr:
            print(f"  {name}: ERROR")
            continue

        base_mean = base.get("mean_ms", 0)
        curr_mean = curr.get("mean_ms", 0)

        if base_mean == 0:
            multiplier = 0
            status = "N/A"
        elif curr_mean == 0:
            multiplier = 0
            status = "ERROR"
        else:
            multiplier = base_mean / curr_mean

            if multiplier > 1.1:
                status = "✓ FASTER"
            elif multiplier < 0.9:
                status = "✗ SLOWER"
            else:
                status = "≈ SAME"

        print(
            f"  {name:20s}: {base_mean:7.1f}ms → {curr_mean:7.1f}ms ({multiplier:5.2f}x) {status}"
        )

    print("-" * 70)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark runner for cloud-vault-mcp performance validation"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for JSON results",
    )
    parser.add_argument(
        "--compare",
        type=str,
        default=None,
        help="Baseline file to compare against",
    )

    args = parser.parse_args()

    if args.compare:
        # Compare mode: run current benchmarks and compare to baseline
        current_file = args.output or "current_results.json"
        run_all_benchmarks(output_file=current_file)
        compare_benchmarks(args.compare, current_file)
    else:
        # Normal mode: just run benchmarks
        run_all_benchmarks(output_file=args.output)


if __name__ == "__main__":
    main()
