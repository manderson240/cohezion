---
name: caching
description: You are a specialist in caching strategies for high-performance AI systems.
  You understand in-memory caches, disk caches, distributed caching, and cache invalidation
  patterns.
keywords:
- caching
- database
- disk cache
- lru cache
- memoization
- redis
- reliability
- ttl
- vector_store
---

# SKILL: CACHING_PRIME

## DOMAIN EXPERTISE
You are a specialist in **caching strategies** for high-performance AI systems. You understand in-memory caches, disk caches, distributed caching, and cache invalidation patterns.

## KEY TEXTS & CONCEPTS
- **LRU Cache:** Least Recently Used eviction with `functools.lru_cache`
- **Redis:** In-memory data store for distributed caching
- **Disk Cache:** `diskcache` library for persistent caching
- **Memoization:** Caching function results by arguments
- **TTL:** Time-to-live for cache expiration

## INSTRUCTION

### 1. Python lru_cache (In-Memory)
```python
from functools import lru_cache

@lru_cache(maxsize=1024)
def compute_embedding(text: str) -> list[float]:
    """Cache embeddings to avoid recomputation."""
    return model.encode(text).tolist()

# Clear cache when needed
compute_embedding.cache_clear()
```

### 2. Disk Cache (Persistent)
```python
import diskcache

cache = diskcache.Cache('./cache_dir')

@cache.memoize(expire=3600)  # 1 hour TTL
def expensive_computation(input_data):
    # Heavy computation here
    return result

# Manual cache operations
cache.set('key', value, expire=600)
value = cache.get('key', default=None)
```

### 3. Redis (Distributed)
```python
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0)

def cached_query(query: str) -> dict:
    cache_key = f"query:{hash(query)}"

    # Try cache first
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    # Compute and cache
    result = execute_query(query)
    r.setex(cache_key, 3600, json.dumps(result))  # 1 hour TTL
    return result
```

### 4. Cache Invalidation Patterns
```python
# Pattern 1: Time-based (TTL)
cache.set('data', value, expire=300)  # 5 minutes

# Pattern 2: Event-based
def on_data_update(event):
    cache.delete(f"data:{event.id}")

# Pattern 3: Version-based
cache_key = f"model:v{MODEL_VERSION}:{input_hash}"
```

### 5. Cohezion Embedding Cache
```python
class EmbeddingCache:
    def __init__(self, max_size=10000):
        self.cache = {}
        self.max_size = max_size

    def get_or_compute(self, text: str, compute_fn) -> list[float]:
        key = hash(text)
        if key not in self.cache:
            if len(self.cache) >= self.max_size:
                # Evict oldest
                self.cache.pop(next(iter(self.cache)))
            self.cache[key] = compute_fn(text)
        return self.cache[key]
```

## APPLICATIONS
- **Embedding Cache:** Avoid recomputing text embeddings
- **LLM Response Cache:** Store frequent query responses
- **Simulation State:** Cache intermediate universe states
- **API Rate Limiting:** Cache external API responses

## VERSION
v1.0

## SEE ALSO
- DATABASE_PRIME.md
- RELIABILITY_PRIME.md
- VECTOR_STORE_PRIME.md
