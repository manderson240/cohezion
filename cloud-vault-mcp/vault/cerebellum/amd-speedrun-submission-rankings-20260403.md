---
type: breakthrough
name: amd-speedrun-submission-rankings-20260403
description: "Power-ranked submission variants for AMD x GPU MODE E2E Model Speedrun Phase 1"
created: 2026-04-03
title: "AMD Speedrun Submission Rankings — Finalist Sprint Analysis"
date: 2026-04-03
tags: [cerebellum, amd, mi355x, competition, luma-speedrun, rankings, gpu-optimization]
aspect: knower
neural:
  activation: 0.91
  stage: mature
  synapse_in: 3
  synapse_out: 5
---

# AMD Speedrun Submission Rankings

> Power-ranked by win probability based on 3 deep research agents, aiter source code analysis, and 18+ phases of prior experimentation.

**Competition**: AMD x GPU MODE E2E Model Speedrun (Phase 1 Qualifiers)
**Deadline**: April 6, 2026
**Prize**: Top 10 → $10K each + advance to $1M finals
**Scoring**: `Score = MaxPoints × (1 - rank/20)`. Only top 20 per kernel score.
**Branch**: `claude/amd-gpu-speedrun-6IKlZ` (13 commits)

## Aggregate Strategy

Being **rank 15 on all 3 kernels = 937.5 pts** — likely top 10 overall since most competitors specialize in 1-2 kernels. Breadth > depth.

| Kernel | Max Pts | Our Best | Leader | Gap | Tolerance |
|--------|---------|----------|--------|-----|-----------|
| **GEMM** | 1000 | ~24µs | 4.3µs | 5.6× | rtol=1e-2 |
| **MoE** | 1500 | ~155µs | 109.8µs | 1.4× | rtol=5e-2 |
| **MLA** | 1250 | ~70µs | 33µs | 2.1× | rtol=1e-2 |

---

## Power Rankings

### Tier S — Highest Win Probability

#### #1: GEMM `triton_v4` — tl.dot_scaled + e8m0_unshuffle
- **File**: `variants/gemm/submission_triton_v4.py`
- **Win Probability**: 35%
- **Expected**: 15-18µs (if tl.dot_scaled works on runner)
- **Risk**: Medium — tl.dot_scaled may not be available in runner's Triton version
- **Why #1**: Uses MI355X's NATIVE MFMA instruction via Triton's `tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc)`. Caches B preparation via `e8m0_unshuffle` (0.1µs vs 7µs re-quant). If this works, it's the single biggest point swing.
- **Research basis**: aiter source confirms `tl.dot_scaled` maps to `__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4`

#### #2: MLA `main` — Official Reference API Match
- **File**: `amd-mixed-mla/submission.py`
- **Win Probability**: 30%
- **Expected**: 55-65µs
- **Risk**: Low — matches reference API exactly
- **Why #2**: CRITICAL fix: uses `config["num_heads"]` (handles tp=4 AND tp=8), passes full `mla_decode_fwd` kwargs matching official reference. Previous submission hardcoded `NUM_HEADS=16` which would FAIL on tp=4 tests.
- **Research basis**: Official reference.py analysis confirmed API signature

#### #3: MoE `main` — splitk + block_size_M Tuned
- **File**: `amd-moe-mxfp4/submission.py`
- **Win Probability**: 25%
- **Expected**: 145-155µs
- **Risk**: Low — proven USE_NT=1 base, additive splitk/block_m
- **Why #3**: 1500 max points (highest kernel). Even rank 18 = 150 pts. MoE research found 155µs plateau is near-optimal for Python API. Only proven gain: USE_NT=1 (+2-4%).
- **Research basis**: MoE agent exhaustive analysis — KSPLIT is dead code, OPUS sorting regresses 19%

---

### Tier A — Strong Contenders

#### #4: GEMM `triton_blockm32` — tl.dot_scaled + Fallback
- **File**: `variants/gemm/submission_triton_blockm32.py`
- **Win Probability**: 30%
- **Expected**: 18-24µs
- **Risk**: Low — falls back to aiter if Triton fails
- **Why**: Same tl.dot_scaled kernel as #1 but with aiter fallback. Safer choice: if tl.dot_scaled crashes, still gets 24µs baseline. 2D grid (no swizzle) is simpler.
- **Trade-off**: Re-quantizes B from scratch (slower than v4's unshuffle cache)

#### #5: MLA `fmha_v3` — FlashMHA V3 + SAGE MXFP4 Probe
- **File**: `variants/mla/submission_fmha_v3.py`
- **Win Probability**: 20%
- **Expected**: <50µs (if V3 exists) or 65µs (fallback)
- **Risk**: Medium — untested API, may not exist on runner
- **Why**: Research found 13 attention APIs in aiter, only 5 tested. `fmha_v3_varlen_fwd` (priority 0.88) and `fav3_sage_mxfp4` are CDNA4-optimized and UNTESTED. If either exists, could eliminate 20-30µs dispatch overhead.
- **Research basis**: MLA agent systematic API landscape scan

#### #6: MoE `clean_minimal` — USE_NT Only
- **File**: `variants/moe/submission_clean_minimal.py`
- **Win Probability**: 25%
- **Expected**: 155µs
- **Risk**: Very Low — simplest possible submission
- **Why**: Research proved KSPLIT is dead code (<0.1% variance). splitk/block_m params may also be inert. This variant strips all unproven tuning — simpler = fewer failure modes.
- **Research basis**: MoE agent exhaustive KSPLIT testing analysis

---

### Tier B — Solid Alternatives

#### #7: GEMM `main` — Single-Call Quant
- **File**: `amd-mxfp4-mm/submission.py`
- **Win Probability**: 20%
- **Expected**: 22-24µs
- **Risk**: Very Low — matches reference exactly
- **Why**: Uses `get_triton_quant(per_1x32)` single call (same as reference). Eliminates separate `e8m0_shuffle`. Safe baseline if Triton variants fail.

#### #8: MLA `autosplit` — CU-Optimized Splits
- **File**: `variants/mla/submission_autosplit.py`
- **Win Probability**: 15%
- **Expected**: 55-65µs
- **Risk**: Low
- **Why**: Emulates aiter's internal `get_meta_param()` logic: sweeps 1-32 splits optimizing CU_utilization × throughput. Wider matmul regime (bs<=16).

#### #9: MLA `api_probe` — Multi-API Explorer
- **File**: `variants/mla/submission_api_probe.py`
- **Win Probability**: 15%
- **Expected**: 60-70µs (or better if untested API works)
- **Risk**: Medium — probes pa_ps_fwd_asm, flash_varlen, mla_decode_fwd
- **Why**: Systematic discovery — prints found APIs to stderr for diagnostics

#### #10: GEMM `loadinline_mfma` — Fused HIP Kernel
- **File**: `variants/gemm/submission_loadinline_mfma.py`
- **Win Probability**: 15%
- **Expected**: 30-100µs (shape-dependent)
- **Risk**: High — scalar inner loop, no MFMA instructions
- **Why**: Fuses A quantization INTO the HIP kernel (eliminates 26-84µs quant dispatch). But scalar FP4 encode/decode loop is slow for large shapes. Best case: small M shapes where quant dominates.
- **Research basis**: Kernel-writer agent (1357 tool uses, round-trip quant matching reference)

---

### Tier C — Experimental / Long Shots

#### #11: MoE `splitk_tuned` — Explicit splitk Variant
- **File**: `variants/moe/submission_splitk_tuned.py`
- **Win Probability**: 10%
- **Why**: Same as main but isolated variant. Research says splitk likely dead code via env var, but function parameter might differ.

#### #12: GEMM `triton_dotscaled` — Aiter Triton Import
- **File**: `variants/gemm/submission_triton_dotscaled.py`
- **Win Probability**: 10%
- **Why**: Tries to import aiter's internal Triton GEMM (`gemm_afp4wfp4_preshuffle`). May be faster than ASM for some shapes. Falls back to ASM.

#### #13: MLA `persistent` — Persistent Env Vars + Two-Stage Fallback
- **File**: `variants/mla/submission_persistent.py`
- **Win Probability**: 10%
- **Why**: Earlier version before reference API match. Still has two-stage ASM fallback. Superseded by main.

#### #14: GEMM `single_quant` — Isolated Single-Call Test
- **File**: `variants/gemm/submission_single_quant.py`
- **Win Probability**: 10%
- **Why**: Same as main GEMM, isolated for A/B testing

#### #15: MoE `envtuned` — All Env Vars
- **File**: `variants/moe/submission_envtuned.py`
- **Win Probability**: 10%
- **Why**: Adds GFX950_EXPL_SCHED on top of USE_NT. May help, may not.

#### #16: GEMM `fused_quant` — Env Vars + Skip Contiguous
- **File**: `variants/gemm/submission_fused_quant.py`
- **Win Probability**: 5%
- **Why**: Marginal optimization. Skip contiguous saves ~0.1µs if already contiguous.

#### #17: MLA `batched_bmm` — Batched BMM Path
- **File**: `variants/mla/submission_batched_bmm.py`
- **Win Probability**: 5%
- **Why**: Alternative matmul dispatch. Unlikely to beat main.

#### #18: MLA `splits_1` — Fixed 1 Split
- **File**: `variants/mla/submission_splits_1.py`
- **Win Probability**: 5%
- **Why**: Extreme: single split. Only helps if bs=1 with tiny KV.

#### #19: MoE `block_64` / `block_128` — Fixed Block Sizes
- **Files**: `variants/moe/submission_block_64.py`, `submission_block_128.py`
- **Win Probability**: 5%
- **Why**: Fixed block_m variants. Research says minimal effect.

#### #20: GEMM `prealloc` — Pre-allocated Buffers
- **File**: `variants/gemm/submission_prealloc.py`
- **Win Probability**: 3%
- **Why**: Pre-existing variant. Marginal allocation savings.

---

## Optimal Submission Strategy

### Phase 1: Test (bash submit_all.sh test)
Submit main submissions first to verify correctness:
1. **MoE main** (highest points, most likely to pass)
2. **MLA main** (critical API fix needs validation)
3. **GEMM main** (safe baseline)

### Phase 2: Variant Testing (bash submit_variants.sh)
Test high-potential variants:
1. **GEMM triton_v4** (biggest potential swing)
2. **GEMM triton_blockm32** (safe fallback version)
3. **MLA fmha_v3** (untested API discovery)
4. **MoE clean_minimal** (simpler-is-better hypothesis)

### Phase 3: Leaderboard (bash submit_all.sh leaderboard)
Submit the variant that performed best in each kernel.

## Score Scenarios

| Scenario | GEMM Rank | MLA Rank | MoE Rank | Aggregate |
|----------|-----------|----------|----------|-----------|
| **Best case** (Triton works) | 12 | 15 | 16 | 400+312+300 = **1012** |
| **Expected case** | 18 | 18 | 16 | 100+125+300 = **525** |
| **Worst case** (no improvement) | >20 | 20 | 18 | 0+0+150 = **150** |
| **Top 10 threshold** (estimated) | — | — | — | **~500-800** |

## Dead Ends (NEVER Retry)

| Approach | Result | Kernel |
|----------|--------|--------|
| `doweight_stage1=True` | GPU fault, 82% mismatch | MoE |
| `expert_mask` | CK crash | MoE |
| `OPUS_MOE_SORTING=1` | -19.3% regression | MoE |
| Direct ctypes dispatch | Stream isolation error | All |
| `torch.compile` on ROCm | Falls back to eager | All |
| `gemm_a4w4_blockscale` | "Not supported" | GEMM |
| `gemm_a4w4_asm` direct | Wrong kernel selection | GEMM |
| Custom Triton MoE | 68% slower than CK ASM | MoE |
| Hardcoded NUM_HEADS=16 | Fails on tp=4 tests | MLA |

## Graph Relations

- [[luma-amd-speedrun-strategy]] — Original competition strategy
- [[luma-amd-breakthroughs-20260323]] — March breakthroughs
- [[amd-hip-kernel-development]] — HIP kernel patterns
- [[MOC-machine-learning]] — Parent map of content
