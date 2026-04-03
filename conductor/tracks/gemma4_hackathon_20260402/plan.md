# Implementation Plan: Gemma 4 Integration & EcoResilience Synthesis

## Phase 1: Foundation & Provider Implementation (Commit: eecaeefbe)
- [x] **Task: Gemma4Provider Development**
    - [x] Create `tests/providers/test_gemma4_provider.py` with failing unit tests for the new provider.
    - [x] Implement `Gemma4Provider` in `src/cohezion/providers/gemma4.py` (inheriting from `ModelProvider`).
    - [x] Add support for Gemma 4 Thinking Mode and context window configuration.
    - [x] Ensure tests pass (Green Phase).
    - [x] Refactor and verify 100% coverage.
- [x] **Task: Provider Factory Integration**
    - [x] Update `src/cohezion/providers/factory.py` (or equivalent) to register `Gemma4Provider`.
    - [x] Write integration tests for the factory to resolve Gemma 4 models.
    - [x] Verify coverage.
- [x] **Task: Conductor - User Manual Verification 'Phase 1: Foundation & Provider Implementation' (Protocol in workflow.md)**

## Phase 2: Benchmarking & Optimization (Commit: 9e30e7d)
- [x] **Task: Local Benchmarking Suite**
    - [x] Create `scripts/benchmarks/gemma4_benchmark.py`.
    - [x] Benchmark latency, throughput, and reasoning quality (thinking mode) for 31B, 26B, 4B, and 2B models.
    - [x] Log results to a markdown report in `docs/benchmarks/gemma4_hardware_eval.md`.
- [x] **Task: Prompt & Routing Optimization**
    - [x] Implement token-efficient routing logic for Gemma 4 (preferring E2B/E4B for lightweight tasks).
    - [x] Test the routing logic with mock agent tasks.
    - [x] Refactor for performance and clarity.
- [x] **Task: Conductor - User Manual Verification 'Phase 2: Benchmarking & Optimization' (Protocol in workflow.md)**

## Phase 3: EcoResilience Synthesis & Prototype (Commit: fa333df)
- [x] **Task: TEK + Physics Prompt Engineering**
    - [x] Research and draft system prompts for the EcoResilience agent.
    - [x] Conduct multi-perspective adversarial review of the prompts.
    - [x] Refine prompts based on review.
- [x] **Task: EcoResilience Specialist Agent Implementation**
    - [x] Write `tests/agents/test_ecoresilience_agent.py`.
    - [x] Implement `EcoResilienceAgent` class synthesizing TEK and Unified Physics.
    - [x] Integrate with the Cohezion swarm execution loop.
    - [x] Verify 100% coverage.
- [x] **Task: Initial Simulation Run & Validation**
    - [x] Execute an ecosystem resilience simulation using the prototype.
    - [x] Document the 12D state trajectories of the simulation.
    - [x] Use Mycelium (ShadowScripter) to grow regression tests around the simulation results.
- [x] **Task: Conductor - User Manual Verification 'Phase 3: EcoResilience Synthesis & Prototype' (Protocol in workflow.md)**

## Phase 4: Documentation & Finalization
- [x] **Task: Obsidian Knowledge Vault Update**
    - [x] Document "Gemma 4 Good" hackathon opportunities identified.
    - [x] Link TEK concepts to 12D manifolds and HIHO stability in the vault.
- [x] **Task: Repo Cleanup & Final Walkthrough**
    - [x] Ensure all code adheres to project style guidelines.
    - [x] Perform final full test suite run.
    - [x] Generate an interactive Marimo walkthrough for the EcoResilience agent.
- [x] **Task: Conductor - User Manual Verification 'Phase 4: Documentation & Finalization' (Protocol in workflow.md)**
