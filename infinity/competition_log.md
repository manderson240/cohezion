---
title: "Luma AMD Speedrun - Competition Log"
date: 2026-03-15
status: in-progress
tags: [infinity, gpu-optimization]
aspect: thinker
---

# Luma AMD Speedrun - Competition Log

**Date**: 2026-03-15
**Status**: Leaderboard Submitted + Triton Development Active

## Current Rankings (manderson240)

| Kernel | Rank | Score | Gap to Top 10 |
|--------|------|-------|---------------|
| MoE | 14/61 | 1.55e-04 (~155µs) | ~3.4µs |
| GEMM | 75/95 | 2.06e-05 (~20.6µs) | ~10µs |
| MLA | 22/79 | 6.93e-05 (~69.3µs) | ~15µs |

## MoE Top 10 Analysis

| Rank | User | Score (µs) | Gap |
|------|------|------------|-----|
| 1 | John Hahn | 114.61 | -40µs |
| 2 | champagnepapi | 114.66 | -40µs |
| 3 | josusanmartin | 141.35 | -14µs |
| 10 | ry2009 | 151.59 | -3.4µs |
| **14** | **manderson240** | **155.00** | **baseline** |

## Strategy

**Phase 1**: ✅ Leaderboard submission (Rank 14 secured)
**Phase 2**: 🔄 Triton kernel development (target Rank 10)
**Phase 3**: 📚 Documentation and knowledge capture

## Key Learnings

1. **aiter ceiling**: ~155µs with direct dispatch
2. **John Hahn**: Uses custom Triton kernel (35 submissions vs 249)
3. **Gap to Rank 10**: Only 3.4µs - achievable with optimizations
4. **Gap to Rank 1**: 40µs - requires breakthrough

## Next Steps

1. Complete Triton MoE kernel
2. Test on runner
3. Iterate based on results
4. Document all techniques

## Files

- Current submission: `submission_direct_dispatch.py`
- Triton WIP: `submission_triton.py`
- Vault: `~/vaults/cohezion-vault/infinity/`

## Related
- [[RESEARCH_REPORT|Research Report]]
- [[CENTRAL_COMMAND|Central Command]]
