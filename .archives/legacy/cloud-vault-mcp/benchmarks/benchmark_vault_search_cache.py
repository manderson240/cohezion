"""Benchmark vault search caching performance."""

from pathlib import Path

from benchmarks.benchmark_utils import BenchmarkResult, run_benchmark
from mcp_server.vault_ops import VaultOps


def run() -> BenchmarkResult:
    """Benchmark vault search performance with and without cache.

    Setup: 84 papers in vault
    Measure: Time to complete repeated searches ("machine learning")
    Iterations: 10 runs
    Expected: 5-10x speedup from cache hits
    """
    vault_path = Path(__file__).parent.parent / "vault"

    if not vault_path.exists():
        # Return a dummy result if vault doesn't exist
        return BenchmarkResult(
            operation="vault_search_cache",
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

    papers_dir = vault_path / "papers"
    if not papers_dir.exists():
        return BenchmarkResult(
            operation="vault_search_cache",
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

    vault_ops = VaultOps(str(vault_path), cache_enabled=True, cache_ttl_seconds=60)

    def repeated_search_operation() -> None:
        """Perform vault search multiple times on same query (cache hits)."""
        # First search populates cache
        vault_ops.search("machine learning")
        # Subsequent searches are cache hits
        vault_ops.search("machine learning")
        vault_ops.search("machine learning")

    return run_benchmark(
        name="vault_search_cache",
        func=repeated_search_operation,
        iterations=10,
        warmup=1,
    )


if __name__ == "__main__":
    result = run()
    stats = result.to_dict()
    print(f"vault_search_cache: {result.mean_ms:.3f}ms (±{result.stddev_ms:.3f}ms)")
    print(f"  p95: {result.p95_ms:.3f}ms, p99: {result.p99_ms:.3f}ms")
    print(f"  error_rate: {result.error_rate:.0%}")
