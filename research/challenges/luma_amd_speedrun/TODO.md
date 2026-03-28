# Luma AMD Speedrun - Mission Tracker

## Phase 1: Preparation (COMPLETED)
- [x] Create research directory `research/challenges/luma_amd_speedrun/`.
- [x] Extract rules and T&C into `RULES.md`.
- [x] Draft execution plan in `plan.md`.
- [x] Perform technical research on MXFP4/MLA and summarize in `technical_analysis.md`.
- [x] Install `popcorn-cli`.
- [x] Register/Authenticate with `popcorn-cli` (GitHub: manderson240).
- [x] Download reference kernels and place in `kernels/`.

## Phase 2: Knowledge Accumulation (COMPLETED)
- [x] Study reference kernel APIs (aiter gemm_a4w4, mla_decode_fwd, fused_moe)
- [x] Understand benchmark shapes and tolerance requirements
- [x] Document reference performance numbers in `results.md`
- [ ] Watch **GPU MODE Lecture 97 (HipKittens)** - Deep dive into AMD tile primitives
- [ ] Watch **GPU MODE Lecture 93 (Cornserve)** - Popcorn CLI in depth

## Phase 3: Optimization Implementation (COMPLETED)
### MXFP4 GEMM
- [x] Module-level quant_func caching
- [x] Removed unnecessary B.contiguous()
- [x] Shape-dependent routing (CK + Triton GEMM probe)
- [ ] Custom fused quant+GEMM Triton kernel (deferred — needs MI355X testing)

### MLA Decode
- [x] Replaced naive torch loop with aiter mla_decode_fwd persistent kernel
- [x] fp8 Q + fp8 KV path (matches reference approach)
- [ ] MXFP4 KV cache path (if mla_decode_fwd supports fp4x2)

### MXFP4 MoE
- [x] Baseline fused_moe call (reference-equivalent)
- [ ] Shared expert specialization (dense GEMM for shared expert)
- [ ] Parameter tuning (doweight_stage1, etc.)

## Phase 4: Submission & Leaderboard (COMPLETED)
- [x] Fix Popcorn CLI auth
- [x] Validate correctness (`--mode test`) for all 3 kernels
- [x] Benchmark performance (`--mode benchmark`) for all 3 kernels
- [x] Official leaderboard submission (`--mode leaderboard`)
- [x] Document final results in `results.md`

## Phase 5: VLIW-Informed Custom Kernel Approaches (COMPLETED)

### GEMM — gemm_afp4wfp4 Triton Alternative
- [x] Task 1: Confirmed dynamic_mxfp4_quant works (plan's get_torch_quant approach N/A — all get_*_quant fail)
- [x] Task 2: gemm_afp4wfp4 Triton kernel — 20.6 µs geomean (16% improvement over 24 µs)
  - Uses dynamic_mxfp4_quant for A + e8m0_unshuffle for B_scale + B_q from input
  - All tensors viewed as uint8 to avoid KeyError on native fp4 dtype
  - Auto-tuner selects better tile configs than fixed ASM tiles
- [x] Task 6: CSV config dump — revealed DSV3 FP4 tuned configs with tile transitions

### MoE — Direct CK/1-Stage Exploration
- [x] Task 3: Remote introspection — discovered fmoe_g1u1 exists, CK stage APIs mapped
- [x] Task 4: Direct torch.ops.aiter.fused_moe_ call — identical perf to Python wrapper
  - No Python overhead to eliminate; gap is kernel-level
  - 1-stage fmoe_g1u1 exists for MXFP4 but gated by run_1stage=False
- [x] MoE at ~155 µs geomean (1.07x gap to leader)

### MLA — MXFP4 KV Cache
- [x] Task 5: BLOCKED — MLA ASM kernel rejects MXFP4 KV (head_size 576 ≠ 288 packed)
- [x] MLA at ~98 µs geomean (2x improvement via torch-native hybrid)

### Current Leaderboard Status (Post-Phase 5)

| Kernel | Our Time | Leader | Gap | Improvement |
|--------|----------|--------|-----|-------------|
| GEMM | 20.6 µs | 9.7 µs | 2.12x | ↑ from 2.49x |
| MoE | ~155 µs | 145 µs | 1.07x | ↑ from 1.28x |
| MLA | ~98 µs | 4.3 µs | 22.9x | ↑ from 44.1x |
