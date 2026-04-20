# Luma AMD Speedrun - Mission Tracker

## Phase 1: Preparation (COMPLETED)
- [x] Create research directory `research/challenges/luma_amd_speedrun/`.
- [x] Extract rules and T&C into `RULES.md`.
- [x] Draft execution plan in `plan.md`.
- [x] Perform technical research on MXFP4/MLA and summarize in `technical_analysis.md`.
- [x] Install `popcorn-cli`.
- [x] Register/Authenticate with `popcorn-cli` (GitHub: manderson240).
- [x] Download reference kernels and place in `kernels/`.

## Phase 2: Knowledge Accumulation (IN PROGRESS)
- [ ] Watch **GPU MODE Lecture 97 (HipKittens)** - Deep dive into AMD-specific tile primitives.
- [ ] Watch **GPU MODE Lecture 93 (Cornserve)** - Understand Popcorn CLI usage in depth.
- [ ] Read **DeepSeek-V3/R1 Paper** sections on MLA and MoE architecture.
- [ ] Study **AITER fused_moe** implementation details (the current reference baseline).

## Phase 3: Baseline & Profiling
- [ ] Run `popcorn-cli submit --mode benchmark` for each reference kernel.
- [ ] Document baseline latencies for all benchmark cases (bs=4, 64, 256, 1024).
- [ ] Identify primary bottlenecks for each kernel (Memory bound vs. Compute bound).

## Phase 4: Optimization Sprints
### MXFP4 MoE
- [ ] Investigate Inter-stage fusion (fusing Stage 1 and Stage 2).
- [ ] Investigate activation quantization fusion.
### MLA Decode
- [ ] Optimize KV latent vector transformations.
- [ ] Fuse RoPE and up-projection.
### MXFP4 GEMM
- [ ] Implement tile-based optimizations using HipKittens primitives.

## Phase 5: Submission & Leaderboard
- [ ] Validate mathematical correctness (`--mode test`).
- [ ] Final performance verification (`--mode benchmark`).
- [ ] Official leaderboard submission (`--mode leaderboard`).
