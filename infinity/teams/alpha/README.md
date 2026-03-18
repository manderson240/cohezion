# Team Alpha - MLA Emergency Response

**Mission**: Fix the 16x performance gap in MLA (69μs → <20μs)

**Leaderboard**: amd-mixed-mla
**Current Rank**: ~22nd
**Target Rank**: Top 10
**Current Score**: ~69μs
**Target Score**: <20μs (still 4x off #1, but closer)
**#1 Score**: 4.33μs (n8_gr8_)

## The Problem

The aiter 3-stage pipeline has ~100-150μs fixed overhead:
1. `get_mla_metadata_v1()` — ~5-20μs
2. `mla_decode_stage1_asm_fwd()` — ~70-120μs
3. `mla_decode_reduce_fwd()` — ~10-30μs

For small decode (bs=4, kv=1k), actual attention compute is <10μs. The pipeline overhead dominates entirely.

## The Solution

**Custom Triton Flash Attention kernel** that:
- Single kernel launch (not 3-stage)
- Fuses: score → softmax → value accumulation
- Handles K≠V dims: 576 (QK) vs 512 (V)
- Optimized for GEMV (qseqlen=1) — don't pad Q to 16
- Uses online softmax (Flash Attention v2 pattern)
- Persistent kernel design

## Key Resources

- Reference: `/research/challenges/luma_amd_speedrun/kernels/mixed-mla/reference.py`
- Task spec: `/research/challenges/luma_amd_speedrun/kernels/mixed-mla/task.yml`
- #1 Analysis: See `john_hahn_intelligence_analysis.md`

## Success Criteria

- [ ] Custom Triton kernel compiles and runs
- [ ] Correctness tests pass
- [ ] Performance <20μs (4x improvement)
- [ ] Document approach in `results/approach.md`

## Timeline

**24 hours** to first working submission

## Coordination

- Daily sync with other teams via `#coordination` channel
- Share learnings in shared vault
- Escalate blockers immediately

**Let's fix the MLA disaster.** 🔥
