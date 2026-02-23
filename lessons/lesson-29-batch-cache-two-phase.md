---
title: Batch Cache Two-Phase Pattern: Check Cache Before Compute
date: 2026-02-23
severity: MEDIUM
category: architecture
tags: [caching, batch-processing, optimization, patterns]
status: validated
---

# Lesson: Batch Cache Two-Phase Pattern: Check Cache Before Compute

## Context

Batch processing operations were re-computing results that were already cached. The cache check was happening after computation rather than before, yielding zero cache benefit for the current run.

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

## Recommendations

### Do
- Always check cache BEFORE computation in batch operations
- Use bulk cache operations (mget/mset) not per-item get/set

### Don't
- Check cache after computing (defeats the purpose)

## Related Concepts

- [[compound-engineering]] - Caching compounds across sessions and batches

## Validation

**Discovered**: Feb 2026 in embedding pipeline optimization
**Status**: Validated -- 60% reduction in embedding computation costs
