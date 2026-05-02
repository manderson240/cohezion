# Tier 2: MLA FastMode Kernel

## File
`mla_fastmode.py`

## Strategy
**Fast Mode A/B Test for MLA**

Tests the `fast_mode` parameter in mla_decode_fwd:

- `fast_mode=False`: Faster on MI355X (verified)
- Metadata overhead reduction
- Simple parameter toggle

## Expected Performance
- **fast_mode=True**: ~69.7 µs
- **fast_mode=False**: ~67.8 µs (verified faster on MI355X)
- **Improvement**: ~3% (small but consistent)

## Risk Level
**LOW** - Single parameter change

## Test Commands

```bash
# Test correctness
popcorn run mla_fastmode.py --mode test --leaderboard amd-mla-decode

# Benchmark
popcorn run mla_fastmode.py --mode benchmark --leaderboard amd-mla-decode

# Leaderboard submission
popcorn run mla_fastmode.py --mode leaderboard --leaderboard amd-mla-decode
```

## Key Parameter
- `fast_mode=False` - Despite name, faster on MI355X

## Success Criteria
- [ ] Passes correctness test
- [ ] Shows 2-5% improvement
- [ ] Consistent across shapes

## Notes
Counter-intuitive: fast_mode=False is faster. This is a MI355X-specific quirk.
