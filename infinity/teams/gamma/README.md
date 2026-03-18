# Team Gamma - GEMM Speedup

**Mission**: Reach Top 10 with pure Triton (13μs → <10μs)

**Leaderboard**: amd-mxfp4-mm
**Current Rank**: ~60th
**Target Rank**: Top 10
**Current Score**: ~13μs
**Target Score**: <10μs
**#1 Score**: 8.75μs (parcadei)

## The Problem

The aiter.gemm_a4w4_asm has a ceiling of ~24μs. Our HIP hybrid gets ~13μs. But parcadei achieved 8.75μs with **pure Triton** using `tl.dot_scaled` for MXFP4.

The 50% gap comes from:
- Python API overhead (~40μs in aiter, 0μs in pure Triton)
- Memory transfers (~30μs → ~15μs with fusion)
- Kernel launch overhead (~15μs → ~5μs)

## The Solution

**Pure Triton GEMM kernel** that:
- Uses `tl.dot_scaled` for MXFP4 (not separate quant step)
- Fuses: quant + GEMM + scale application in one kernel
- Shape-specific blocks:
  - M=4 → BLOCK_M=16, BLOCK_N=128, BLOCK_K=128
  - M=16 → BLOCK_M=32, BLOCK_N=128, BLOCK_K=128
  - M=256 → BLOCK_M=128, BLOCK_N=256, BLOCK_K=128
- Split-K for small M (4, 16): SPLIT_K=4-8
- No split for large M (256): SPLIT_K=0

## Key Resources

- Reference: `/research/challenges/luma_amd_speedrun/kernels/mxfp4-mm/reference.py`
- Task spec: `/research/challenges/luma_amd_speedrun/kernels/mxfp4-mm/task.yml`
- Helion generator: `/research/challenges/luma_amd_speedrun/helion_gemm_gen.py`

## Success Criteria

- [ ] Pure Triton kernel compiles and runs
- [ ] Correctness tests pass
- [ ] Performance <10μs (25% improvement)
- [ ] Document approach in `results/approach.md`

## Timeline

**24 hours** to first working submission

## Coordination

- Daily sync with other teams via `#coordination` channel
- Share learnings in shared vault
- Escalate blockers immediately

**Let's optimize GEMM to the max.** ⚡
