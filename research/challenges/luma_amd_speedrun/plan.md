# Execution Plan: AMD x GPU MODE Hackathon (Phase 1)

## Objective
Optimize three critical GPU kernels (MXFP4 MoE, MLA Decode, MXFP4 GEMM) for AMD Instinct™ MI355X GPUs to qualify for Phase 2.

## Phase 1: Environment & Tooling Setup
1. **Install Popcorn CLI**
   - Execute the one-line install script.
   - Verify `popcorn` binary is in the `PATH`.
2. **Authentication**
   - Run `popcorn register discord` or `github`.
   - Verify credentials in `$HOME/.popcorn.yaml`.
3. **Repository Initialization**
   - Create isolated environments/folders for each of the three kernels:
     - `research/challenges/luma_amd_speedrun/kernels/mxfp4_moe`
     - `research/challenges/luma_amd_speedrun/kernels/mla_decode`
     - `research/challenges/luma_amd_speedrun/kernels/mxfp4_gemm`
   - Use `popcorn setup` within each to bootstrap the required scaffolding.

## Phase 2: Technical Deep Dive & Baseline Establishment
1. **Reference Acquisition:** Locate and download the reference implementations for the 3 kernels (available on the GPU MODE Discord/Website).
2. **Baseline Testing:**
   - Run each reference kernel through the Popcorn CLI using `--mode benchmark` and `--mode test`.
   - Record the baseline performance metrics in a central `results.md` tracking file.

## Phase 3: Iterative Kernel Optimization (The Loop)
For each kernel:
1. **Analysis:** Profile the reference implementation (if profiling is available via `popcorn --mode profile`) to identify bottlenecks (e.g., memory bandwidth, compute bound, register spilling).
2. **Development:** 
   - Apply ROCm/HIP specific optimizations (e.g., vectorization, shared memory usage, unrolling, custom warp-level primitives).
   - Ensure MXFP4 format constraints are strictly handled.
3. **Validation:**
   - Run local validation (if possible) or use `popcorn submit --mode test` to ensure mathematical correctness.
4. **Benchmarking:**
   - Run `popcorn submit --mode benchmark`.
   - Update `results.md` with the new performance numbers.
5. **Leaderboard Submission:**
   - Once a significant improvement is confirmed, submit using `--mode leaderboard`.

## Phase 4: Finalization (Before March 30, 2026)
- Ensure only the single fastest, verified script per problem is submitted as the final entry.
- Ensure all code is cleanly formatted and prepared for potential merging into AMD repositories (ATOM/vLLM/SGLang) as required for Phase 2 eligibility.
