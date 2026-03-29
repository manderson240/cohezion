# Implementation Plan: Luma AMD Speedrun - Phase 1 Kernels

## Phase 1: Knowledge Ingestion & Baseline
- [ ] Task: Ingest reference kernels into the Triune Manifold.
    - [ ] Sub-task: Use `HFEmbeddingBridge` to encode reference code into the 'Knower' layer.
    - [ ] Sub-task: Run the `benchmark_baseline.py` script to establish our 'Root of Trust' performance metrics.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Ingestion & Baseline' (Protocol in workflow.md)

## Phase 2: MLA Decode Optimization (Bandwidth Sprint)
- [ ] Task: Prototype the native MXFP4 decode kernel.
    - [ ] Sub-task: Implement `a4w4` or `a8w4` logic using HipKittens primitives.
    - [ ] Sub-task: Validate correctness via `popcorn-cli submit --mode test`.
- [ ] Task: Iterative Performance Tuning.
    - [ ] Sub-task: Loop `EVOAgent` actions to refine tile sizes and register usage.
    - [ ] Sub-task: Record benchmark results in SurrealDB.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: MLA Optimization' (Protocol in workflow.md)

## Phase 3: MXFP4 MoE Optimization (Fusion Sprint)
- [ ] Task: Implement Inter-stage Fusion.
    - [ ] Sub-task: Fuse SwiGLU activation and quantization into the primary GEMM.
    - [ ] Sub-task: Validate correctness via `popcorn-cli`.
- [ ] Task: Shared Expert Specialization.
    - [ ] Sub-task: Optimize the non-routed expert path for UMA architecture.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: MoE Optimization' (Protocol in workflow.md)

## Phase 4: Final Benchmarking & Submission
- [ ] Task: Perform system-wide verification of all three kernels.
- [ ] Task: Execute official submission using `popcorn-cli submit --mode leaderboard`.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Final Submission' (Protocol in workflow.md)
