# Tier 1: GEMM Breakthrough Kernel

## File
`gemm_breakthrough.py`

## Strategy
**Fused Prologue Quantization + MFMA GEMM**

Addresses the fundamental bottleneck: quantization (~26 µs) dominates actual GEMM (~7-10 µs). Custom HIP kernel:

1. **Inline FP4 Unpacking**: Dequant on-the-fly during GEMM
2. **MFMA Integration**: AMD MFMA intrinsics for matrix multiply
3. **E8M0 Scale Application**: Applies scales inline
4. **BF16 Output**: Native BF16 accumulation

## Expected Performance
- **Baseline (aiter gemm_a4w4)**: ~13.4 µs
- **Target**: 4.3 µs (3.1x improvement to match leader)
- **Potential**: Up to 50% improvement if fused quantization works

## Risk Level
**HIGH** - Complex kernel with custom FP4 handling

## Test Commands

```bash
# Test correctness
popcorn run gemm_breakthrough.py --mode test --leaderboard amd-mxfp4-mm

# Benchmark
popcorn run gemm_breakthrough.py --mode benchmark --leaderboard amd-mxfp4-mm

# Leaderboard submission
popcorn run gemm_breakthrough.py --mode leaderboard --leaderboard amd-mxfp4-mm
```

## Success Criteria
- [ ] Passes correctness test
- [ ] Shows improvement over 13.4 µs baseline
- [ ] FP4 unpacking produces correct values

## Known Issues
- FP4 unpacking logic must match reference exactly
- BLOCK_K >= 128 constraint for MFMA
- Falls back to gemm_a4w4 on failure
