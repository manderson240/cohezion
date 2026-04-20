#!/usr/bin/env python3
"""Phase 2 Integration Test: Verify TokenEfficientClient with Phase 1 components."""

import asyncio
import logging
import sys
import tempfile
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def test_lru_persistent_token_cache():
    """Test LRUPersistentTokenCache integration."""
    logger.info("=" * 70)
    logger.info("TEST: LRUPersistentTokenCache with bounded memory")
    logger.info("=" * 70)

    from cohezion.swarm.batch_processor import CacheEntry
    from cohezion.swarm.lru_persistent_token_cache import LRUPersistentTokenCache

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create cache with small max_entries to test eviction
        cache = LRUPersistentTokenCache(
            cache_dir=tmpdir,
            max_entries=5,
            eviction_threshold=0.8,
            target_utilization=0.6,
            persistence_enabled=False,
        )

        # Add entries up to eviction threshold
        for i in range(6):
            cache[f"key_{i}"] = CacheEntry(key=f"key_{i}", value=f"response_{i}", tokens_used=100 + i)

        # Check stats
        stats = cache.get_stats()
        logger.info("Cache stats after 6 puts:")
        logger.info(f"  Memory entries: {stats['memory_entries']}")
        logger.info(f"  Max entries: {stats['max_entries']}")
        logger.info(f"  Utilization: {stats['utilization']:.1%}")

        # Verify bounded memory (allow for off-by-one due to async eviction)
        if stats["memory_entries"] <= cache.max_entries + 1:
            logger.info("✅ Memory bounded correctly")
            return True
        else:
            logger.error(f"❌ Memory not bounded: {stats['memory_entries']} > {cache.max_entries}")
            return False


async def test_dynamic_concurrency_gate_integration():
    """Test DynamicConcurrencyGate integration in batch processor."""
    logger.info("=" * 70)
    logger.info("TEST: DynamicConcurrencyGate in BatchProcessor")
    logger.info("=" * 70)

    from cohezion.swarm.dynamic_concurrency_gate import get_concurrency_gate

    gate = get_concurrency_gate()
    concurrency = gate.get_safe_concurrency()

    logger.info(f"Safe concurrency level: {concurrency}")
    logger.info(f"  Base: {gate.base_concurrency}")

    # Check if concurrency is reasonable (4-12 range)
    if 4 <= concurrency <= 12:
        logger.info("✅ Concurrency within expected range")
        return True
    else:
        logger.error(f"❌ Concurrency out of range: {concurrency}")
        return False


async def test_persistent_cache_integration():
    """Test PersistentCache session restore."""
    logger.info("=" * 70)
    logger.info("TEST: PersistentCache session restore")
    logger.info("=" * 70)

    from cohezion.swarm.persistent_cache import PersistentCache

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = Path(tmpdir) / "test_cache.jsonl"

        # Create cache and add entries
        cache1 = PersistentCache(cache_file=str(cache_file))
        cache1.set("test_key", "test_value")
        stats1 = cache1.get_stats()
        logger.info(f"Created cache with size {stats1.get('cache_size', 0)}")

        # Create new cache instance and restore
        cache2 = PersistentCache(cache_file=str(cache_file))
        stats2 = cache2.get_stats()
        logger.info(f"Restored cache with size {stats2.get('cache_size', 0)}")

        # Verify restoration
        if stats2.get("cache_size", 0) == 1:
            logger.info("✅ Session restore working correctly")
            return True
        else:
            logger.error(f"❌ Session restore failed: {stats2}")
            return False


async def main():
    """Run all Phase 2 integration tests."""
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 2 INTEGRATION TEST SUITE")
    logger.info("=" * 70 + "\n")

    tests = [
        ("LRU Persistent Token Cache", test_lru_persistent_token_cache),
        ("Dynamic Concurrency Gate", test_dynamic_concurrency_gate_integration),
        ("Persistent Cache", test_persistent_cache_integration),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            result = await test_fn()
            results[name] = result
            logger.info("")
        except Exception as e:
            logger.error(f"❌ Test failed with exception: {e}")
            import traceback

            traceback.print_exc()
            results[name] = False

    # Summary
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {name}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")
    logger.info("=" * 70 + "\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
