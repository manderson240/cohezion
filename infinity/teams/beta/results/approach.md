# Team Beta: Breaking the MoE AITER Ceiling

## Status Update (Hour 0-6)

**Current State**: Created optimized aiter-based submission with shape-aware dispatch
**Target**: <130µs (20% improvement from 155µs baseline)
**Strategy**: John Hahn-inspired shape-aware tuning

## Implementation

### Submission: `submission.py`

Uses shape-aware dispatch based on estimated tokens per expert:

```python
if estimated_m < 10:    # Extreme sparsity (S2-like)
    KSPLIT=8, BLOCK_M=32
elif estimated_m < 25: # Sparse
    KSPLIT=4, BLOCK_M=64
elif estimated_m < 80: # Moderate
    KSPLIT=2
else:                    # Dense
    Default CK tuning
```

### Optimizations Applied

1. **AITER_USE_OPUS_MOE_SORTING=1**: Improved expert dispatch ordering
2. **AITER_USE_NT=1**: Non-temporal stores for better memory bandwidth
3. **AITER_BYPASS_TUNE_CONFIG=1**: Use custom KSPLIT/BLOCK_M values
4. **State tracking**: Only update environment when config changes

## Benchmark Shape Analysis

| Shape | Tokens | Experts | TopK | Est_M | Config | Expected |
|-------|--------|---------|------|-------|--------|----------|
| S1 | 16 | 257 | 9 | ~0.56 | KSPLIT=8, BLOCK_M=32 | ~140µs |
| S2 | 128 | 257 | 9 | ~4.5 | KSPLIT=8, BLOCK_M=32 | ~150µs |
| S3 | 512 | 257 | 9 | ~18 | KSPLIT=4, BLOCK_M=64 | ~155µs |
| S4 | 16 | 33 | 9 | ~4.4 | KSPLIT=8, BLOCK_M=32 | ~120µs |
| S5 | 128 | 33 | 9 | ~35 | KSPLIT=2 | ~130µs |
| S6 | 512 | 33 | 9 | ~140 | Default | ~140µs |

## Path to <130µs

### Option 1: Full Triton Kernel (High Risk/Reward)

Create custom Triton kernel bypassing aiter entirely:
- Fused: token sorting + quant + GEMM1 + SiLU + GEMM2
- Shape-aware autotune
- Persistent kernel design

**Challenge**: Complex MXFP4 handling, scale layout, weight shuffling

### Option 2: Hybrid Approach (Medium Risk)

Use Triton for specific shapes (S2, S4) where aiter struggles:
- Keep aiter for dense shapes (S3, S5, S6)
- Custom Triton for sparse shapes (S1, S2, S4)

### Option 3: Further AITER Tuning (Lower Risk)

- Fine-tune BLOCK_M per shape
- Experiment with num_stages/num_warps
- Profile-guided optimization

## Next Steps (Hours 6-12)

1. **Test current submission** for correctness
2. **Benchmark** to verify performance improvement
3. **Profile** to identify remaining bottlenecks
4. **Iterate** on config values based on results

## Files Created

- `/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/moe-mxfp4/submission.py` - Optimized aiter submission
- `/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/moe-mxfp4/submission_beta_triton.py` - Triton kernel skeleton (WIP)

---

**Status**: Phase 1 Complete - Submission ready for testing
**Last Updated**: 2026-03-16
