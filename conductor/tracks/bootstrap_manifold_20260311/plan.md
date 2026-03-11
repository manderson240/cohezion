# Implementation Plan: Bootstrap Triune Manifold Engine

## Phase 1: Core State Architecture
- [ ] Task: Define `TriuneState` PyTorch/Pydantic models for 12D, 512D, and 2048D tensors.
    - [ ] Sub-task: Write unit tests enforcing shape and type constraints.
    - [ ] Sub-task: Implement the models.
- [ ] Task: Implement the 0.5 Coherence (HIHO) calculation utility.
    - [ ] Sub-task: Write unit tests for coherence edge cases.
    - [ ] Sub-task: Implement the calculation logic.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Core State Architecture' (Protocol in workflow.md)

## Phase 2: Persistence Integration
- [ ] Task: Scaffold SurrealDB 3.0 async client for trajectory storage.
    - [ ] Sub-task: Write async mock tests for DB insertion.
    - [ ] Sub-task: Implement `SurrealTrajectoryLogger`.
- [ ] Task: Scaffold MCP Client for Obsidian Vault interaction.
    - [ ] Sub-task: Write tests for standard tool-call formatting.
    - [ ] Sub-task: Implement `ObsidianMemoryMCP`.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Persistence Integration' (Protocol in workflow.md)

## Phase 3: Engine Initialization
- [ ] Task: Build the `TriuneSimulationEngine` base class binding State to Persistence.
    - [ ] Sub-task: Write end-to-end simulation step test (mocked DB).
    - [ ] Sub-task: Implement the `step(dt)` method.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Engine Initialization' (Protocol in workflow.md)