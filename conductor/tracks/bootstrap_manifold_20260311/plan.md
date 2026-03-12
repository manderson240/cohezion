# Implementation Plan: Bootstrap Triune Manifold Engine

## Phase 1: Core State Architecture
- [x] Task: Define `TriuneState` PyTorch/Pydantic models for 12D, 512D, and 2048D tensors.
    - [x] Write unit tests enforcing shape and type constraints.
    - [x] Implement the models.
- [x] Task: Implement the 0.5 Coherence (HIHO) calculation utility.
    - [x] Sub-task: Write unit tests for coherence edge cases.
    - [x] Sub-task: Implement the calculation logic.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Core State Architecture' (Protocol in workflow.md)

## Phase 2: Persistence Integration
- [x] Task: Scaffold SurrealDB 3.0 async client for trajectory storage.
    - [x] Sub-task: Write async mock tests for DB insertion.
    - [x] Sub-task: Implement `SurrealTrajectoryLogger`.
- [x] Task: Scaffold MCP Client for Obsidian Vault interaction.
    - [x] Sub-task: Write tests for standard tool-call formatting.
    - [x] Sub-task: Implement `ObsidianMemoryMCP`.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Persistence Integration' (Protocol in workflow.md)

## Phase 3: Engine Initialization
- [x] Task: Build the `TriuneSimulationEngine` base class binding State to Persistence.
    - [x] Sub-task: Write end-to-end simulation step test (mocked DB).
    - [x] Sub-task: Implement the `step(dt)` method.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Engine Initialization' (Protocol in workflow.md)

## Phase: Review Fixes
- [x] Task: Apply review suggestions 889e83f
