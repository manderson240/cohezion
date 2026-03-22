"""Benchmark SurrealDB parallel sync performance.

Compares sequential vs parallel bulk import approaches and measures
improvements in throughput and latency.
"""

import json
from pathlib import Path
from typing import Any

from benchmarks.benchmark_utils import BenchmarkResult, run_benchmark


def run_sequential_benchmark() -> BenchmarkResult:
    """Benchmark sequential SurrealDB sync.

    Simulates reading and syncing papers sequentially.
    """
    # Try real vault first, fall back to test vault
    vault_path = Path("/home/mike-anderson/vaults/cohezion-vault")
    if not vault_path.exists():
        vault_path = Path(__file__).parent.parent / "vault"
    papers_dir = vault_path / "papers"

    if not papers_dir.exists():
        return BenchmarkResult(
            operation="surrealdb_sync_sequential",
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
    len(paper_files)

    def sync_operation() -> None:
        """Simulate sequential SurrealDB sync of papers."""
        for paper_file in paper_files:
            try:
                content = paper_file.read_text(encoding="utf-8", errors="ignore")

                # Extract frontmatter
                if content.startswith("---"):
                    try:
                        _, frontmatter_str, _ = content.split("---", 2)
                    except ValueError:
                        continue

                    # Simulate SurrealDB operation
                    _ = {
                        "file": paper_file.stem,
                        "frontmatter": frontmatter_str[:100],
                    }
            except Exception:
                pass

    result = run_benchmark(
        name="surrealdb_sync_sequential",
        func=sync_operation,
        iterations=1,
        warmup=0,
    )

    return result


def run_parallel_simulation_benchmark() -> BenchmarkResult:
    """Benchmark parallel sync simulation.

    Simulates concurrent file processing with asyncio-like overhead.
    In real scenario, this would measure actual async HTTP operations.
    """
    # Try real vault first, fall back to test vault
    vault_path = Path("/home/mike-anderson/vaults/cohezion-vault")
    if not vault_path.exists():
        vault_path = Path(__file__).parent.parent / "vault"
    papers_dir = vault_path / "papers"

    if not papers_dir.exists():
        return BenchmarkResult(
            operation="surrealdb_sync_parallel",
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
        """Simulate parallel processing of papers."""
        import asyncio

        async def process_paper(paper_file: Path) -> None:
            try:
                content = paper_file.read_text(encoding="utf-8", errors="ignore")
                if content.startswith("---"):
                    try:
                        _, frontmatter_str, _ = content.split("---", 2)
                    except ValueError:
                        return

                    _ = {
                        "file": paper_file.stem,
                        "frontmatter": frontmatter_str[:100],
                    }
                    # Simulate async work
                    await asyncio.sleep(0.0001)
            except Exception:
                pass

        async def main() -> None:
            # Simulate max_concurrent=10
            semaphore = asyncio.Semaphore(10)

            async def sem_process(paper: Path) -> None:
                async with semaphore:
                    await process_paper(paper)

            tasks = [sem_process(p) for p in paper_files]
            await asyncio.gather(*tasks)

        asyncio.run(main())

    result = run_benchmark(
        name="surrealdb_sync_parallel",
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
        "status": "PASS"
        if speedup >= 1.5
        else "CHECK"
        if speedup >= 1.0
        else "NEEDS_INVESTIGATION",
    }


def run() -> dict[str, Any]:
    """Run parallel sync benchmarks and comparisons.

    Returns:
        Dictionary with results and comparison
    """
    sequential = run_sequential_benchmark()
    parallel = run_parallel_simulation_benchmark()
    comparison = compare_results(sequential, parallel)

    return {
        "sequential": sequential.to_dict(),
        "parallel": parallel.to_dict(),
        "comparison": comparison,
    }


if __name__ == "__main__":
    print("Running SurrealDB parallel sync benchmarks...")
    print("=" * 70)

    results = run()

    seq_result = results["sequential"]
    par_result = results["parallel"]
    comp = results["comparison"]

    paper_count = 84

    print("\nSequential Sync:")
    print(f"  Total: {seq_result['mean_ms']:.1f}ms")
    print(f"  Per paper: {seq_result['mean_ms'] / paper_count:.3f}ms")
    print(f"  Samples: {seq_result['samples']}")

    print("\nParallel Sync (max_concurrent=10):")
    print(f"  Total: {par_result['mean_ms']:.1f}ms")
    print(f"  Per paper: {par_result['mean_ms'] / paper_count:.3f}ms")
    print(f"  Samples: {par_result['samples']}")

    print("\nComparison:")
    print(f"  Improvement: {comp['improvement_ms']}ms ({comp['improvement_percent']}%)")
    print(f"  Speedup: {comp['speedup_factor']}x")
    print(f"  Status: {comp['status']}")

    print("\n" + "=" * 70)
    print("Full results saved to: benchmark_surrealdb_parallel_results.json")

    # Save results
    with open("benchmark_surrealdb_parallel_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Benchmarks complete!")
