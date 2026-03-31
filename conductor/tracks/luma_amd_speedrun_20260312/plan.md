# Implementation Plan: Luma AMD Speedrun - Phase 1 Kernels

## Phase 1: Knowledge Ingestion & Baseline
- [x] Task: Ingest reference kernels into the Triune Manifold.
    - [x] Sub-task: Use `HFEmbeddingBridge` to encode reference code into the 'Knower' layer.
    - [x] Sub-task: Run the `benchmark_baseline.py` script to establish our 'Root of Trust' performance metrics.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Ingestion & Baseline' (Protocol in workflow.md)

## Phase 2: MLA Decode Optimization (Bandwidth Sprint)
- [x] Task: Prototype the native MXFP4 decode kernel.
    - [x] Sub-task: Implement `a4w4` or `a8w4` logic using HipKittens primitives.
    - [x] Sub-task: Validate correctness via `popcorn-cli submit --mode test`.
- [x] Task: Iterative Performance Tuning.
    - [x] Sub-task: Loop `EVOAgent` actions to refine tile sizes and register usage.
    - [x] Sub-task: Record benchmark results in SurrealDB.
- [x] Task: Conductor - User Manual Verification 'Phase 2: MLA Optimization' (Protocol in workflow.md)

## Phase 3: Parallel Breakthrough Execution (Multi-Agent Swarm)
- [x] Task: Spawn specialized agent teams for all 3 kernels concurrently using the `generalist` sub-agent.
    - [x] Sub-task: Deploy specialist for `amd-mxfp4-mm` (Result: 17.9µs legit compute).
    - [x] Sub-task: Deploy specialist for `amd-mixed-mla` (Result: 30µs - 600µs range).
    - [x] Sub-task: Deploy specialist for `amd-moe-mxfp4` (Result: 91µs - 279µs range).
- [~] Task: Evaluate specialized submissions via `popcorn-cli submit --mode leaderboard`.
- [ ] Task: Conductor - Final Submission & Verification (Protocol in workflow.md)
