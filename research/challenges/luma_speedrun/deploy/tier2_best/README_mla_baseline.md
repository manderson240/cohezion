# Tier 2: MLA Baseline Kernel

## File
`mla_baseline.py`

## Strategy
**Standard aiter mla_decode_fwd**

Simple, proven baseline using aiter's MLA decode:

- A16W8/A8W8 routing based on KV size
- Standard API usage
- Reliable fallback

## Expected Performance
- **Baseline**: ~69.7 µs
- **Reliability**: HIGH

## Risk Level
**LOW** - Proven API

## Test Commands

```bash
# Test correctness
popcorn run mla_baseline.py --mode test --leaderboard amd-mla-decode

# Benchmark
popcorn run mla_baseline.py --mode benchmark --leaderboard amd-mla-decode

# Leaderboard submission
popcorn run mla_baseline.py --mode leaderboard --leaderboard amd-mla-decode
```

## Key Features
- Automatic A16W8/A8W8 selection
- Default fast_mode
- Standard reference implementation

## Success Criteria
- [ ] Passes correctness test
- [ ] Matches baseline performance
- [ ] Reliable fallback

## Notes
Use when custom kernels fail or for comparison.
