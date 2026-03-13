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

## Phase 4: Submission & Leaderboard (BLOCKED)
- [ ] Fix Popcorn CLI auth (run `popcorn-cli reregister github` interactively)
- [ ] Validate correctness (`--mode test`) for all 3 kernels
- [ ] Benchmark performance (`--mode benchmark`) for all 3 kernels
- [ ] Official leaderboard submission (`--mode leaderboard`)
- [ ] Document final results in `results.md`
