# Luma AMD Speedrun: Optimize Kernels for Top Rankings

Created: 2026-03-11
Status: PENDING
Approved: Yes
Iterations: 1
Worktree: Yes

> **Status Lifecycle:** PENDING -> COMPLETE -> VERIFIED
> **Iterations:** Tracks implement->verify cycles
> **Deadline:** March 30, 2026 (18 days remaining)

## Context

All 3 kernels are submitted and ranked on the leaderboard (as of 2026-03-12):

| Kernel | Rank | Our Time | Leader Time | Gap | Leaderboard |
|--------|------|----------|-------------|-----|-------------|
| GEMM | 67/68 | 24.082 us | 9.671 us | 2.49x | `amd-mxfp4-mm` |
| MLA | 40/54 | 191.259 us | 4.335 us | 44.1x | `amd-mixed-mla` |
| MoE | 34/43 | 185.189 us | 145.177 us | 1.28x | `amd-moe-mxfp4` |

**We score 0 points** — must reach top 10 in at least one kernel. MoE is closest (1.28x gap).

Prior work: Correctness issues fixed (GEMM delegates to ref_kernel due to Triton JIT call-site
bug). All leaderboard names discovered. Skills created for Popcorn CLI workflow and JIT bug.

## Summary

**Goal:** Optimize all 3 kernels to improve leaderboard rankings. Priority: MoE (quick win) -> MLA (highest impact potential) -> GEMM (blocked by JIT bug).

**Architecture:** Each kernel is a single submission.py that exports custom_kernel(data: input_t) -> output_t. Evaluated remotely on MI355X via Popcorn CLI (~2 min/submit). Scoring = geometric mean of benchmark runtimes. No local testing possible (gfx1151 not supported by ROCm 6.2.4).

**Tech Stack:** Python, PyTorch, Triton (AMD ROCm), aiter library (AMD optimized kernels), Popcorn CLI.

## Scope

### In Scope

- Optimize MoE kernel parameters (fused_moe tuning, stage config, sorting)
- Optimize MLA kernel (NUM_KV_SPLITS tuning, batch-size dispatch, MXFP4 KV)
- Fix GEMM JIT call-site issue to enable optimization
- Research competitor approaches via aiter source and GPU MODE community
- Leaderboard submissions for improved kernels

### Out of Scope

- Custom HIP C++ / assembly kernels (Python + aiter only for now)
- Local testing (all via Popcorn CLI remote submission)
- Changes to reference.py, task.py, eval.py, utils.py (competition files)
- Phase 2 hackathon work (end-to-end DeepSeek-R1)

## Context for Implementer

> **This is iterative GPU kernel optimization. Each change requires a remote submission (~2 min).**

**Workflow per optimization attempt:**
1. Modify submission.py
2. popcorn-cli submit --no-tui --mode test --gpu MI355X --leaderboard <name> <file> (correctness)
3. If passes: --mode benchmark (timing without leaderboard impact)
4. If faster: --mode leaderboard (official ranked submission)

**Key constraints:**
- Benchmark clears L2 cache between runs -- no cache warming tricks
- GEMM benchmark includes A quantization time (part of timed region)
- Correctness tolerances: GEMM rtol=1e-2, MLA rtol=1e-2, MoE rtol=5e-2
- Transient artifact download failures happen -- retry on unexplained failure
- No per-user rate limit; submit freely

### Key Files

| File | Purpose |
|------|---------|
| kernels/moe-mxfp4/submission.py | MoE submission (59 lines, calls fused_moe) |
| kernels/mixed-mla/submission.py | MLA submission (143 lines, mla_decode_fwd persistent mode) |
| kernels/mxfp4-mm/submission.py | GEMM submission (22 lines, delegates to ref_kernel) |
| kernels/*/reference.py | Reference implementations (read-only, study for optimization hints) |
| results.md | Competition results documentation |

### Benchmark Configurations

**MoE** (7 configs, geometric mean):
- TP=8: bs={16,128,512}, dhidden=7168, dexpert=256, E=257, topk=9
- TP=4: bs={16,128,512}, dhidden=7168, dexpert=512, E=33, topk=9
- EP:   bs=512, dhidden=7168, dexpert=2048, E=33, topk=9

**MLA** (8 configs, geometric mean):
- bs={4,32,64,256} x kvseqlen={1024,8192}, qseqlen=1, tp=4 or 8

**GEMM** (6 configs, geometric mean):
- m={4,16,32,32,64,256}, n={2880,2112,4096,2880,7168,3072}, k={512,7168,512,512,2048,1536}

### Current Submission Analysis

**MoE (34/43, 185.189 us):** Identical to reference -- calls fused_moe with same params.
Already beats task.yml reference baselines for most configs. Leader at 145 us uses same API
with better parameter tuning.

**MLA (40/54, 191.259 us):** Uses mla_decode_fwd persistent mode with FP8 Q + FP8 KV,
fixed NUM_KV_SPLITS=32. Reference uses same approach. Top entries at 4.3 us likely use
custom assembly kernels or radically different algorithms.

**GEMM (67/68, 24.082 us):** Delegates to ref_kernel due to Triton JIT call-site bug.
~2x slower than reference baselines (8-20 us) due to Python delegation overhead. Leader
at 9.67 us likely uses custom Triton or HIP kernels.

### Top Competitors

| Competitor | GEMM | MLA | MoE | Strategy |
|------------|------|-----|-----|----------|
| mega-dmitriy | 6th | 6th | 1st | Strong all-around |
| josusanmartin | 2nd | 14th | 2nd | GEMM+MoE |
| Yufeng98 | 7th | 5th | 4th | Consistent |
| sanjay_arvind | 5th | 8th | 6th | Consistent |
| parcadei | 1st | 11th | 12th | GEMM specialist |
| Jayluci4 | - | 1st | - | MLA breakthrough (4.3 us) |

## Progress Tracking

- [ ] Task 1: Research aiter fused_moe optimization parameters
- [ ] Task 2: Optimize MoE kernel (target: top 20)
- [ ] Task 3: Tune MLA NUM_KV_SPLITS per batch size
- [ ] Task 4: Optimize MLA kernel (target: top 25)
- [ ] Task 5: Fix GEMM JIT call-site issue
- [ ] Task 6: Optimize GEMM kernel (target: top 40)

**Total Tasks:** 6 | **Completed:** 0 | **Remaining:** 6

## Implementation Tasks

### Task 1: Research aiter fused_moe Optimization Parameters

**Objective:** Study the aiter fused_moe API to identify tunable parameters that could improve performance.

**Dependencies:** None

**Steps:**
1. Search aiter source for fused_moe function signature and all parameters
2. Identify parameters not used in our submission: expert_mask, doweight_stage1, sorting options
3. Check if fused_moe has config/tuning knobs (block sizes, number of stages, etc.)
4. Study the difference between E=257 (shared expert) vs E=33 configs

**Definition of Done:**
- [ ] List of tunable fused_moe parameters documented
- [ ] Hypothesis for 2-3 optimization approaches

---

### Task 2: Optimize MoE Kernel (target: top 20)

**Objective:** Improve MoE from 185 us (rank 34/43) to under ~170 us (target top 20).

**Dependencies:** Task 1

**Files:** Modify kernels/moe-mxfp4/submission.py

**Optimization ideas (try in order):**
1. doweight_stage1=True
2. expert_mask parameter
3. Token sorting
4. Shape-specific dispatch for E=257 vs E=33
5. Pre-compute shared expert output

**Definition of Done:**
- [ ] At least 3 parameter variations tested
- [ ] Best result submitted to leaderboard
- [ ] Results documented with timing per config

---

### Task 3: Tune MLA NUM_KV_SPLITS per Batch Size

**Objective:** Replace fixed NUM_KV_SPLITS=32 with batch-size-dependent dispatch.

**Dependencies:** None

**Files:** Modify kernels/mixed-mla/submission.py

**Steps:**
1. bs=4: try NUM_KV_SPLITS={8, 16}
2. bs=32: try NUM_KV_SPLITS={16, 32}
3. bs=64: try NUM_KV_SPLITS={32}
4. bs=256: try NUM_KV_SPLITS={32, 64}

**Definition of Done:**
- [ ] Tested at least 2 NUM_KV_SPLITS values
- [ ] Best configuration submitted to leaderboard

---

### Task 4: Optimize MLA Kernel (target: top 25)

**Objective:** Deeper MLA optimizations beyond NUM_KV_SPLITS.

**Dependencies:** Task 3

**Files:** Modify kernels/mixed-mla/submission.py

**Optimization ideas:**
1. MXFP4 KV cache (kv_data["mxfp4"] instead of kv_data["fp8"])
2. fast_mode=True for metadata builder
3. Non-persistent mode for small batches
4. Tune kv_granularity

**Definition of Done:**
- [ ] At least 2 optimization approaches tested
- [ ] MLA rank improved from 40/54

---

### Task 5: Fix GEMM JIT Call-Site Issue

**Objective:** Stop delegating to ref_kernel; call gemm_a4w4 directly.

**Dependencies:** None

**Files:** Modify kernels/mxfp4-mm/submission.py

**Fix strategies:**
1. Use aiter.get_torch_quant instead of get_triton_quant
2. Import quant function from reference module
3. Force Triton cache invalidation via TRITON_CACHE_DIR

**Definition of Done:**
- [ ] custom_kernel calls gemm_a4w4 directly
- [ ] Passes --mode test with 0.0 max error
- [ ] Benchmark shows improvement over 24 us baseline

---

### Task 6: Optimize GEMM Kernel (target: top 40)

**Objective:** Optimize GEMM after JIT fix.

**Dependencies:** Task 5

**Files:** Modify kernels/mxfp4-mm/submission.py

**Optimization ideas:**
1. Shape-dependent routing for small vs large M
2. Triton GEMM for large M via aiter.ops.triton.gemm
3. Pre-shuffle optimization
4. Quantization fusion

**Definition of Done:**
- [ ] At least 2 optimization approaches tested
- [ ] GEMM rank improved from 67/68

## Popcorn CLI Reference

```bash
KERNELS=/home/mike-anderson/dev/cohezion/.worktrees/spec-luma-amd-speedrun/research/challenges/luma_amd_speedrun/kernels
CLI=~/.local/bin/popcorn-cli

$CLI submit --no-tui --mode test --gpu MI355X --leaderboard amd-moe-mxfp4 $KERNELS/moe-mxfp4/submission.py
$CLI submit --no-tui --mode benchmark --gpu MI355X --leaderboard amd-moe-mxfp4 $KERNELS/moe-mxfp4/submission.py
$CLI submit --no-tui --mode leaderboard --gpu MI355X --leaderboard amd-moe-mxfp4 $KERNELS/moe-mxfp4/submission.py

$CLI submit --no-tui --mode test --gpu MI355X --leaderboard amd-mixed-mla $KERNELS/mixed-mla/submission.py
$CLI submit --no-tui --mode test --gpu MI355X --leaderboard amd-mxfp4-mm $KERNELS/mxfp4-mm/submission.py
```

**Confirmed leaderboard names:** amd-mxfp4-mm, amd-mixed-mla, amd-moe-mxfp4

**No per-user rate limit.** Submit freely. Retry on transient artifact download failures.

## Risks

| Risk | Mitigation |
|------|------------|
| MoE gains are marginal | Focus on parameter tuning. Even 5% helps. |
| MLA top entries use custom ASM | Target mid-pack (top 25), not top 3. MXFP4 KV is a realistic 2x win. |
| GEMM JIT bug has no workaround | Try torch_quant path; worst case stay at ref_kernel delegation. |
| Slow iteration (~2 min/submit) | Batch optimizations: test multiple params per submission when possible. |
| Correctness regression | Always --mode test before --mode benchmark. |
