# Implementation Plan: Luma AMD Speedrun - Phase 1 Kernels

## Phase 1: Knowledge Ingestion & Baseline (COMPLETED)
- [x] Task: Ingest reference kernels and handoff into the Triune Manifold.
- [x] Task: Establish baseline performance (24 us for GEMM).
- [x] Task: Conductor - User Manual Verification 'Phase 1: Ingestion & Baseline' (Protocol in workflow.md)

## Phase 2: GEMM Optimization (The Main Target)
- [x] Task: Fix the fused quant+GEMM Triton kernel.
    - [x] Sub-task: Create a diagnostic hybrid kernel: `dynamic_mxfp4_quant(A)` (known correct) + custom Triton GEMM.
    - [x] Sub-task: Isolate if bug is in quantization formula or GEMM kernel.
    - [x] Sub-task: Implement fix based on diagnosis (e.g., E8M0 scale normalization or Origami scheduling).
    - [x] Sub-task: Validate correctness via `popcorn-cli submit --mode test`.
    - [x] Sub-task: Benchmark to beat 9.7 us.
- [x] Task: Conductor - User Manual Verification 'Phase 2: GEMM Optimization' (Protocol in workflow.md)

## Phase 3: MLA Decode Optimization (Bandwidth Sprint)
- [x] Task: Prototype the native MXFP4 decode kernel.
    - [x] Sub-task: Implement `a4w4` or `a8w4` logic using `kv_data["mxfp4"]`.
    - [x] Sub-task: Validate correctness via `popcorn-cli submit --mode test`.
- [x] Task: Conductor - User Manual Verification 'Phase 3: MLA Optimization' (Protocol in workflow.md)

## Phase 4: MXFP4 MoE Optimization (Fusion Sprint)
- [x] Task: Implement Inter-stage Fusion.
    - [x] Sub-task: Fuse SwiGLU activation and quantization into the primary GEMM.
- [x] Task: Conductor - User Manual Verification 'Phase 4: MoE Optimization' (Protocol in workflow.md)

## Phase 5: Final Benchmarking & Submission
- [x] Task: Execute official submission using `popcorn-cli submit --mode leaderboard`.
- [x] Task: Conductor - User Manual Verification 'Phase 5: Final Submission' (Protocol in workflow.md)

## Phase: Review Fixes
- [x] Task: Apply review suggestions 0fb8f0e
