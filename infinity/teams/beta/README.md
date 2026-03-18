# Team Beta - MoE Optimization

**Mission**: Break through aiter ceiling to reach Top 10 (155μs → <130μs)

**Leaderboard**: amd-moe-mxfp4
**Current Rank**: ~14th
**Target Rank**: Top 10
**Current Score**: ~155μs
**Target Score**: <130μs
**#1 Score**: 114.61μs (John Hahn)

## The Problem

The aiter.fused_moe library has a ceiling of ~155μs. John Hahn achieved 114.61μs with only 35 submissions by using a **custom Triton kernel** that bypasses aiter entirely.

The 35% gap is entirely Python/library overhead elimination, not algorithmic improvement.

## The Solution

**Custom Triton MoE kernel** that:
- Bypasses `aiter.fused_moe` entirely
- Single fused kernel replacing 3+ separate calls
- Fuses: token sorting → quant → GEMM1 → SiLU → GEMM2 → weights
- Shape-aware autotune: different configs for each benchmark shape
- Persistent kernel design
- Handles all 6 benchmark shapes:
  - S2 (hardest): 128 tokens, 256 experts, est_m=4 → BLOCK_M=32, SPLIT_K=8
  - S5 (largest): 2048 tokens, 8 experts, est_m=512 → BLOCK_M=128, SPLIT_K=0

## Key Resources

- Reference: `/research/challenges/luma_amd_speedrun/kernels/moe-mxfp4/reference.py`
- Task spec: `/research/challenges/luma_amd_speedrun/kernels/moe-mxfp4/task.yml`
- John Hahn analysis: See `john_hahn_technique_analysis.md`

## Success Criteria

- [ ] Custom Triton kernel compiles and runs
- [ ] Correctness tests pass
- [ ] Performance <130μs (20% improvement)
- [ ] Document approach in `results/approach.md`

## Timeline

**24 hours** to first working submission

## Coordination

- Daily sync with other teams via `#coordination` channel
- Share learnings in shared vault
- Escalate blockers immediately

**Let's crack the MoE code.** 🎯
