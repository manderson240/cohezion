# Tier 2: MoE Dispatch1 + Mask Kernel

## File
`moe_dispatch1_mask.py`

## Strategy
**Expert Masking with Dispatch Policy 1**

Combines `moe_sorting_dispatch_policy=1` with expert masking:

- Filters experts based on topk_ids
- Reduces active expert computation
- Policy=1 handles sorting differently

## Expected Performance
- **Baseline**: ~154 µs
- **Target**: 140-150 µs (5-10% improvement)
- **Potential**: Reduced compute for sparse expert activation

## Risk Level
**MEDIUM** - Expert masking adds complexity

## Test Commands

```bash
# Test correctness
popcorn run moe_dispatch1_mask.py --mode test --leaderboard amd-moe-mxfp4

# Benchmark
popcorn run moe_dispatch1_mask.py --mode benchmark --leaderboard amd-moe-mxfp4

# Leaderboard submission
popcorn run moe_dispatch1_mask.py --mode leaderboard --leaderboard amd-moe-mxfp4
```

## Key Features
- Expert mask computation from topk_ids
- Combined with dispatch_policy=1 benefits
- Falls back to standard fused_moe

## Success Criteria
- [ ] Passes correctness test
- [ ] Shows 5-10% improvement
- [ ] Expert masking works correctly

## Notes
Best for workloads with sparse expert activation patterns.
