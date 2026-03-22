#!/usr/bin/env python3
"""Example: Token-efficient batch processing with caching and parallelism.

Demonstrates the two-layer optimization:
  Layer 1: SHA-256 hash cache (eliminates redundant API calls)
  Layer 2: Batch processing (Phase 1 cache + Phase 2 parallel execution)

Usage::

    python scripts/example_token_efficient_batch.py

Expected output:
  - Cache priming: 3 unique prompts
  - Batch processing: 8 items (5 cache hits, 3 misses)
  - Tokens saved: ~750 tokens (5 cache hits * 150 per hit)
  - Total duration: < 500ms (parallel execution with concurrency control)
"""

import asyncio
import sys
from pathlib import Path


# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.core.config import CohezionConfig
from cohezion.swarm import BatchItem, TokenEfficientClient


async def main() -> None:
    """Run token-efficient batch processing example."""
    print("=" * 70)
    print("Token-Efficient Batch Processing Example")
    print("=" * 70)

    # Initialize client and config
    config = CohezionConfig()
    config.batch.parallel_tasks = 2  # Limit parallelism for demo
    client = TokenEfficientClient(config=config)

    print("\n📊 Configuration:")
    print(f"  Cache size: {config.cache.max_size} entries")
    print(f"  Cache hit value: {config.cache.cache_hit_value} tokens")
    print(f"  Parallel tasks: {config.batch.parallel_tasks}")
    print(f"  Batch enabled: {config.batch.enabled}")

    # Prime the cache with some popular prompts
    # This simulates real-world scenarios where prompts are reused
    print("\n🔄 Priming cache with popular prompts (Step 1):")
    popular_prompts = [
        "Explain quantum computing",
        "What is machine learning?",
        "Define artificial intelligence",
    ]

    # Mock the generate method to simulate Ollama responses
    async def mock_generate(prompt: str, model: str, system: str = "", num_predict: int = 256):
        """Simulate Ollama response."""
        await asyncio.sleep(0.05)  # Simulate API latency
        # Return different token counts based on prompt length
        tokens = 50 + len(prompt) // 10
        return f"Response to: {prompt[:30]}...", tokens

    original_generate = client.ollama.generate
    client.ollama.generate = mock_generate

    try:
        # Prime cache
        for prompt in popular_prompts:
            await client.generate(prompt=prompt, model="phi3:mini", system="You are helpful")
            print(f"  ✓ Cached: {prompt[:40]}...")

        print(f"\n  Cache now contains {len(client.batch_processor.cache)} entries")

        # Now create batch items that will mostly hit the cache
        print("\n📝 Creating batch items (8 items, reusing cached prompts):")
        system_prompt = "You are helpful"
        model = "phi3:mini"
        items = [
            BatchItem(
                id="1",
                prompt="Explain quantum computing",
                system=system_prompt,
                model=model,
            ),
            BatchItem(
                id="2",
                prompt="What is machine learning?",
                system=system_prompt,
                model=model,
            ),
            BatchItem(
                id="3",
                prompt="Explain quantum computing",
                system=system_prompt,
                model=model,
            ),
            BatchItem(
                id="4",
                prompt="Define artificial intelligence",
                system=system_prompt,
                model=model,
            ),
            BatchItem(
                id="5",
                prompt="What is machine learning?",
                system=system_prompt,
                model=model,
            ),
            BatchItem(
                id="6",
                prompt="Explain quantum computing",
                system=system_prompt,
                model=model,
            ),
            BatchItem(
                id="7",
                prompt="Define artificial intelligence",
                system=system_prompt,
                model=model,
            ),
            BatchItem(
                id="8",
                prompt="What is deep learning?",
                system=system_prompt,
                model=model,
            ),
        ]

        seen = set()
        for item in items:
            is_cached = item.prompt in seen
            seen.add(item.prompt)
            cache_marker = "📌 CACHED" if is_cached else "✨ NEW"
            print(f"  {item.id}: {item.prompt[:40]}... ({cache_marker})")

        # Process with Phase 1 + Phase 2 batch
        print("\n⚡ Processing batch with Phase 1 (cache) + Phase 2 (parallel)...")

        result = await client.batch_generate(items)

        # Display results
        print("\n✅ Batch Processing Complete!")
        print("\n📈 Results:")
        print(f"  Total items: {len(result.items)}")
        print(f"  Cache hits: {result.cache_hits} ({100 * result.cache_hit_rate:.1f}%)")
        print(f"  Cache misses: {result.cache_misses}")
        print(f"  Total tokens: {result.total_tokens}")
        print(f"  Tokens saved: {result.tokens_saved} (from {result.cache_hits} cache hits)")
        print(f"  Parallel executions: {result.parallel_executions}")
        print(f"  Total duration: {result.total_duration_ms:.1f}ms")

        # Show per-item results
        print("\n📋 Per-Item Results:")
        for item in result.items:
            status = "✓ CACHE HIT" if item.cached else "→ API CALL"
            print(f"  [{status}] {item.id}: {item.tokens_used} tokens")

        # Display client metrics
        metrics = client.get_metrics()
        print("\n📊 Token Efficiency Metrics:")
        print(f"  Cache hit rate: {metrics['cache_hit_rate'] * 100:.1f}%")
        print(f"  Total operations: {metrics['total_operations']}")
        print(f"  API calls made: {metrics['api_calls']}")
        print(f"  Estimated tokens saved: {metrics['estimated_tokens_saved']}")
        print(f"  Tokens per second: {metrics['tokens_per_second']:.0f}")

        # Show cache statistics
        cache_stats = client.batch_processor.cache_stats()
        print("\n💾 Cache Statistics:")
        print(f"  Cache size: {cache_stats['cache_size']} entries")
        print(f"  Max size: {cache_stats['max_cache_size']}")
        print(f"  Enabled: {cache_stats['cache_enabled']}")

        print("\n" + "=" * 70)
        print("✨ Batch processing complete with token efficiency!")
        print("=" * 70)

    finally:
        # Restore original method
        client.ollama.generate = original_generate


if __name__ == "__main__":
    asyncio.run(main())
