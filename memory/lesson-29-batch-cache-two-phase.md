---
title: Batch Cache Two-Phase Pattern: Check Cache Before Compute
date: 2026-02-23
severity: MEDIUM
category: architecture
cost_of_forgetting: "60% wasted compute -- re-computing embeddings that are already cached"
tags: [caching, batch-processing, optimization, patterns]
status: validated
aspect: knower
neural:
  activation: 0.79
  stage: growing
  synapse_in: 11
  synapse_out: 9
---

# Lesson: Batch Cache Two-Phase Pattern: Check Cache Before Compute

## Context

During Cohezion embedding pipeline optimization in February 2026, batch embedding operations were taking far longer than expected. Profiling revealed that the cache was being checked after computation, not before. The pipeline computed embeddings for all texts in a batch, then stored results in cache for future runs. The current run received zero cache benefit -- even when 80%+ of the texts had been embedded in a previous session.

## Problem

The original code followed a compute-then-cache pattern:

1. **Batch arrives**: 500 texts need embedding
2. **All 500 computed**: Ollama generates embeddings for every text (400 were already cached from prior sessions)
3. **Results cached**: All 500 embeddings written to cache
4. **Cache hit on next run**: Only the next batch benefits from the cache

This meant the first run of every session recomputed everything. With Ollama embedding latency of 50-100ms per text, a 500-text batch took 25-50 seconds when it should have taken 5-10 seconds (computing only the 100 cache misses).

## Core Learning

**Cache check MUST precede computation. Two-phase pattern: (1) bulk cache lookup, (2) compute only misses, (3) write all results to cache.**

### Pattern
```python
def batch_embed(texts):
    # Phase 1: Bulk cache lookup
    cache_keys = [hash(t) for t in texts]
    cached = cache.mget(cache_keys)

    # Phase 2: Compute only misses
    misses = [(i, texts[i]) for i, v in enumerate(cached) if v is None]
    computed = model.embed([t for _, t in misses]) if misses else []

    # Phase 3: Write misses to cache
    for (i, _), embedding in zip(misses, computed):
        cache.set(cache_keys[i], embedding)
        cached[i] = embedding

    return cached
```

## Solution

The pipeline was restructured into an explicit three-phase pattern:

1. **Phase 1 -- Bulk cache lookup**: Use `mget` (not per-item `get`) to check all keys in a single cache round trip
2. **Phase 2 -- Compute only misses**: Build a list of uncached texts and compute only those
3. **Phase 3 -- Write misses to cache**: Store newly computed results so the next batch benefits

Key implementation detail: use bulk cache operations (`mget`/`mset`) rather than per-item `get`/`set`. A single `mget` for 500 keys is 10-50x faster than 500 individual `get` calls.

## Prevention

- **Default to cache-first**: When writing any batch processing function, start with the cache lookup phase
- **Measure cache hit rate**: Log the ratio of cache hits to total items per batch. If hit rate is near zero, the cache may not be working.
- **Use bulk operations**: Per-item cache calls negate the performance benefit of caching for large batches
- **Test cache ordering**: Write a test that runs the same batch twice and asserts the second run computes zero items

## Cost of Forgetting

- **60% wasted compute**: Re-computing cached results on every run
- **25-50 second batch times** instead of 5-10 seconds for typical workloads
- **Higher Ollama load**: Unnecessary inference requests that contribute to cold-start problems (see [[lesson-06-ollama-latency]])
- **Higher token costs**: In API-based embedding services, every unnecessary compute call costs money

## Recommendations

### Do
- Always check cache BEFORE computation in batch operations
- Use bulk cache operations (mget/mset) not per-item get/set

### Don't
- Check cache after computing (defeats the purpose)

## Related Concepts

- [[compound-engineering]] - Caching compounds across sessions and batches
- [[agentic-ai-memory-hierarchies]] - the two-phase cache pattern reduces KV cache memory pressure: by computing only cache misses, it minimizes the volume of new inference that must be held in HBM
- [[concept-caching]] - this lesson defines the canonical batch caching pattern: check cache before compute
- [[context-management]] - batch cache pattern directly optimizes context retrieval at scale
- [[agent-context]] - reduces redundant computation in context retrieval pipelines
- [[token-efficiency]] - 60% reduction in compute costs through cache-before-compute ordering
- [[semantic-search]] - batch embedding cache lookups before computing new embeddings saves significant compute
- [[lesson-06-ollama-latency]] - unnecessary embedding calls compound Ollama's cold-start latency problem
- [[machine-learning-optimization]] - cache-before-compute is a core ML pipeline optimization

## Validation

**Discovered**: Feb 2026 in embedding pipeline optimization
**Impact**: 60% reduction in embedding computation costs; batch time from 25-50s to 5-10s
**Status**: Validated
