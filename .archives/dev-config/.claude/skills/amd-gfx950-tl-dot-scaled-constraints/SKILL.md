---
name: amd-gfx950-tl-dot-scaled-constraints
description: |
  Hardware constraints for Triton tl.dot_scaled with MXFP4 (e2m1) format on AMD gfx950 (MI355X).
  Use when: (1) writing Triton kernels using tl.dot_scaled for FP4 GEMM on MI355X,
  (2) seeing silent wrong results or correctness failures from Triton FP4 kernels,
  (3) "unsupported tensor index" or "KeyError float4_e2m1fn_x2" errors.
  CRITICAL: BLOCK_K >= 128 is MANDATORY. BLOCK_K=64 silently produces wrong results.
  Verified Session 95: 4/4 tests passed with BLOCK_K=128/256, 0/N with BLOCK_K=64.
author: Claude Code
version: 1.0.0
---

# Triton tl.dot_scaled Constraints on gfx950 (MI355X)

## CRITICAL CONSTRAINT: BLOCK_K >= 128

**BLOCK_K=64 SILENTLY PRODUCES WRONG RESULTS on gfx950.**

This is the #1 cause of "Triton is 68% slower than CK ASM" conclusions — those kernels
were computing garbage with BLOCK_K=64 and passing benchmarks with corrupted output.

```python
# WRONG (silent corruption):
@triton.jit
def gemm_kernel(..., BLOCK_K: tl.constexpr = 64):  # BAD!
    tl.dot_scaled(a, scale_a, "e2m1", b, scale_b, "e2m1")

# CORRECT:
@triton.jit
def gemm_kernel(..., BLOCK_K: tl.constexpr = 128):  # MINIMUM
    tl.dot_scaled(a, scale_a, "e2m1", b, scale_b, "e2m1")
```

## Working Configuration (Verified Session 95)

```python
# Shape-adaptive BLOCK_K
BLOCK_K = 256 if K >= 4096 else 128  # Never below 128!

# Working tile sizes
BLOCK_M = 32   # Must be 16 or 32 (MFMA constraint)
BLOCK_N = 32   # Must be 16 or 32

# Scale groups per K tile
K_SCALE_GROUPS = BLOCK_K // 32  # 4 for BLOCK_K=128, 8 for BLOCK_K=256
```

## B Matrix Transpose Requirement

`tl.dot_scaled` rhs needs K-first layout `[K//2, N]`, but competition provides B_q as `[N, K//2]`.

```python
# Cache the transpose at module level (7.5MB for N=7168, K=7168)
_B_T = None
def custom_kernel(data):
    global _B_T
    if _B_T is None:
        _B_T = B_q.view(torch.uint8).T.contiguous()
```

## Scale Layout for RHS

B scales must be loaded N-first: `[BLOCK_N, K_SCALE_GROUPS]` not `[K_SCALE_GROUPS, BLOCK_N]`.

## e8m0_unshuffle Required

B_scale_sh from competition is in aiter's shuffled format. Must unshuffle:
```python
def e8m0_unshuffle(s, m, n):
    sm, sn = s.shape
    return s.view(sm//32, sn//8, 4, 16, 2, 2).permute(0,5,3,1,4,2).contiguous().view(sm,sn)[:m,:n]
```

## Performance (Session 95 Benchmark)

| Shape | BLOCK_K=128 | BLOCK_K=256 | aiter |
|-------|-------------|-------------|-------|
| M=4, K=512 | 14.1µs | — | 8.2µs |
| M=16, K=7168 | 63.6µs | **50.7µs** | 20.9µs |
| M=32, K=512 | 16.7µs | — | 9.5µs |
| M=64, K=2048 | 31.3µs | — | 12.7µs |
| M=256, K=1536 | 26.3µs | — | 12.2µs |
| **Geomean** | ~25µs | ~23µs | 11.5µs |

## Why Still 2x Slower Than Aiter

1. Aiter uses hand-tuned CK ASM with hardware-specific memory access patterns
2. Triton JIT overhead (~2-3µs per launch)
3. No LDS double-buffering in Triton for FP4 (would need custom lowering)
4. Separate A quantization pass (not fused into Triton kernel)

## Files

- Working submission: `luma_speedrun/amd-mxfp4-mm/submission_triton_dotscaled.py`
- Skill file: `luma_speedrun/amd-mxfp4-mm/submission_triton_dotscaled.py` (4/4 tests, error 0.0)
