---
title: "A3 Shape Analysis & Dispatch Logic Optimization"
date: 2026-03-15
status: in-progress
tags: [infinity, alpha, gpu-optimization]
aspect: thinker
---

# A3 Shape Analysis & Dispatch Logic Optimization
## Agent A3 - Team Alpha (MoE Optimization)

### Current Status Analysis

**Base Submission**: `submission_custom_dispatch.py`  
**Current Performance**: ~155µs  
**Target**: ~115µs (25% reduction)  
**Gap**: ~40µs to optimize

---

## 1. Token Dispatch Pattern Analysis

### Current Dispatch Flow
```
Stage 0: moe_sorting_fwd
  - Sorts tokens by expert assignment
  - Creates sorted_ids, sorted_weights, sorted_expert_ids
  - Time: ~15-20µs (estimated)

Stage 1: fused_dynamic_mxfp4_quant_moe_sort
  - Quantizes hidden_states to MXFP4
  - Time: ~25-30µs (estimated)

Stage 2: moe_cktile2stages_gemm1
  - Gate-up projection with SiLU activation
  - Time: ~60-80µs (estimated, shape-dependent)

Stage 3: moe_cktile2stages_gemm2
  - Down projection with routing weights
  - Time: ~40-50µs (estimated)
```

### Identified Bottlenecks

1. **Buffer Cache Misses**: `_get_buffers()` creates new buffers on first call per shape
2. **Redundant Tensor Operations**: Multiple view/reshape operations in hot path
3. **Suboptimal Block_M Selection**: Current heuristic doesn't account for MI355X XCD topology
4. **Split-K Overhead**: Split-K path requires extra tmp_out allocation and silu_and_mul call

---

## 2. Dispatch Optimization Strategy

### 2.1 Pre-allocated Buffer Pool

**Problem**: Current buffer cache is per-shape, causing allocation on first call  
**Solution**: Pre-allocate maximum-sized buffers at module load

```python
# Current (per-shape allocation)
def _get_buffers(num_tokens, topk, num_experts, model_dim, block_m, device):
    key = (num_tokens, topk, num_experts, model_dim, block_m)
    if key in _buf_cache:
        return _buf_cache[key]
    # ... allocate new buffers

# Optimized (pre-allocated pool)
_MAX_TOKENS = 2048
_MAX_TOPK = 8
_MAX_EXPERTS = 256
_MAX_MODEL_DIM = 7168
_MAX_BLOCK_M = 128

_BUF_POOL = {
    "sorted_ids": torch.empty(_MAX_TOKENS * _MAX_TOPK + _MAX_EXPERTS * _MAX_BLOCK_M, 
                               dtype=torch.int32, device="cuda"),
    "sorted_weights": torch.empty(_MAX_TOKENS * _MAX_TOPK + _MAX_EXPERTS * _MAX_BLOCK_M,
                                  dtype=torch.float32, device="cuda"),
    # ... etc
}

def _get_buffer_views(num_tokens, topk, num_experts, model_dim, block_m):
    """Return views into pre-allocated pool instead of new allocations."""
    max_padded = num_tokens * topk + num_experts * block_m - topk
    return {
        "sorted_ids": _BUF_POOL["sorted_ids"][:max_padded],
        "sorted_weights": _BUF_POOL["sorted_weights"][:max_padded],
        # ... etc
    }
```

**Expected Gain**: ~5-8µs (eliminates allocation overhead on first calls)

### 2.2 XCD-Aware Block_M Selection

**Problem**: Current selection doesn't account for MI355X's 8 XCDs  
**Solution**: Optimize for XCD-local memory access patterns

```python
def _select_block_m_xcd_aware(num_tokens: int, topk: int, num_experts: int,
                               inter_dim: int) -> int:
    """XCD-aware block_m selection for MI355X.
    
    MI355X has 8 XCDs (XCD-aware Compute Domains).
    Optimal dispatch ensures tokens for same expert stay on same XCD
    to maximize L2 cache hit rate.
    """
    tile_n = 128
    tg_n = (inter_dim + tile_n - 1) // tile_n
    
    # For MI355X: prefer block_m that creates tile groups
    # aligned to XCD boundaries (multiples of 8)
    candidates = [32, 64, 128]
    best = (float("inf"), float("inf"), 32)
    
    for bm in candidates:
        max_tokens_padded = num_tokens * topk + num_experts * bm - topk
        tg_num = tg_n * ((max_tokens_padded + bm - 1) // bm)
        rounds = (tg_num + _CU_NUM - 1) // _CU_NUM
        empty = _CU_NUM - (tg_num % _CU_NUM) if tg_num % _CU_NUM else 0
        
        # XCD alignment bonus: prefer block_m that creates
        # expert-aligned work groups
        xcd_alignment = 0
        if num_experts <= 8:
            # Few experts: align tokens per expert to XCD count
            tokens_per_expert = (num_tokens * topk) // num_experts
            if tokens_per_expert % 8 == 0:
                xcd_alignment = -0.5  # bonus
        
        score = (rounds, empty + xcd_alignment, bm)
        if score < best:
            best = score
    
    return best[2]
```

**Expected Gain**: ~3-5µs (better cache locality)

### 2.3 Fused Quantization + Sorting

**Problem**: Current code calls `fused_dynamic_mxfp4_quant_moe_sort` separately  
**Opportunity**: Fuse with token sorting to reduce memory traffic

```python
# Current: separate calls
aiter.moe_sorting_fwd(...)  # writes to buffers
a1, a1_scale = fused_dynamic_mxfp4_quant_moe_sort(...)  # reads hidden_states

# Optimized: fused kernel (if available)
# a1, a1_scale = fused_sort_and_quant(
#     hidden_states, topk_ids, topk_weights, ...
# )
```

**Expected Gain**: ~5-10µs (reduced memory bandwidth)

---

## 3. Buffer Management Improvements

### 3.1 Zero-Copy Buffer Views

Eliminate unnecessary tensor copies by using views:

```python
# Current: creates new tensors
out_stage1 = torch.empty((M, topk, out_dim), dtype=torch.bfloat16, device=device)
tmp_out = torch.zeros((M, topk, inter_dim_packed), dtype=hidden_states.dtype, device=device)

# Optimized: pre-allocated with views
_STAGE1_BUF = torch.empty((2048, 8, 7168 * 8), dtype=torch.bfloat16, device="cuda")
_TMP_BUF = torch.empty((2048, 8, 4096), dtype=torch.bfloat16, device="cuda")

out_stage1 = _STAGE1_BUF[:M, :topk, :out_dim]
tmp_out = _TMP_BUF[:M, :topk, :inter_dim_packed]
```

### 3.2 Scale Tensor Reuse

Scale tensors (e8m0) are small and can be pre-allocated:

```python
# Pre-allocated scale buffers
_SCALE_BUFS = {
    "a1_scale": torch.empty((2048, 256), dtype=torch.uint8, device="cuda"),  # [M, K/32]
    "a2_scale": torch.empty((2048, 256), dtype=torch.uint8, device="cuda"),
}
```

---

## 4. Memory Layout Optimizations

### 4.1 Coalesced Memory Access Patterns

Ensure weight tensors are accessed with stride-1 patterns:

```python
# Current weight layout (may not be optimal)
# w1: [E, 2*d_expert, d_hidden/2] fp4x2

# Optimized: ensure contiguous access
# Verify weights are stored in CK-compatible layout
# and accessed with proper stride
```

### 4.2 Shared Expert Fast Path

For shapes with shared experts, add fast path:

```python
def _direct_dispatch(...):
    # ... existing code ...
    
    # Check if shared expert is present
    if config.get("n_shared_experts", 0) > 0:
        # Use optimized shared expert path
        return _dispatch_with_shared_expert(...)
    
    # ... rest of dispatch ...

def _dispatch_with_shared_expert(...):
    """Optimized path when shared expert is present.
    
    Shared expert is always activated, so we can:
    1. Pre-compute shared expert output
    2. Fuse with routed expert dispatch
    3. Avoid separate kernel launch
    """
    # Implementation: fuse shared expert GEMM with stage 2
    pass
```

---

## 5. Performance Projections

| Optimization | Expected Gain | Cumulative |
|--------------|---------------|------------|
| Pre-allocated buffer pool | 5-8µs | 147-150µs |
| XCD-aware block_m selection | 3-5µs | 142-147µs |
| Fused quant+sort | 5-10µs | 132-142µs |
| Zero-copy buffer views | 2-4µs | 128-140µs |
| Scale tensor reuse | 1-3µs | 125-139µs |
| **Total Projected** | **16-33µs** | **122-139µs** |

**Conservative Target**: 130µs (16% improvement)  
**Optimistic Target**: 115µs (26% improvement)

---

## 6. Implementation Plan

### Phase 1: Buffer Pool (Immediate)
- [ ] Implement pre-allocated buffer pool
- [ ] Update `_get_buffers()` to use views
- [ ] Test for correctness

### Phase 2: XCD-Aware Dispatch (Day 1)
- [ ] Implement XCD-aware block_m selection
- [ ] Benchmark vs current heuristic
- [ ] Tune for benchmark shapes

### Phase 3: Memory Optimizations (Day 2)
- [ ] Implement zero-copy views
- [ ] Add scale tensor reuse
- [ ] Profile memory bandwidth

### Phase 4: Integration (Day 2-3)
- [ ] Combine all optimizations
- [ ] Full benchmark suite
- [ ] Document final results

---

## 7. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Buffer pool too large | Low | Calculate max from benchmark shapes |
| XCD-aware selection worse for some shapes | Medium | Keep fallback to current heuristic |
| Fused kernel not available | Medium | Keep separate call path |
| Memory layout assumptions wrong | Low | Verify with CK documentation |

---

## 8. Key Insights

1. **Buffer allocation is a hidden cost**: First-call allocation can add 5-10µs
2. **XCD topology matters**: MI355X's 8 XCDs benefit from aligned work distribution
3. **Memory bandwidth is the bottleneck**: Fusing operations reduces traffic
4. **Shape-specific tuning**: Different shapes need different strategies

---

*Analysis completed by Agent A3 (LFM2.5-Thinking 1.2B)*  
*Timestamp: 2026-03-14*


## Related
- [[OPTIMIZATION_SUMMARY|Optimization Summary]] (a1)
- [[OPTIMIZATION_REPORT|Optimization Report]] (a1)
- [[TUNING_REPORT|Tuning Report]] (a2)
- [[buffer_management_improvements|Buffer Management Improvements]] (a3)
- [[memory_layout_optimizations|Memory Layout Optimizations]] (a3)
- [[performance_projections|Performance Projections]] (a3)
