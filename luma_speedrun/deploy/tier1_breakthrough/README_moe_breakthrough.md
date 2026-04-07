# Tier 1: MoE Breakthrough Kernel

## File
`moe_breakthrough.py`

## Strategy
**Fused Quant+GEMM via Custom HIP Kernel**

This kernel attempts to bypass the API ceiling by using `load_inline` to compile a custom HIP kernel that fuses quantization with the MoE computation. Key features:

1. **LDS Bridge**: Fuses Stage 1+2 of MoE via shared memory
2. **Expert-Parallel Saturation**: Targets 304 CUs on MI355X
3. **Stream Synchronization**: Explicit CUDA stream handling
4. **Fallback to fused_moe**: If custom kernel fails, falls back to proven aiter API

## Expected Performance
- **Baseline (aiter fused_moe)**: ~154 µs
- **Target**: 107 µs (1.4x improvement to match leader)
- **Potential**: Up to 40% improvement if custom kernel works

## Risk Level
**HIGH** - load_inline may fail on runner due to compilation restrictions

## Test Commands

```bash
# Test correctness
popcorn run moe_breakthrough.py --mode test --leaderboard amd-moe-mxfp4

# Benchmark
popcorn run moe_breakthrough.py --mode benchmark --leaderboard amd-moe-mxfp4

# Leaderboard submission
popcorn run moe_breakthrough.py --mode leaderboard --leaderboard amd-moe-mxfp4
```

## Success Criteria
- [ ] Passes correctness test
- [ ] Shows improvement over 154 µs baseline
- [ ] Custom kernel executes without errors

## Known Issues
- Custom HIP kernel may fail to compile on runner
- Falls back to fused_moe if custom kernel fails
- May require gfx950 architecture flag
