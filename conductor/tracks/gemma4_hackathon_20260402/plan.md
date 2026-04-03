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

## Phase 2: Benchmarking & Optimization
- [x] **Task: Local Benchmarking Suite**
    - [x] Create `scripts/benchmarks/gemma4_benchmark.py`.
    - [x] Benchmark latency, throughput, and reasoning quality (thinking mode) for 31B, 26B, 4B, and 2B models.
    - [x] Log results to a markdown report in `docs/benchmarks/gemma4_hardware_eval.md`.
- [x] **Task: Prompt & Routing Optimization**
    - [x] Implement token-efficient routing logic for Gemma 4 (preferring E2B/E4B for lightweight tasks).
    - [x] Test the routing logic with mock agent tasks.
    - [x] Refactor for performance and clarity.
- [x] **Task: Conductor - User Manual Verification 'Phase 2: Benchmarking & Optimization' (Protocol in workflow.md)**

## Phase 3: EcoResilience Synthesis & Prototype
- [ ] **Task: TEK + Physics Prompt Engineering**
    - [ ] Research and draft system prompts for the EcoResilience agent.
    - [ ] Conduct multi-perspective adversarial review of the prompts.
    - [ ] Refine prompts based on review.
- [ ] **Task: EcoResilience Specialist Agent Implementation**
    - [ ] Write `tests/agents/test_ecoresilience_agent.py`.
    - [ ] Implement `EcoResilienceAgent` class synthesizing TEK and Unified Physics.
    - [ ] Integrate with the Cohezion swarm execution loop.
    - [ ] Verify 100% coverage.
- [ ] **Task: Initial Simulation Run & Validation**
    - [ ] Execute an ecosystem resilience simulation using the prototype.
    - [ ] Document the 12D state trajectories of the simulation.
    - [ ] Use Mycelium (ShadowScripter) to grow regression tests around the simulation results.
- [ ] **Task: Conductor - User Manual Verification 'Phase 3: EcoResilience Synthesis & Prototype' (Protocol in workflow.md)**

## Phase 4: Documentation & Finalization
- [ ] **Task: Obsidian Knowledge Vault Update**
    - [ ] Document "Gemma 4 Good" hackathon opportunities identified.
    - [ ] Link TEK concepts to 12D manifolds and HIHO stability in the vault.
- [ ] **Task: Repo Cleanup & Final Walkthrough**
    - [ ] Ensure all code adheres to project style guidelines.
    - [ ] Perform final full test suite run.
    - [ ] Generate an interactive Marimo walkthrough for the EcoResilience agent.
- [ ] **Task: Conductor - User Manual Verification 'Phase 4: Documentation & Finalization' (Protocol in workflow.md)**
