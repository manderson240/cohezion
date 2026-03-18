# Team Gamma: Pure Triton MXFP4 GEMM Approach

## Mission
Reach GEMM Top 10 by achieving <10µs (25% improvement from current 13µs).

## Current State Analysis
- **Current**: HIP + aiter = 13µs (Rank ~60)
- **Target**: <10µs (Top 10)
- **Leader**: parcadei = 8.75µs with pure Triton
- **Gap**: 50% slower, need 4.25µs improvement

## Key Insight
The performance gap comes from:
1. Python API overhead (~40µs → 0µs with pure Triton)
2. Memory transfers (~30µs → ~15µs with fused kernel)
3. Kernel launch overhead (~15µs → ~5µs with single kernel)

## Strategy: Pure Triton with tl.dot_scaled

### Architecture
```
Input: bf16 A [M, K], pre-quantized B [N, K//2] fp4x2
  ↓
Preprocess B (cached):
  - Transpose B from [N, K//2] to [K//2, N]
  - Unshuffle B_scale from shuffled to linear [N, K//32]
  ↓
Fused Kernel (per tile):
  1. Load A bf16 [BLOCK_M, BLOCK_K]
  2. Inline quantize A to MXFP4 (fp4x2 + e8m0 scales)
  3. Load B fp4x2 [BLOCK_K//2, BLOCK_N]
  4. Load B_scale e8m0 [BLOCK_N, BLOCK_K//32]
  5. tl.dot_scaled(A_fp4, A_scale, B_fp4, B_scale)
  6. Accumulate to fp32
  ↓
Output: bf16 C [M, N]
```

### Key Optimizations

1. **Inline MXFP4 Quantization**
   - Bit-exact match to aiter C++ backend
   - Per-1x32 group scaling with E8M0 format
   - Pack adjacent FP4 values into fp4x2 bytes
   - No separate quantization kernel launch

2. **tl.dot_scaled Hardware Acceleration**
   - gfx950 MI355X native MXFP4 GEMM instruction
   - Fused dequant + multiply + accumulate
   - Proper scale layout: LHS row-major, RHS N-first

3. **Shape-Specific Block Configurations**
   - M=4: BLOCK_M=16, BLOCK_N=128/256, high parallelism
   - M=16: BLOCK_M=32, BLOCK_N=128, balanced
   - M=32/64: BLOCK_M=32/64, BLOCK_N=128/256
   - M=256: BLOCK_M=64/128, BLOCK_N=128/256, compute-bound

4. **Group-M Swizzle**
   - Improves L2 cache locality across CUs
   - Groups M-blocks to reduce cache thrashing

5. **Pre-transposed B**
   - Eliminates CPU-side transpose (~5µs)
   - B stored as [K//2, N] for coalesced access

6. **Autotune**
   - Grid search over block sizes, warps, stages
   - Key=["M", "N", "K"] for shape-specific tuning

## Implementation

### File: `submission_gamma_triton.py`

**Components:**
1. `_mxfp4_quant_tile()`: Inline quantization (Triton JIT)
2. `_unshuffle_e8m0_kernel()`: Scale unshuffling (Triton JIT)
3. `_fused_mxfp4_gemm_kernel()`: Main GEMM kernel with autotune
4. `_get_preprocessed_b()`: B preprocessing with caching
5. `custom_kernel()`: Entry point

### Block Size Selection

| M | BLOCK_M | BLOCK_N | BLOCK_K | num_warps | num_stages |
|---|---------|---------|---------|-----------|------------|
| 4 | 16 | 128/256 | 128/256 | 4-8 | 1-3 |
| 16 | 32 | 128/256 | 128/256 | 4-8 | 1-3 |
| 32 | 32/64 | 128/256 | 128/256 | 4-8 | 2-3 |
| 64 | 64 | 128/256 | 128/256 | 4-8 | 2-3 |
| 256 | 64/128 | 128/256 | 128/256 | 8 | 2-3 |

## Expected Performance

Based on Helion-generated kernel analysis:
- **M=4, N=2880, K=512**: ~6-8µs (small M, high parallelism)
- **M=16, N=2112, K=7168**: ~12-15µs (largest K, memory bound)
- **M=32, N=4096, K=512**: ~7-9µs (balanced)
- **M=64, N=7168, K=2048**: ~10-12µs (medium M)
- **M=256, N=3072, K=1536**: ~9-11µs (large M, compute bound)

**Geomean target**: <10µs

## Risks & Mitigations

1. **Correctness**: Bit-exact MXFP4 quantization matching aiter
   - Mitigation: Use proven quantization logic from submission_fused_triton.py

2. **Scale Layout**: gfx950 requires N-first scale layout for RHS
   - Mitigation: Verify B_scale is [N, K//32] not [K//32, N]

3. **Autotune Overhead**: First call compiles many configs
   - Mitigation: Acceptable for competition (one-time cost)

4. **Split-K**: Not implemented (may hurt small M performance)
   - Mitigation: Use small BLOCK_M with high parallelism

## Next Steps

1. [ ] Test kernel compilation (syntax check)
2. [ ] Run correctness tests against reference
3. [ ] Benchmark on competition shapes
4. [ ] Tune autotune configs based on results
5. [ ] Submit to leaderboard

## References

- `submission_fused_triton.py`: Proven inline quantization
- `submission_helion_*.py`: Helion-generated tl.dot_scaled patterns
- `reference.py`: aiter reference implementation
- `task.yml`: Competition shapes and requirements
