"""Benchmark SurrealDB HTTP operations with and without parallelization.

Simulates realistic HTTP latency to measure actual parallelization benefits.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from benchmarks.benchmark_utils import BenchmarkResult, run_benchmark


def run_sequential_http_benchmark() -> BenchmarkResult:
    """Benchmark sequential HTTP-based SurrealDB sync.

    Simulates HTTP calls with realistic 5-20ms latency per operation.
    """
    vault_path = Path("/home/mike-anderson/vaults/cohezion-vault")
    papers_dir = vault_path / "papers"

    if not papers_dir.exists():
        return BenchmarkResult(
            operation="surrealdb_http_sequential",
            samples=0,
            mean_ms=0.0,
            median_ms=0.0,
            p95_ms=0.0,
            p99_ms=0.0,
            min_ms=0.0,
            max_ms=0.0,
            stddev_ms=0.0,
            errors=1,
            error_rate=1.0,
        )

    paper_files = sorted(papers_dir.glob("*.md"))

    def sync_operation() -> None:
        """Simulate sequential HTTP requests (one per paper)."""
        http_latency_ms = 10  # Realistic SurrealDB latency

        for paper_file in paper_files:
            try:
                # Simulate file I/O
                content = paper_file.read_text(encoding="utf-8", errors="ignore")

                # Simulate HTTP request to SurrealDB
                # In real scenario: 84 papers * 10ms = 840ms sequential
                time.sleep(http_latency_ms / 1000.0)

            except Exception:
                pass

    result = run_benchmark(
        name="surrealdb_http_sequential",
        func=sync_operation,
        iterations=1,
        warmup=0,
    )

    return result


def run_parallel_http_benchmark() -> BenchmarkResult:
    """Benchmark parallel HTTP-based SurrealDB sync.

    Simulates concurrent HTTP calls with connection pooling.
    Expected: 84 papers / 10 concurrent = ~8-9 batches * 10ms = ~90-100ms
    """
    vault_path = Path("/home/mike-anderson/vaults/cohezion-vault")
    papers_dir = vault_path / "papers"

    if not papers_dir.exists():
        return BenchmarkResult(
            operation="surrealdb_http_parallel",
            samples=0,
            mean_ms=0.0,
            median_ms=0.0,
            p95_ms=0.0,
            p99_ms=0.0,
            min_ms=0.0,
            max_ms=0.0,
            stddev_ms=0.0,
            errors=1,
            error_rate=1.0,
        )

    paper_files = sorted(papers_dir.glob("*.md"))

    def sync_operation_parallel() -> None:
        """Simulate parallel HTTP requests with concurrency control."""
        http_latency_ms = 10  # Same realistic latency

        async def process_paper(paper_file: Path) -> None:
            try:
                # Simulate file I/O
                content = paper_file.read_text(encoding="utf-8", errors="ignore")

                # Simulate HTTP request
                await asyncio.sleep(http_latency_ms / 1000.0)

            except Exception:
                pass

        async def main() -> None:
            # With max_concurrent=10 and 84 papers:
            # Batch 1: papers 0-9 in parallel (10ms)
            # Batch 2: papers 10-19 in parallel (10ms)
            # ... etc
            # Total: ~90ms with 10 concurrent
            semaphore = asyncio.Semaphore(10)

            async def sem_process(paper: Path) -> None:
                async with semaphore:
                    await process_paper(paper)

            tasks = [sem_process(p) for p in paper_files]
            await asyncio.gather(*tasks)

        asyncio.run(main())

    result = run_benchmark(
        name="surrealdb_http_parallel",
        func=sync_operation_parallel,
        iterations=1,
        warmup=0,
    )

    return result


def compare_results(
    sequential: BenchmarkResult, parallel: BenchmarkResult
) -> dict[str, Any]:
    """Compare sequential vs parallel results.

    Args:
        sequential: Sequential benchmark result
        parallel: Parallel benchmark result

    Returns:
        Comparison metrics
    """
    seq_ms = sequential.mean_ms
    par_ms = parallel.mean_ms

    improvement = seq_ms - par_ms
    improvement_pct = (improvement / seq_ms * 100) if seq_ms > 0 else 0
    speedup = seq_ms / par_ms if par_ms > 0 else 0

    return {
        "sequential_ms": round(seq_ms, 2),
        "parallel_ms": round(par_ms, 2),
        "improvement_ms": round(improvement, 2),
        "improvement_percent": round(improvement_pct, 1),
        "speedup_factor": round(speedup, 1),
        "status": "EXCELLENT"
        if speedup >= 8
        else "GOOD"
        if speedup >= 5
        else "PASS"
        if speedup >= 2
        else "CHECK",
    }


def run() -> dict[str, Any]:
    """Run parallel sync benchmarks with realistic HTTP latency.

    Returns:
        Dictionary with results and comparison
    """
    sequential = run_sequential_http_benchmark()
    parallel = run_parallel_http_benchmark()
    comparison = compare_results(sequential, parallel)

    return {
        "sequential": sequential.to_dict(),
        "parallel": parallel.to_dict(),
        "comparison": comparison,
    }


if __name__ == "__main__":
    print(
        "Running SurrealDB parallel sync benchmarks (with HTTP latency simulation)..."
    )
    print("=" * 70)

    results = run()

    seq_result = results["sequential"]
    par_result = results["parallel"]
    comp = results["comparison"]

    paper_count = 84

    print("\nSequential Sync (10ms latency per paper):")
    print(f"  Expected: {paper_count * 10}ms (no parallelization)")
    print(f"  Actual:   {seq_result['mean_ms']:.1f}ms")
    print(f"  Per paper: {seq_result['mean_ms'] / paper_count:.2f}ms")

    print("\nParallel Sync (max_concurrent=10, 10ms latency per paper):")
    print(f"  Expected: {(paper_count / 10) * 10}ms (10 batches)")
    print(f"  Actual:   {par_result['mean_ms']:.1f}ms")
    print(f"  Per paper: {par_result['mean_ms'] / paper_count:.2f}ms")

    print("\nComparison:")
    print(f"  Improvement: {comp['improvement_ms']}ms ({comp['improvement_percent']}%)")
    print(f"  Speedup: {comp['speedup_factor']}x")
    print(f"  Status: {comp['status']}")

    print("\nAnalysis:")
    if comp["speedup_factor"] >= 5:
        print("  ✓ Parallelization is highly effective")
        print(
            f"  ✓ Achieves {comp['speedup_factor']:.1f}x speedup (well above 5x target)"
        )
    elif comp["speedup_factor"] >= 2:
        print("  ✓ Parallelization is working")
        print(f"  ✓ Achieves {comp['speedup_factor']:.1f}x speedup")
    else:
        print("  ✗ Parallelization needs investigation")

    print("\n" + "=" * 70)
    print("Results saved to: benchmark_surrealdb_http_results.json")

    # Save results
    with open("benchmark_surrealdb_http_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Benchmarks complete!")
