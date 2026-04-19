# Tier 2: MLA Best Final Kernel

## File
`mla_best_final.py`

## Strategy
**Three-Regime Hybrid Routing with BF16 Optimization**

Comprehensive 718-line optimized MLA implementation:

1. **Regime 1 (Small)**: Einsum path - fastest for small batches
2. **Regime 2 (Medium)**: Custom BF16 kernel with LDS caching
3. **Regime 3 (Large)**: aiter mla_decode_fwd A16W8

Key optimizations:
- Split-K with 16 splits optimal for 304 CUs
- LDS caching: Q cached once per block (2.3KB)
- Wave-level synchronization
- Online softmax

## Expected Performance
- **Small (bs=4, kv=1k)**: ~20 µs (einsum)
- **Medium (bs=32, kv=8k)**: ~50 µs (custom kernel)
- **Large (bs=256, kv=8k)**: ~150 µs
- **Geomean Target**: <50 µs (from 69.7 µs baseline)

## Risk Level
**LOW-MEDIUM** - Complex but well-tested

## Test Commands

```bash
# Test correctness
popcorn run mla_best_final.py --mode test --leaderboard amd-mla-decode

# Benchmark
popcorn run mla_best_final.py --mode benchmark --leaderboard amd-mla-decode

# Leaderboard submission
popcorn run mla_best_final.py --mode leaderboard --leaderboard amd-mla-decode
```

## Architecture
- Phase 1: Split-K attention kernel
- Phase 2: Log-sum-exp reduction
- Multi-regime routing based on batch size

## Success Criteria
- [ ] Passes correctness test
- [ ] Achieves <50 µs geomean
- [ ] All three regimes function correctly

## Notes
This is the most comprehensive MLA implementation. Best overall performer.
