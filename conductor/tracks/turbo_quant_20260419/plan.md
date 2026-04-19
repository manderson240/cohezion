# Implementation Plan: Unlock Turbo Quant on local silicon

## Phase 1: The Thinker (Definition, Decomposition, & Harness Design)
- [ ] Task: Define System Requirements & Architecture
    - [ ] Formalize integration boundaries with Lemonade Server and OllamaProvider.
    - [ ] Map AMD NPU/iGPU/CPU distribution logic.
- [ ] Task: Module Design (AutoHarness)
    - [ ] Synthesize deterministic AutoHarness for 4-bit, 8-bit, and mixed-precision tensors.
    - [ ] Define invariant validation for HIHO stability (0.5 coherence) during quantization.
- [ ] Task: Conductor - User Manual Verification 'The Thinker (Definition, Decomposition, & Harness Design)' (Protocol in workflow.md)

## Phase 2: The Doer (Implementation & Unit Verification - Core Engine)
- [ ] Task: Write Failing Tests (Red Phase) - Triton Kernels
    - [ ] Create unit tests for custom AMD Triton Kernels (ROCm/HIP).
    - [ ] Ensure tests fail on unoptimized execution paths.
- [ ] Task: Implement Triton Kernels (Green Phase)
    - [ ] Develop and optimize Triton kernels for 4-bit, 8-bit, and mixed precision.
    - [ ] Distribute workload explicitly across NPU, iGPU, and CPUs.
- [ ] Task: Write Failing Tests (Red Phase) - FLUME VAE Integration
    - [ ] Create tests verifying latent space operations against the AutoHarness.
- [ ] Task: Implement FLUME VAE Quantization (Green Phase)
    - [ ] Integrate Turbo Quant into FLUME VAE operations.
- [ ] Task: Refactor & Manifold Integration
    - [ ] Integrate kernels and VAE changes into the core engine.
    - [ ] Verify 100% test coverage for new modules.
- [ ] Task: Conductor - User Manual Verification 'The Doer (Implementation & Unit Verification - Core Engine)' (Protocol in workflow.md)

## Phase 3: The Doer (Implementation & Unit Verification - Ecosystem)
- [ ] Task: Write Failing Tests (Red Phase) - Lemonade Server & Ollama
    - [ ] Create tests for Lemonade Server backend routing.
    - [ ] Create tests for OllamaProvider fallback routing.
- [ ] Task: Implement Ecosystem Integration (Green Phase)
    - [ ] Wire Lemonade Server to utilize the optimized Triton Kernels.
    - [ ] Implement seamless OllamaProvider fallback support.
- [ ] Task: Refactor & Manifold Integration
    - [ ] Run full system regression to ensure HIHO stability remains exactly at 0.5.
    - [ ] Profile memory and speed to confirm >= 40% VRAM reduction and >= 30% tokens/sec increase.
- [ ] Task: Conductor - User Manual Verification 'The Doer (Implementation & Unit Verification - Ecosystem)' (Protocol in workflow.md)

## Phase 4: The Knower (Validation & Persistence)
- [ ] Task: System Validation (Adversarial Review)
    - [ ] Execute multi-perspective swarm critique on all modified code paths.
    - [ ] Fix any identified "workslop" or security vulnerabilities.
- [ ] Task: Document & Persist
    - [ ] Extract "Key Learnings" to the Obsidian Knowledge Vault.
    - [ ] Update `plan.md` to reflect 100% completion.
- [ ] Task: Final Acceptance
    - [ ] Log the 12D trajectory of the phase into SurrealDB.
    - [ ] Perform Journey Retrospective.
- [ ] Task: Conductor - User Manual Verification 'The Knower (Validation & Persistence)' (Protocol in workflow.md)