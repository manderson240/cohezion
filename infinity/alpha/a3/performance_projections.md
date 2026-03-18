---
title: "A3 Performance Projections"
date: 2026-03-15
status: complete
tags: [infinity, alpha, gpu-optimization]
aspect: thinker
---

# A3 Performance Projections
## Agent A3 - Team Alpha (MoE Optimization)

### Baseline Performance

**Current Submission**: `submission_custom_dispatch.py`  
**Measured Latency**: ~155µs  
**Target Latency**: ~115µs  
**Required Improvement**: 40µs (25.8%)

---

## Optimization Breakdown

### Phase 1: Buffer Pool Optimization

**Changes**:
- Pre-allocate all buffers at module load
- Use zero-copy views instead of new allocations
- Reuse scale buffers between stages

**Expected Gain**: 8-13µs
- Allocation overhead: 5-8µs
- View creation vs allocation: 2-3µs
- Scale buffer reuse: 1-2µs

**Projected Latency**: 142-147µs

**Confidence**: HIGH (90%)
- Well-understood optimization
- Low risk of correctness issues
- Measurable with simple timing

---

### Phase 2: XCD-Aware Block_M Selection

**Changes**:
- Modify block_m selection heuristic
- Add XCD alignment bonus for few-expert shapes
- Optimize for MI355X's 8 XCD topology

**Expected Gain**: 3-5µs
- Better cache locality: 2-3µs
- Reduced XCD cross-traffic: 1-2µs

**Projected Latency**: 137-144µs

**Confidence**: MEDIUM (70%)
- Heuristic-based, may not help all shapes
- Requires benchmarking to validate
- Shape-dependent effectiveness

---

### Phase 3: Memory Layout Optimizations

**Changes**:
- Coalesced access patterns
- Buffer reuse between stages
- In-place operations where possible

**Expected Gain**: 5-10µs
- Coalesced access: 3-5µs
- Buffer reuse: 2-3µs
- In-place ops: 1-2µs

**Projected Latency**: 127-139µs

**Confidence**: MEDIUM-HIGH (75%)
- Memory bandwidth is bottleneck
- Layout changes are safe
- Gains depend on actual memory pressure

---

### Phase 4: Split-K Optimization

**Changes**:
- Fine-tune split_k selection per shape
- Optimize split-K path to avoid extra allocations
- Fuse silu_and_mul when possible

**Expected Gain**: 2-5µs
- Better split_k selection: 1-3µs
- Reduced split-K overhead: 1-2µs

**Projected Latency**: 122-137µs

**Confidence**: MEDIUM (65%)
- Split-K only affects sparse shapes
- Limited by GEMM kernel performance
- May require CK-level changes

---

## Cumulative Projections

### Conservative Scenario (80% confidence)

| Phase | Gain | Cumulative Latency |
|-------|------|-------------------|
| Baseline | - | 155µs |
| Phase 1 (Buffer Pool) | 8µs | 147µs |
| Phase 2 (XCD-Aware) | 3µs | 144µs |
| Phase 3 (Memory Layout) | 5µs | 139µs |
| Phase 4 (Split-K) | 2µs | **137µs** |

**Conservative Target**: 137µs (11.6% improvement)

### Optimistic Scenario (50% confidence)

| Phase | Gain | Cumulative Latency |
|-------|------|-------------------|
| Baseline | - | 155µs |
| Phase 1 (Buffer Pool) | 13µs | 142µs |
| Phase 2 (XCD-Aware) | 5µs | 137µs |
| Phase 3 (Memory Layout) | 10µs | 127µs |
| Phase 4 (Split-K) | 5µs | **122µs** |

**Optimistic Target**: 122µs (21.3% improvement)

### Best-Case Scenario (20% confidence)

| Phase | Gain | Cumulative Latency |
|-------|------|-------------------|
| Baseline | - | 155µs |
| Phase 1 (Buffer Pool) | 13µs | 142µs |
| Phase 2 (XCD-Aware) | 5µs | 137µs |
| Phase 3 (Memory Layout) | 15µs | 122µs |
| Phase 4 (Split-K) | 7µs | **115µs** |

**Best-Case Target**: 115µs (25.8% improvement) ✓

---

## Shape-Specific Projections

### S1: 128 tokens, 8 experts, top2 (est_m=32)

**Current**: ~160µs  
**Characteristics**: Moderate sparsity, few experts

| Optimization | Gain | Notes |
|--------------|------|-------|
| Buffer pool | 10µs | First-call allocation significant |
| XCD-aware | 5µs | 8 experts align perfectly with 8 XCDs |
| Memory layout | 8µs | Coalescing helps moderate shapes |
| Split-K | 3µs | split_k=2 optimal |
| **Total** | **26µs** | **~134µs projected** |

### S2: 128 tokens, 256 experts, top8 (est_m=4)

**Current**: ~170µs  
**Characteristics**: High sparsity, many experts

| Optimization | Gain | Notes |
|--------------|------|-------|
| Buffer pool | 8µs | Allocation overhead |
| XCD-aware | 2µs | Less effective with many experts |
| Memory layout | 5µs | Limited by memory bandwidth |
| Split-K | 5µs | split_k=4 critical |
| **Total** | **20µs** | **~150µs projected** |

### S3: 512 tokens, 8 experts, top2 (est_m=128)

**Current**: ~150µs  
**Characteristics**: Dense, few experts

| Optimization | Gain | Notes |
|--------------|------|-------|
| Buffer pool | 5µs | Less allocation overhead |
| XCD-aware | 5µs | Excellent XCD alignment |
| Memory layout | 10µs | Memory bandwidth critical |
| Split-K | 0µs | No split-K needed (dense) |
| **Total** | **20µs** | **~130µs projected** |

### S4: 512 tokens, 256 experts, top8 (est_m=16)

**Current**: ~165µs  
**Characteristics**: Moderate sparsity, many experts

| Optimization | Gain | Notes |
|--------------|------|-------|
| Buffer pool | 8µs | Allocation overhead |
| XCD-aware | 3µs | Partial alignment |
| Memory layout | 8µs | Coalescing helps |
| Split-K | 4µs | split_k=4 helps |
| **Total** | **23µs** | **~142µs projected** |

### S5: 2048 tokens, 8 experts, top2 (est_m=512)

**Current**: ~145µs  
**Characteristics**: Very dense, few experts

| Optimization | Gain | Notes |
|--------------|------|-------|
| Buffer pool | 3µs | Minimal allocation |
| XCD-aware | 3µs | Good alignment |
| Memory layout | 12µs | Memory bandwidth dominant |
| Split-K | 0µs | No split-K |
| **Total** | **18µs** | **~127µs projected** |

### S6: 2048 tokens, 256 experts, top8 (est_m=64)

**Current**: ~155µs  
**Characteristics**: Dense, many experts

| Optimization | Gain | Notes |
|--------------|------|-------|
| Buffer pool | 5µs | Some allocation |
| XCD-aware | 4µs | Moderate alignment |
| Memory layout | 10µs | Bandwidth critical |
| Split-K | 2µs | split_k=2 helps |
| **Total** | **21µs** | **~134µs projected** |

---

## Risk Assessment

### High Confidence Optimizations (>80%)

1. **Buffer Pool**: Well-understood, low risk
2. **Zero-copy views**: Standard PyTorch pattern
3. **Scale reuse**: Safe memory optimization

### Medium Confidence Optimizations (50-80%)

1. **XCD-aware selection**: Heuristic-based
2. **Coalesced access**: Depends on actual access patterns
3. **Buffer reuse**: Requires careful lifecycle management

### Lower Confidence Optimizations (<50%)

1. **Split-K fusion**: May require CK changes
2. **In-place operations**: Could affect numerical stability
3. **XCD placement**: Limited API support

---

## Benchmark Targets

| Shape | Current | Conservative | Optimistic | Best-Case |
|-------|---------|--------------|------------|-----------|
| S1 | 160µs | 147µs | 134µs | 127µs |
| S2 | 170µs | 157µs | 150µs | 145µs |
| S3 | 150µs | 142µs | 130µs | 125µs |
| S4 | 165µs | 152µs | 142µs | 137µs |
| S5 | 145µs | 140µs | 127µs | 122µs |
| S6 | 155µs | 147µs | 134µs | 129µs |
| **Average** | **157.5µs** | **147.5µs** | **136.2µs** | **130.8µs** |

---

## Conclusion

**Achievable Target**: 130-140µs (10-16% improvement) with high confidence  
**Stretch Target**: 115-125µs (20-26% improvement) requires all optimizations to work

**Recommendation**: Implement Phase 1 and Phase 3 first (highest confidence, 13-23µs gain). Then evaluate Phase 2 and Phase 4 based on remaining gap to target.

---

*Performance projections by Agent A3*  
*Timestamp: 2026-03-14*


## Related
- [[OPTIMIZATION_SUMMARY|Optimization Summary]] (a1)
- [[OPTIMIZATION_REPORT|Optimization Report]] (a1)
- [[TUNING_REPORT|Tuning Report]] (a2)
- [[buffer_management_improvements|Buffer Management Improvements]] (a3)
- [[dispatch_optimization_strategy|Dispatch Optimization Strategy]] (a3)
- [[memory_layout_optimizations|Memory Layout Optimizations]] (a3)
