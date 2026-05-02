"""Benchmark SurrealDB bulk sync operation."""

from pathlib import Path

from benchmarks.benchmark_utils import BenchmarkResult, run_benchmark


def run() -> BenchmarkResult:
    """Benchmark SurrealDB sync performance.

    Setup: 84 papers with 148 links (already loaded)
    Measure: Time to re-sync all papers (current sequential approach)
    Iterations: 1 run (slow operation)
    Output: Total time + time per paper
    """
    vault_path = Path(__file__).parent.parent / "vault"

    if not vault_path.exists():
        return BenchmarkResult(
            operation="surrealdb_sync",
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
            operation="surrealdb_sync",
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

    def sync_operation() -> None:
        """Simulate sequential SurrealDB sync of papers.

        This simulates reading each paper's metadata and syncing to SurrealDB.
        In a real scenario, this would make HTTP calls to SurrealDB.
        """
        for paper_file in papers_dir.glob("*.md"):
            try:
                content = paper_file.read_text(encoding="utf-8", errors="ignore")

                # Extract frontmatter
                if content.startswith("---"):
                    _, frontmatter_str, _ = content.split("---", 2)
                    # Parse YAML-like frontmatter (simplified)
                    lines = frontmatter_str.strip().split("\n")
                    metadata = {}
                    for line in lines:
                        if ":" in line:
                            key, value = line.split(":", 1)
                            metadata[key.strip()] = value.strip()

                    # Simulate SurrealDB operation (just in-memory)
                    _ = {
                        "file": paper_file.stem,
                        "metadata": metadata,
                    }
            except Exception:
                pass

    return run_benchmark(
        name="surrealdb_sync",
        func=sync_operation,
        iterations=1,
        warmup=0,
    )


if __name__ == "__main__":
    result = run()
    paper_count = 84
    time_per_paper = result.mean_ms / paper_count if paper_count > 0 else 0
    print(
        f"surrealdb_sync: {result.mean_ms:.1f}ms total "
        f"({time_per_paper:.2f}ms per paper)"
    )
