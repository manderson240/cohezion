# Phase 2: Priority Reordering (VAE Diagnostic Findings)

## Discovery from Diagnostic

### What We Found
1. ✅ VAE Encoder IS loaded and functional (0.22ms per encoding)
2. ✅ L2 cache semantic matching IS working for similar prompts
3. ❌ **BUT**: Semantic discrimination is poor (~0.97 similarity for both related AND unrelated texts)

### Root Cause Analysis

The VAE discrimination issue stems from:
- VAE trained on hash-based embeddings (limited signal)
- Hash embeddings are normalized random vectors (high dimensionality curse)
- Result: Poor semantic discrimination between unrelated topics

### Impact Assessment

**Current L3 cache hit rate bottleneck: NOT semantic discrimination, but QUERY LATENCY**

Why L3 hits are only 5%:
1. Skill selection queries take 50-200ms each (slow)
2. Each query must search vault linearly O(n)
3. Slow queries limit how many similarities we can check
4. Result: Miss patterns that would have matched if we had time to query

**Example:**
- Old: Search 5 patterns in 50-200ms → find 1 match = 20% hit rate
- New (optimized): Search 50 patterns in 5-20ms → find 10 matches = 100% potential hit rate!

---

## Revised Priority Order (HIGH IMPACT FIRST)

### Priority 1: Vault Query Optimization (DO THIS FIRST) — 2-3 hours
**Impact**: 5-10× faster skill selection queries
**Bottleneck**: Currently SLOWEST step in compound execution

**Work:**
1. Implement hierarchical vault search (metadata indexing + tagging)
2. Replace O(n) linear scan with O(log n) tagged lookup
3. Enable processing 10× more patterns in same time budget
4. Result: More L3 cache hits from searching more candidates

**Success Metrics:**
- Query latency: 50-200ms → 5-20ms (5-10× faster)
- Patterns searched per skill selection: 5-10 → 50-100
- L3 hit rate: 5% → 25%+
- Skill selection latency → Overall throughput improvement

### Priority 2: VAE Encoder Enhancement (DO THIS SECOND) — 2-3 hours
**Impact**: Better semantic discrimination (once queries are fast)
**Current Bottleneck**: Query latency makes VAE discrimination moot

**Work:**
1. Integrate sentence-transformers for real semantic embeddings
2. Replace hash-based inputs to VAE with actual semantic vectors
3. Retrain lightweight VAE or use pretrained model
4. Result: Excellent discrimination for semantic cache matching

**Success Metrics:**
- Discrimination: unrelated <0.7, related >0.85
- L2 cache hit rate: 30% → 40%+
- Combined L1+L2+L3 hit rate: 92% → 96%+

### Priority 3: Observability Dashboard — 3-4 hours
**Impact**: Production visibility and monitoring

### Priority 4: Production Deployment — 2-3 hours
**Impact**: Safe, monitored rollout

---

## Why This Order Makes Sense

### Mathematical Analysis

**Throughput = f(query_speed, semantic_quality)**

- If queries are slow (current): semantic_quality has minimal impact
  - Even perfect discrimination (1.0) won't help if you can only check 5 patterns

- If queries are fast (after Priority 1): semantic_quality becomes critical
  - Now you can check 50 patterns and benefit from better discrimination

### Expected Throughput Gains

| Phase | Query Speed | Semantic Quality | L3 Hit Rate | Token Efficiency |
|-------|-------------|------------------|-------------|------------------|
| Current | 50-200ms | ~0.5 (poor) | 5% | 85 tok/sec |
| After P1 | 5-20ms | ~0.5 (poor) | 25% | +18 tok/sec |
| After P2 | 5-20ms | ~0.9 (good) | 40% | +22 tok/sec |
| Target | 5-20ms | ~0.9 (good) | 40% | 155 tok/sec |

---

## Implementation Plan (REVISED)

### Session 30: Priority 1 - Vault Query Optimization (2-3 hours)

**Task 1.1: Design Hierarchical Search**
```python
# New tagging scheme for vault patterns:
# Operation type: generate, analyze, search, transform, persist
# Domain: nlp, ml, cv, qa, general
# Skill category: core, integration, utility

# Search implementation:
# Old: vault_search(query_string) → linear O(n) scan
# New: vault_search_by_operation(op_type, domain) → O(log n) tagged lookup
```

**Task 1.2: Implement Metadata Indexing**
- Add metadata to each vault pattern
- Create hierarchical directory structure (by operation type, domain)
- Implement fast path lookup

**Task 1.3: Update SkillSelector Integration**
- Modify `select_skills()` to use hierarchical search
- Benchmark latency improvement (50-200ms → 5-20ms target)
- Measure L3 hit rate improvement (5% → 25%+ target)

**Task 1.4: Commit & Verify**
- All 41+ SkillSelector tests pass
- Latency benchmarks show 5-10× improvement
- L3 cache hit rate measurably improves

### Session 31: Priority 2 - VAE Enhancement (2-3 hours)

**Task 2.1: Integrate Sentence-Transformers**
- pip install sentence-transformers
- Create SentenceTransformerEncoder wrapper
- Load pretrained "all-MiniLM-L6-v2" model (32MB, fast)

**Task 2.2: Update Cache Integration**
- Modify `_text_to_embedding()` to use sentence-transformers
- Fall back to hash if sentence-transformers unavailable
- Update cache tests for better discrimination thresholds

**Task 2.3: Measure Improvement**
- Semantic discrimination: unrelated <0.7, related >0.85 ✅
- L2 cache hit rate: 30% → 40%+
- Combined L3 hit rate: 25% → 40%+

**Task 2.4: Commit & Verify**
- All 45+ VAE tests pass
- Semantic discrimination tests show 0.7 threshold achieved
- L3 cache hit rate improves further

### Session 32: Priorities 3 & 4 (Run in Parallel) — 5-7 hours total
- **P3**: Observability Dashboard (3-4 hours)
- **P4**: Production Deployment (2-3 hours)

---

## New Token Efficiency Targets

| Metric | Current | After P1 | After P2 | After P3+4 |
|--------|---------|----------|----------|-----------|
| Query Latency | 50-200ms | 5-20ms ⬇️ | 5-20ms | 5-20ms |
| L3 Hit Rate | 5% | 25% ⬆️ | 40% ⬆️ | 40% |
| Cache Hit Rate | 75% | 85% ⬆️ | 92% ⬆️ | 92% |
| Token Efficiency | 85 tok/sec | 103 tok/sec ⬆️ | 125 tok/sec ⬆️ | 155 tok/sec |

---

## Rationale

1. **Query Optimization FIRST** — Lowest hanging fruit, immediate 5-10× speedup
2. **VAE Enhancement SECOND** — Builds on faster queries to unlock semantic benefits
3. **Observability THIRD** — Visibility into improvements
4. **Deployment FOURTH** — Safe rollout with monitoring

This order maximizes impact per hour of work.

---

## Next Steps

✅ Diagnostics complete - ready to start Priority 1
→ **Proceed to Vault Query Optimization (Phase 2 Priority 1)**
