import asyncio
import logging
import os
import sys
import time


# Setup paths
sys.path.append(os.path.abspath("src"))

from cohezion.caching.semantic_cache import SemanticCache


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CacheTest")


async def test_semantic_cache():
    logger.info("🧪 Testing Semantic Cache...")

    cache = SemanticCache(threshold=0.8)  # Lower threshold for demo
    await cache.connect()

    # 1. SET
    query_1 = "What is the nature of the void?"
    response_1 = (
        "The Void is not empty space, but a plenum of infinite potential where i=0.5 stability acts as a gateway."
    )

    logger.info(f"Step 1: Caching Query: '{query_1}'")
    await cache.set(query_1, response_1)

    # Wait a moment for consistency (SurrealDB is fast but good practice)
    await asyncio.sleep(0.5)

    # 2. GET (Partial Match)
    query_2 = "Explain the nature of the void to me."
    logger.info(f"Step 2: Checking Semantically Similar Query: '{query_2}'")

    start = time.perf_counter()
    result = await cache.get(query_2)
    duration = (time.perf_counter() - start) * 1000

    if result == response_1:
        logger.info(f"✅ SUCCESS: Cache Hit! (Response matched) in {duration:.2f}ms")
    else:
        logger.error(f"❌ FAILURE: Cache Miss or Mismatch. Result: {result}")

    # 3. GET (Unrelated)
    query_3 = "What is the price of eggs?"
    logger.info(f"Step 3: Checking Unrelated Query: '{query_3}'")
    result_3 = await cache.get(query_3)

    if result_3 is None:
        logger.info("✅ SUCCESS: Cache Miss as expected.")
    else:
        logger.error(f"❌ FAILURE: False Positive! Result: {result_3}")

    await cache.dba.close()


if __name__ == "__main__":
    asyncio.run(test_semantic_cache())
