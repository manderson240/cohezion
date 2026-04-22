"""Benchmark vault_backlinks operation."""

import re
from pathlib import Path

from benchmarks.benchmark_utils import BenchmarkResult, run_benchmark


def run() -> BenchmarkResult:
    """Benchmark vault backlinks performance.

    Setup: Random paper with ~10 incoming links
    Measure: Time to scan all 84 papers for backlinks
    Iterations: 5 runs
    """
    vault_path = Path(__file__).parent.parent / "vault"

    if not vault_path.exists():
        return BenchmarkResult(
            operation="vault_backlinks",
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
            operation="vault_backlinks",
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

    # Pick first paper as target for backlink search
    paper_files = list(papers_dir.glob("*.md"))
    if not paper_files:
        return BenchmarkResult(
            operation="vault_backlinks",
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

    target_paper = paper_files[0].stem

    def backlinks_operation() -> None:
        """Scan all papers for backlinks to target paper."""
        wiki_link_pattern = r"\[\[([^\]]+)\]\]"
        target_normalized = target_paper.lower().replace("_", " ")

        for paper_file in papers_dir.glob("*.md"):
            if paper_file.stem == target_paper:
                continue

            try:
                content = paper_file.read_text(encoding="utf-8", errors="ignore")
                matches = re.findall(wiki_link_pattern, content)

                for match in matches:
                    if match.lower().replace("_", " ") == target_normalized:
                        pass  # Found a backlink
            except Exception:
                pass

    return run_benchmark(
        name="vault_backlinks",
        func=backlinks_operation,
        iterations=5,
        warmup=1,
    )


if __name__ == "__main__":
    result = run()
    print(f"vault_backlinks: {result.mean_ms:.1f}ms (±{result.stddev_ms:.1f}ms)")
