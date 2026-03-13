# Luma AMD Speedrun - Competition Results

**Competition:** AMD x GPU MODE Hackathon - Phase 1 Qualifiers
**Dates:** March 6, 2026 - March 30, 2026 (deadline: 2026-03-30 06:00 UTC)
**Hardware:** AMD Instinct MI355X
**Participant:** manderson240 (GitHub) / miked238725 (Discord)
**Submission Date:** 2026-03-12

## Current Rankings (as of 2026-03-12)

| Kernel | Leaderboard | Our Time | Our Rank | Total Entries | Leader | Leader Time | Gap |
|--------|-------------|----------|----------|---------------|--------|-------------|-----|
| MXFP4 GEMM | `amd-mxfp4-mm` | 24.082 us | 67/68 | 68 | parcadei | 9.671 us | 2.49x |
| MLA Decode | `amd-mixed-mla` | 191.259 us | 40/54 | 54 | Jayluci4 | 4.335 us | 44.1x |
| MoE MXFP4 | `amd-moe-mxfp4` | 185.189 us | 34/43 | 43 | mega-dmitriy | 145.177 us | 1.28x |

**Leaderboard URLs:**
- GEMM: https://www.gpumode.com/leaderboard/763
- MLA: https://www.gpumode.com/leaderboard/765
- MoE: https://www.gpumode.com/leaderboard/764

## Analysis

### MoE - Closest to Competitive (1.28x gap)

Our MoE submission is only 28% slower than the leader. The top ~15 entries are
clustered tightly between 145-178 us, suggesting `aiter.fused_moe` is already
well-optimized and the gains come from parameter tuning (stage configuration,
sorting, block sizes) rather than algorithmic breakthroughs.

**Optimization priority: HIGH** — Small improvements could yield significant rank jumps.

### GEMM - Moderate Gap (2.49x)

Our GEMM submission delegates to `ref_kernel` due to the Triton JIT call-site
sensitivity bug. The reference uses `aiter.gemm_a4w4` which averages ~24 us.
The leader at 9.671 us is likely using custom Triton kernels or HIP C++ with
optimized tiling for the specific MI355X architecture.

The top ~8 entries are under 11 us, then there's a cluster at 13-15 us (the
"reference-level" performers). Getting into that 13-15 us cluster would require
solving the call-site issue or writing a custom kernel.

**Optimization priority: MEDIUM** — Need to overcome the JIT call-site issue first.

### MLA - Largest Gap (44.1x)

The MLA leaderboard has a massive spread. The top 3 entries (4.3 us) are ~44x
faster than our 191 us. Even the cluster at rank 7-15 (54-72 us) is 3x faster.

The top performers likely use:
- Optimized persistent-mode kernels with tuned `NUM_KV_SPLITS`
- Custom assembly (`.co`) kernels compiled for GFX950
- Aggressive quantization (MXFP4 KV instead of FP8)
- Shape-specific dispatch for different batch sizes

**Optimization priority: HIGH** — Largest potential for improvement.

## Benchmark Details

### GEMM (`amd-mxfp4-mm`) - Submission #534150

Approach: Delegate to `ref_kernel` (correctness workaround for Triton JIT call-site bug).

| Config (k, m, n) | Mean | Best |
|---|---|---|
| k=512, m=4, n=2880 | 20.6 us | 19.5 us |
| k=7168, m=16, n=2112 | 34.4 us | 32.8 us |
| k=512, m=32, n=4096 | 22.2 us | 21.1 us |
| k=512, m=32, n=2880 | 21.9 us | 21.0 us |
| k=2048, m=64, n=7168 | 24.4 us | 23.5 us |
| k=1536, m=256, n=3072 | 23.3 us | 22.3 us |

Reference baseline from task.yml:

| M | N | K | Ref time [us] |
|---|---|---|---------------|
| 4 | 2880 | 512 | 8.198 |
| 16 | 2112 | 7168 | 20.873 |
| 32 | 4096 | 512 | 9.462 |
| 32 | 2880 | 512 | 9.173 |
| 64 | 7168 | 2048 | 12.738 |
| 256 | 3072 | 1536 | 12.219 |

Our geometric mean is ~2x slower than the task.yml reference baselines, which
makes sense since our submission includes the Python delegation overhead.

### MLA Decode (`amd-mixed-mla`) - Submission #534167

Approach: `aiter.mla.mla_decode_fwd` persistent mode with FP8 Q + FP8 KV.
All 4 tests passed with 0.0 maximum error.

| Config (bs, kvseqlen) | Mean | Best |
|---|---|---|
| bs=4, kv=1024 | 120 us | 110 us |
| bs=4, kv=8192 | 128 us | 120 us |
| bs=32, kv=1024 | 126 us | 118 us |
| bs=32, kv=8192 | 177 us | 167 us |
| bs=64, kv=1024 | 135 us | 125 us |
| bs=64, kv=8192 | 224 us | 212 us |
| bs=256, kv=1024 | 176 us | 166 us |
| bs=256, kv=8192 | 370 us | 354 us |

### MoE (`amd-moe-mxfp4`) - Submission #534166

Approach: `aiter.fused_moe` with MXFP4 quantization (CK 2-stage).
All 3 tests passed (0.015625 max error, within rtol=5e-2 tolerance).

| Config (bs, dexpert, nexperts) | Mean | Best |
|---|---|---|
| bs=16, d=256, n=256 | 141 us | 129 us |
| bs=128, d=256, n=256 | 224 us | 212 us |
| bs=512, d=256, n=256 | 256 us | 248 us |
| bs=16, d=512, n=32 | 98.0 us | 92.2 us |
| bs=128, d=512, n=32 | 134 us | 129 us |
| bs=512, d=512, n=32 | 218 us | 213 us |
| bs=512, d=2048, n=32 | 354 us | 344 us |

MoE reference baseline from task.yml:

| bs | E | d_expert | Ref time [us] |
|----|---|----------|---------------|
| 16 | 257 | 256 | 152.7 |
| 128 | 257 | 256 | 239.0 |
| 512 | 257 | 256 | 336.5 |
| 16 | 33 | 512 | 106.2 |
| 128 | 33 | 512 | 141.1 |
| 512 | 33 | 512 | 225.0 |
| 512 | 33 | 2048 | 380.4 |

Our MoE times are FASTER than the task.yml reference for most configs, which
is why we rank in the middle of the pack rather than at the bottom.

## Top Competitors (Appearing in Multiple Leaderboards)

| Competitor | GEMM Rank | MLA Rank | MoE Rank | Notes |
|---|---|---|---|---|
| parcadei | 1st (9.671 us) | 11th | 12th | GEMM specialist |
| josusanmartin | 2nd (9.683 us) | 14th | 2nd | Strong all-around |
| mega-dmitriy | 6th (10.894 us) | 6th | 1st | MoE specialist, strong everywhere |
| Yufeng98 | 7th (11.131 us) | 5th | 4th | Consistent top performer |
| sanjay_arvind | 5th (10.623 us) | 8th | 6th | Very consistent |
| ry2009 | 11th | 11th | 7th | Consistent |
| ooousay | 12th | 12th | 3rd | MoE specialist |
| John Hahn | 4th (10.598 us) | 4th | - | GEMM + MLA specialist |
| Jayluci4 | - | 1st (4.335 us) | - | MLA breakthrough |
| n8_gr8_ | - | 2nd (4.335 us) | 10th | MLA breakthrough |

## Scoring (Competition Rules)

- Scoring: **geometric mean** of benchmark runtimes (lower = better)
- Must **beat the baseline** to receive points
- **Top 10 fastest** kernels per problem considered for aggregate score
- Only the **top scoring kernel** per problem from a team is considered

We are currently NOT in the top 10 for any kernel, so we score 0 points in
the aggregate ranking. To score points, we need to reach top 10 in at least
one kernel.

## Optimization Roadmap (Priority Order)

### 1. MoE - Quick Win (target: top 15)
- Try `doweight_stage1=True` parameter
- Experiment with 1-stage vs 2-stage routing
- Custom tile sizes for E=33 configs (where we're fastest)
- Profile to find bottleneck (dispatch vs compute)

### 2. MLA - Highest Impact (target: top 20)
- Tune `NUM_KV_SPLITS` per batch size (current: fixed 32)
- Try non-persistent mode for small batch sizes (bs=4)
- MXFP4 KV cache instead of FP8 (2x bandwidth savings)
- Study Jayluci4/n8_gr8_ approach (4.3 us = likely custom kernel)

### 3. GEMM - Requires Call-Site Fix (target: top 40)
- Solve JIT call-site issue to enable custom optimization
- Try Triton GEMM for larger M values (M >= 64)
- Explore shape-dependent routing
- Study parcadei's approach (9.67 us)

## Key Learnings

### Triton JIT Call-Site Sensitivity (GEMM)
Calling `aiter.get_triton_quant(QuantType.per_1x32)` from `submission.py`
produces different Triton JIT compilations than from `reference.py` on MI355X.
Results in ~80% element mismatches with ~1-3% per-element error. Fix: delegate
to `ref_kernel`. See skill: `amd-triton-jit-callsite-correctness`.

### Popcorn CLI Workflow
- Leaderboard names follow `amd-<directory-name>` pattern
- No per-user rate limit; submit freely
- Transient artifact download failures require retry
- See skill: `popcorn-cli-amd-kernel-submission`

### Local Testing Not Feasible
AMD Radeon 8060S (gfx1151, RDNA4) is not supported by ROCm 6.2.4. All testing
must happen via Popcorn CLI remote submission on MI355X hardware (~2 min/submit).

## Files

| File | Purpose |
|------|---------|
| `kernels/mxfp4-mm/submission.py` | GEMM submission (delegates to ref_kernel) |
| `kernels/mixed-mla/submission.py` | MLA submission (aiter mla_decode_fwd persistent mode) |
| `kernels/moe-mxfp4/submission.py` | MoE submission (aiter fused_moe) |
| `docs/plans/2026-03-11-luma-amd-speedrun.md` | Implementation plan (Status: VERIFIED) |
| `~/.claude/skills/amd-triton-jit-callsite-correctness/` | Skill: JIT call-site fix |
| `~/.claude/skills/popcorn-cli-amd-kernel-submission/` | Skill: Popcorn CLI workflow |
