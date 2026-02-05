
import asyncio
import logging
import numpy as np
import time
from cohezion.reliability.semantic_cache import SemanticCache
from cohezion.core.persistence.redis_aggregator import get_redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_phase_8")

async def test_redis_connection():
    print("\n--- Testing Redis Connection ---")
    redis = get_redis()
    connected = await redis.connect()
    if connected:
        print("✅ Redis connected successfully.")
        await redis.set("test_key", {"msg": "hello from Phase 8"})
        val = await redis.get("test_key")
        print(f"Retrieved: {val}")
        assert val["msg"] == "hello from Phase 8"
    else:
        print("⚠️ Redis not available or connection failed.")
    return connected

async def test_semantic_cache_tiers():
    print("\n--- Testing Semantic Cache Tiers (L0/L1) ---")
    cache = SemanticCache(cache_dir="cache/test_semantic", threshold=0.9)
    
    # Mock vector
    vec = np.random.rand(512).astype(np.float32)
    response = "The manifold is stable at 0.5 overlap."
    metadata = {"agent": "TestAgent", "phi": 0.95}
    query_text = "What is the stability condition?"
    
    # 1. Add to cache
    print("Adding entry to cache (L0 + L1)...")
    await cache.add(vec, response, metadata, query_text=query_text)
    
    # 2. Test L1 Hit (Exact Match)
    print("Testing L1 Hit (Exact Match)...")
    hit = await cache.search(vec, query_text=query_text)
    assert hit is not None
    assert hit["response"] == response
    print(f"✅ L1 Hit Verified. Score: {hit.get('semantic_score')}")
    
    # 3. Test L0 Hit (Semantic Match)
    print("Testing L0 Hit (Semantic Match with slight vector drift)...")
    drifted_vec = vec + np.random.normal(0, 0.01, 512).astype(np.float32)
    hit_l0 = await cache.search(drifted_vec, query_text="Slightly different query")
    assert hit_l0 is not None
    assert hit_l0["response"] == response
    print(f"✅ L0 Hit Verified. Score: {hit_l0.get('semantic_score')}")

async def run_all():
    redis_available = await test_redis_connection()
    if redis_available:
        await test_semantic_cache_tiers()
    else:
        print("⏭️ Skipping semantic cache tier test as Redis is unavailable.")

if __name__ == "__main__":
    asyncio.run(run_all())
