# Specification: Luma AMD Speedrun - Phase 1 Kernels

## 1. Overview
This mission deploys the Cohezion swarm to solve the **AMD x GPU MODE Hackathon Phase 1** (Qualifiers). The objective is to optimize three critical GPU kernels for the AMD Instinct™ MI355X GPU: MXFP4 MoE, MLA Decode, and MXFP4 GEMM. Success is measured by absolute runtime speed averaged over large test cases, while maintaining mathematical correctness.

## 2. Core Requirements
- **Kernel Optimization Loop**: Use `EVOAgent` entities to iterate on the provided reference kernels in `research/challenges/luma_amd_speedrun/kernels/`.
- **Performance Benchmarking**: Integrate the `popcorn-cli` into the agent's action space to run `--mode benchmark` and `--mode test`.
- **Strategic Targets**:
  - **MLA Decode**: Implement a native MXFP4 decode kernel (`a4w4` or `a8w4`) to reduce memory bandwidth by ~2x compared to the FP8 reference.
  - **MXFP4 MoE**: Implement inter-stage fusion (Gate+Up and Down GEMMs) and activation quantization fusion.
  - **MXFP4 GEMM**: Implement high-performance tiling strategies using **HipKittens** primitives.
- **Autonomous Feedback**: Use Ouroboros to monitor benchmark regressions and Mycelium to verify that optimized kernels remain mathematically sound.

## 3. Technical Constraints
- Target Hardware: AMD Instinct™ MI355X.
- Submission Tool: `popcorn-cli` (installed and authenticated).
- Languages: Python (orchestration), HIP/C++ (optimized kernels).
- Strict TDD: Every optimized kernel must pass `popcorn submit --mode test` before being benchmarked.
