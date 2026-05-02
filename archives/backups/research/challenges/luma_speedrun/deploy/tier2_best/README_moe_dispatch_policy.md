# Tier 2: MoE Dispatch Policy Kernel

## File
`moe_dispatch_policy.py`

## Strategy
**moe_sorting_dispatch_policy=1 Optimization**

Uses the undocumented `moe_sorting_dispatch_policy=1` parameter which changes expert token sorting strategy:

- Reduces worst-case shapes by **37%** (695→436 µs)
- Cost: ~5 µs overhead on best shapes
- Different sorting/dispatch path internally

## Expected Performance
- **Best case**: ~154 µs (same as baseline)
- **Worst case**: ~436 µs (vs 695 µs baseline) - 37% improvement
- **Average**: Modest improvement on skewed expert distributions

## Risk Level
**LOW** - Simple parameter change on proven fused_moe API

## Test Commands

```bash
# Test correctness
popcorn run moe_dispatch_policy.py --mode test --leaderboard amd-moe-mxfp4

# Benchmark
popcorn run moe_dispatch_policy.py --mode benchmark --leaderboard amd-moe-mxfp4

# Leaderboard submission
popcorn run moe_dispatch_policy.py --mode leaderboard --leaderboard amd-moe-mxfp4
```

## Key Parameters
- `moe_sorting_dispatch_policy=1` - Alternative sorting strategy
- `doweight_stage1=False` - Required for correctness
- `QuantType.per_1x32` - Standard quantization

## Success Criteria
- [ ] Passes correctness test
- [ ] Shows improvement on worst-case shapes
- [ ] No regression on best-case shapes

## Notes
Verified in Session 91 (April 2026). Safe and reliable improvement.
