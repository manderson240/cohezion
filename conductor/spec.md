# Track Specification: Gemma 4 Integration & EcoResilience Synthesis

## Overview
This track focuses on the rapid integration of the newly released **Gemma 4** open models (March 31, 2026) into the Cohezion ecosystem. By leveraging Gemma 4's advanced reasoning ("Thinking Mode"), extended context windows (up to 256K), and native multimodal support, we will identify and implement a high-impact strategy for the **"Gemma 4 Good" Kaggle Hackathon**. The core opportunity identified is the synthesis of **Traditional Ecological Knowledge (TEK)** from Indigenous worldviews with **Unified Physics (12D Manifolds/HIHO Stability)** for advanced ecosystem resilience modeling.

## Functional Requirements
1.  **Gemma 4 Model Provider (`Gemma4Provider`)**:
    - Implement a new provider in `src/cohezion/providers/` following the existing `ModelProvider` interface.
    - Add support for Gemma 4-specific configurations (e.g., `thinking_mode: true`, `context_window: 256000`).
    - Integrate with Ollama's native tool-calling and structured JSON output for Gemma 4.
2.  **Multi-Size Model Benchmarking**:
    - Create a benchmarking script to evaluate performance on local hardware (128GB RAM/UMA):
        - **31B Dense**: Deep reasoning, complex manifold calculations.
        - **26B MoE**: High-performance agent orchestration.
        - **Effective 4B (E4B)**: Fast simulation steering.
        - **Effective 2B (E2B)**: Low-latency daily research and token-efficient classification.
3.  **EcoResilience Specialist Agent**:
    - Develop a prototype specialist agent prompt that bridges:
        - **Indigenous TEK**: Interconnectedness, systemic balance, and seasonal cycles.
        - **Unified Physics**: 12D state trajectories, HIHO stability (0.5 coherence), and FLUME encoding.
    - Implement an initial "Ecosystem Resilience" simulation using this agent.
4.  **Compound Engineering Integration**:
    - Ensure the `Gemma4Provider` is accessible to the existing Research Swarm, FLUME VAE, and World Model modules.

## Non-Functional Requirements
- **Strict TDD**: 100% test coverage for all new provider and agent logic.
- **Token Efficiency**: Optimize routing to use E2B/E4B for simple tasks and 26B/31B only for complex reasoning.
- **Zero-Workslop**: Multi-perspective adversarial review of system prompts.

## Acceptance Criteria
- [ ] Gemma 4 models (31B, 26B, 4B, 2B) are fully operational via Ollama within the Cohezion swarm.
- [ ] Benchmark report documenting speed and accuracy across all four models on local hardware.
- [ ] Successful "EcoResilience" prototype run demonstrating the synthesis of TEK and Unified Physics.
- [ ] Documentation of the "Gemma 4 Good" hackathon opportunities in the Obsidian Knowledge Vault.

## Out of Scope
- Training or fine-tuning Gemma 4 (local execution and RAG/few-shot only).
- Non-Ollama inference providers for Gemma 4 (Ollama-only for this track).
