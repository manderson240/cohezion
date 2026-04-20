# Implementation Plan: Triune Orchestrator for Long Horizon Experiments

## Objective
Implement a reusable `TriuneOrchestrator` module that leverages the `GaiaAgentTier` and the `TieredOrchestrator` to automatically route complex, long-horizon tasks across the AMD Strix Halo architecture (NPU on port 13306, iGPU on port 13307, and CPU on port 11434). This approach yields maximum compound engineering returns by formalizing the hardware-aware dispatch logic into a permanent fixture of `cohezion.inference`.

## Phase 1: The Thinker (Module Design & Architecture)
- [x] Task: Create `src/cohezion/inference/triune_orchestrator.py`
  - [x] Implement `build_triune_orchestrator()` factory function.
  - [x] Configure Tier 0 (NPU) using `qwen3.5-4b-FLM` via `GaiaAgentTier` with a fast-reject quality gate (e.g., min_chars=500).
  - [x] Configure Tier 1 (iGPU) using `Gemma-4-E4B-it-GGUF` via `GaiaAgentTier` (port 13307) with an analytical quality gate (e.g., min_chars=1500).
  - [x] Configure Tier 2 (CPU) using `Gemma-4-31B-it-GGUF` (port 11434) with `QualityGate.TRUST` for the final fallback reasoning.
- [x] Task: Conductor - User Manual Verification 'The Thinker' (Protocol in workflow.md)

## Phase 2: The Doer (Unit Verification & Core Engine)
- [x] Task: Write Failing Tests (Red Phase)
  - [x] Create `tests/inference/test_triune_orchestrator.py` to test the factory construction and hardware routing fallback logic.
- [x] Task: Implement Triune Orchestrator (Green Phase)
  - [x] Ensure the orchestrator smoothly hands off the long-horizon context if a lower-tier node returns an error or fails a quality gate.
- [x] Task: Conductor - User Manual Verification 'The Doer' (Protocol in workflow.md)

## Phase 3: The Doer (Ecosystem Integration)
- [x] Task: Create Executable Script `scripts/run_long_horizon_experiment.py`
  - [x] Instantiate the `TriuneOrchestrator`.
  - [x] Execute a complex task evaluating the thermodynamic and cognitive implications of 3.5-bit TurboQuant on the emergence of local AGI.
  - [x] Log the `escalation_count` and final `resolving_tier` to output.
- [x] Task: Conductor - User Manual Verification 'The Doer Ecosystem' (Protocol in workflow.md)

## Phase 4: The Knower (Validation & Persistence)
- [x] Task: System Validation
  - [x] Execute `scripts/run_long_horizon_experiment.py`.
  - [x] Verify that the NPU, iGPU, or CPU handles the context appropriately based on the required depth of analysis.
- [x] Task: Document & Persist
  - [x] Add insights from the orchestrator run to `KEY_LEARNINGS.md` (Learning 368 added).
  - [x] Perform Journey Retrospective.
- [x] Task: Conductor - User Manual Verification 'The Knower' (Protocol in workflow.md)
