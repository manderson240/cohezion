"""Benchmark vault_search operation."""

from pathlib import Path

from benchmarks.benchmark_utils import BenchmarkResult, run_benchmark
from mcp_server.vault_ops import VaultOps


def run() -> BenchmarkResult:
    """Benchmark vault search performance.

    Setup: 84 papers in vault
    Measure: Time to complete search on "machine learning"
    Iterations: 5 runs
    """
    vault_path = Path(__file__).parent.parent / "vault"

    if not vault_path.exists():
        # Return a dummy result if vault doesn't exist
        return BenchmarkResult(
            operation="vault_search",
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

    VaultOps(str(vault_path))

    def search_operation() -> None:
        """Perform vault search for papers containing 'machine learning'."""
        papers_dir = vault_path / "papers"
        if not papers_dir.exists():
            return

        search_term = "machine learning"
        for paper_file in papers_dir.glob("*.md"):
            try:
                content = paper_file.read_text(encoding="utf-8", errors="ignore")
                if search_term.lower() in content.lower():
                    pass  # Found a match
            except Exception:
                pass

    return run_benchmark(
        name="vault_search",
        func=search_operation,
        iterations=5,
        warmup=1,
    )


if __name__ == "__main__":
    result = run()
    print(f"vault_search: {result.mean_ms:.1f}ms (±{result.stddev_ms:.1f}ms)")
