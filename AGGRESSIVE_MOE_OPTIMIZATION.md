# Aggressive MoE Optimization Plan

## Current State
- **Best achieved**: 93.4μs
- **Target (Rank 1)**: 70.47μs (or 109.79μs - conflicting data)
- **Gap**: Need ~22.93μs improvement (25%)

## Potential Optimizations

### 1. Block Size Tuning
Current: Unknown (default)
Target: block_m=128 or 256
Expected gain: 10-15μs

### 2. Split-K Parallelism
Current: splitK=0
Target: splitK=1, 2, or 4
Expected gain: 5-10μs

### 3. Direct CK Dispatch (bypass fused_moe)
Load CK kernels directly via load_inline
Expected gain: 15-20μs (eliminates Python overhead)

### 4. LDS Optimization
Use local data share for intermediate results
Expected gain: 5-10μs

### 5. Stream Optimization
Use multiple HIP streams for overlapping
Expected gain: 3-5μs

## Implementation Priority

1. **High Impact**: Direct CK dispatch (Phase 2)
2. **Medium Impact**: Block size tuning
3. **Medium Impact**: Split-K
4. **Low Impact**: LDS optimization (complex)

## Direct CK Dispatch Plan

From CodeExpert skill (popcorn-cli):
```python
# Load CK .so files from /home/runner/aiter/hsa/gfx950/
# Call CK kernels directly via load_inline
# Bypass fused_moe entirely
```

This is the most promising path for 70μs.
