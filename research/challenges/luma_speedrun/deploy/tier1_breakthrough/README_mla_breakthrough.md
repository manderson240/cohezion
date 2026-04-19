# Tier 1: MLA Breakthrough Kernel

## File
`mla_breakthrough.py`

## Strategy
**Flash Attention-Style Fused Kernel for 576/512 Latent Split**

This kernel addresses the fundamental MLA challenge: QK dim (576) ≠ V dim (512). Custom HIP kernel using load_inline:

1. **Direct FP4 Dequantization**: Reads MXFP4 KV cache directly
2. **576/512 Split Handling**: Handles asymmetric latent attention
3. **Multi-Split-K**: Parallelism across 304 CUs
4. **FP4 LUT**: Fast lookup table for FP4→FP32 conversion

## Expected Performance
- **Baseline (aiter mla_decode_fwd)**: ~69.7 µs
- **Target**: 33 µs (2.1x improvement to match leader)
- **Potential**: 50% improvement if custom kernel works

## Risk Level
**HIGH** - Complex kernel with asymmetric dimensions

## Test Commands

```bash
# Test correctness
popcorn run mla_breakthrough.py --mode test --leaderboard amd-mla-decode

# Benchmark
popcorn run mla_breakthrough.py --mode benchmark --leaderboard amd-mla-decode

# Leaderboard submission
popcorn run mla_breakthrough.py --mode leaderboard --leaderboard amd-mla-decode
```

## Success Criteria
- [ ] Passes correctness test
- [ ] Shows improvement over 69.7 µs baseline
- [ ] Handles 576/512 dimension split correctly

## Known Issues
- Complex FP4 dequantization may have precision issues
- Latent attention math is non-trivial
- Falls back to mla_decode_fwd on failure
