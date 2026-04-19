# Tier 2: MoE Baseline Kernel

## File
`moe_baseline.py`

## Strategy
**Proven fused_moe with Adaptive KSPLIT**

Standard aiter `fused_moe` with default adaptive KSPLIT:

- Adaptive KSPLIT based on token distribution
- No experimental parameters
- Most reliable baseline

## Expected Performance
- **Baseline**: ~154 µs
- **Variance**: ±10 µs depending on shape
- **Reliability**: HIGH - proven API

## Risk Level
**LOW** - Standard API usage

## Test Commands

```bash
# Test correctness
popcorn run moe_baseline.py --mode test --leaderboard amd-moe-mxfp4

# Benchmark
popcorn run moe_baseline.py --mode benchmark --leaderboard amd-moe-mxfp4

# Leaderboard submission
popcorn run moe_baseline.py --mode leaderboard --leaderboard amd-moe-mxfp4
```

## Key Parameters
- Default adaptive KSPLIT
- `doweight_stage1=False` (correctness)
- Standard fused_moe path

## Success Criteria
- [ ] Passes correctness test
- [ ] Matches ~154 µs baseline
- [ ] Reliable fallback option

## Notes
Use this as the safe fallback if other variants fail.
