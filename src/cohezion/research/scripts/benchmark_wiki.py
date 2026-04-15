#!/usr/bin/env python3
"""Benchmark script for LLM-Wiki integration performance.

Metrics:
- ingest_latency_ms: Time to ingest a source and update wiki
- query_latency_ms: Time to query wiki with progressive disclosure
- sync_throughput: Pages synced per second to SurrealDB
- end_to_end_s: Full cycle: ingest → sync → query
"""

from __future__ import annotations

import asyncio
import tempfile
import time
from pathlib import Path
from typing import Any

import cohezion.integrations.obsidian_wiki as obsidian
from cohezion.integrations.wiki_mirix_bridge import WikiMirixBridge
from cohezion.mcp.wiki_mcp import WikiMCP


class WikiBenchmark:
    """Benchmark suite for wiki operations."""

    def __init__(self, vault_path: Path | None = None):
        self.vault_path = vault_path or Path(tempfile.mkdtemp(prefix="wiki_benchmark_"))
        self.wiki = obsidian.ObsidianWiki(self.vault_path)
        self.bridge = WikiMirixBridge(self.wiki)
        self.mcp = WikiMCP(self.wiki)

    async def benchmark_ingest(self, num_sources: int = 100) -> dict[str, float]:
        """Benchmark source ingestion."""
        times = []

        for i in range(num_sources):
            source_content = f"""
# Test Article {i}

This is a test article about topic {i}. It discusses various concepts:
- Concept A related to topic {i}
- Concept B that builds on Concept A
- Entity {i} who is an expert in this field

## Key Points
1. First important point about {i}
2. Second point referencing [[Concept A]]
3. Third point linking to [[Entity {i}]]
"""
            start = time.perf_counter()
            await self.mcp.wiki_ingest(
                source=source_content, source_type="article", auto_extract=True
            )
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

        return {
            "ingest_latency_ms": sum(times) / len(times),
            "ingest_p99_ms": sorted(times)[int(len(times) * 0.99)],
            "ingest_throughput": num_sources / (sum(times) / 1000),  # sources/sec
        }

    async def benchmark_query(self, num_queries: int = 100) -> dict[str, float]:
        """Benchmark wiki queries with progressive disclosure."""
        # First ingest some data
        await self.benchmark_ingest(50)

        queries = [
            "What is Concept A?",
            "Who is Entity 5?",
            "Tell me about topic 10",
            "How does Concept A relate to Concept B?",
        ] * (num_queries // 4)

        times = []
        for query in queries:
            start = time.perf_counter()
            await self.mcp.wiki_query(query, depth="standard", file_back=False)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        return {
            "query_latency_ms": sum(times) / len(times),
            "query_p99_ms": sorted(times)[int(len(times) * 0.99)],
            "queries_per_sec": num_queries / (sum(times) / 1000),
        }

    async def benchmark_sync(self, num_pages: int = 100) -> dict[str, float]:
        """Benchmark SurrealDB sync throughput."""
        # Create pages first
        for i in range(num_pages):
            await self.wiki.create_wiki_page(
                path=f"test/sync_test_{i}.md",
                content=f"# Test Page {i}\n\nContent for page {i}.",
                category="synthesis",
            )

        start = time.perf_counter()
        await self.bridge.sync_all_to_surreal()
        elapsed = time.perf_counter() - start

        return {
            "sync_duration_s": elapsed,
            "sync_throughput": num_pages / elapsed,
        }

    async def benchmark_end_to_end(self, cycles: int = 10) -> dict[str, float]:
        """Benchmark full cycle: ingest → sync → query."""
        times = []

        for i in range(cycles):
            start = time.perf_counter()

            # Ingest
            await self.mcp.wiki_ingest(
                source=f"Cycle {i}: New research about topic X and Y", source_type="article"
            )

            # Sync to SurrealDB
            await self.bridge.sync_all_to_surreal()

            # Query
            await self.mcp.wiki_query("What do we know about topic X?")

            elapsed = time.perf_counter() - start
            times.append(elapsed)

        return {
            "end_to_end_s": sum(times) / len(times),
            "cycles_per_minute": cycles / (sum(times) / 60),
        }

    async def run_all(self) -> dict[str, Any]:
        """Run all benchmarks and return results."""
        print("Running wiki integration benchmarks...")

        results = {}

        print("  → ingest benchmark (100 sources)...")
        results |= await self.benchmark_ingest(100)

        print("  → query benchmark (100 queries)...")
        results |= await self.benchmark_query(100)

        print("  → sync benchmark (100 pages)...")
        results |= await self.benchmark_sync(100)

        print("  → end-to-end benchmark (10 cycles)...")
        results |= await self.benchmark_end_to_end(10)

        return results


async def main():
    """Run benchmark and output metrics."""
    bench = WikiBenchmark()
    results = await bench.run_all()

    # Print METRIC lines for autoresearch parsing
    for key, value in results.items():
        print(f"METRIC {key}={value:.6f}")

    # Also print summary
    print("\n--- Summary ---")
    print(f"Ingest latency: {results['ingest_latency_ms']:.2f} ms")
    print(f"Query latency: {results['query_latency_ms']:.2f} ms")
    print(f"Sync throughput: {results['sync_throughput']:.2f} pages/sec")
    print(f"End-to-end cycle: {results['end_to_end_s']:.2f} sec")


if __name__ == "__main__":
    asyncio.run(main())
