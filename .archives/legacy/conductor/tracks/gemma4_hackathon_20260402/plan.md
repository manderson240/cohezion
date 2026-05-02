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

## Phase 5: Advanced Resonance & Swarm Integration (Expansion)
- [x] **Task: Multi-Agent Resonance Loop (Swarm)**
    - [x] Create `tests/swarm/test_ecoresilience_swarm_loop.py` for collaborative tasks.
    - [x] Implement a specialized `SwarmOrchestrator` sub-protocol where `EcoResilienceAgent` (Gemma 4) leads a trio with `PhysicsAgent` (Ollama) and `BiologistAgent` (Mistral).
    - [x] Define the "Resonance Protocol" for cross-agent 12D state vector sharing.
    - [x] Verify coherence with `HIHOStabilityResolver`.
- [x] **Task: Real-world Data Grounding (Data)**
    - [x] Design and implement `src/cohezion/mcp/env_data_mcp.py` to fetch real-time data from NOAA and Copernicus APIs.
    - [x] Update `EcoResilienceAgent` to use this MCP server for "Ground Truth" grounding during simulations.
    - [x] Write integration tests for data-driven agent reasoning.
- [x] **Task: Anima Dashboard Genesis Integration (Visual)**
    - [x] Create `src/web/anima_dashboard/components/EcoResilienceView.tsx` in the Next.js frontend.
    - [x] Implement real-time Three.js visualization for 12D manifold trajectories and HIHO stability indicators.
    - [x] Add SSE (Server-Sent Events) streaming from the `ecoresilience` API endpoint to the dashboard.
- [x] **Task: Gemma 4 QLoRA Specialization (ML)**
    - [x] Prepare a training dataset from the `cohezion/knowledge_graph/` and `cohezion/physics/` domains.
    - [x] Set up a QLoRA fine-tuning script `scripts/ml/finetune_gemma4_cohezion.py` (compatible with the G4 Blackwell/AMD setup).
    - [x] Evaluate the fine-tuned model against the baseline for "Unified Physics" reasoning and TEK synthesis.
- [x] **Task: Conductor - User Manual Verification 'Phase 5: Advanced Resonance & Swarm Integration' (Protocol in workflow.md)**

## Phase 6: Production Hardening & Deployment
- [x] **Task: Performance Optimization (Latency)**
    - [x] Profile the `SwarmOrchestrator` resonance loop for bottlenecks.
    - [x] Implement parallel agent execution within the resonance protocol where possible.
    - [x] Optimize Three.js rendering in `EcoResilienceView.tsx` using `InstancedMesh`.
- [x] **Task: Automated Monitoring & Drift Detection**
    - [x] Integrate `EcoResilienceAgent` with `cohezion.reliability.monitor.ResourceMonitor`.
    - [x] Implement drift detection for 12D trajectories to identify simulation instability early.
    - [x] Create a Slack/Discord notification hook for HIHO stability breaches.
- [x] **Task: Production-Ready Scaling**
    - [x] Containerize the `EnvDataMCP` server for Kubernetes deployment.
    - [x] Set up a production-ready model routing fallback chain (Gemma 4 -> Gemini Flash).
    - [x] Finalize the interactive Marimo dashboard for public presentation.
- [x] **Task: Conductor - User Manual Verification 'Phase 6: Production Hardening & Deployment' (Protocol in workflow.md)**

## Phase 7: Rich Multimodal Synthesis & Actual Testing
- [x] **Task: Knowledge Graph Grounding (Gemma 4 Model Card)**
    - [x] Create `src/cohezion/knowledge_graph/GEMMA4_MODEL_CARD.md` with extracted specs.
    - [x] Update `MISSION_JOURNAL.md` to reference the new model card grounding.
- [x] **Task: Gemma 4 Visual Component Synthesis**
    - [x] Update `EcoResilienceAgent` to generate precise DALL-E/Stable Diffusion prompts for ecosystem "Resilience Maps".
    - [x] Integrate with `nanobanana` to generate actual images during simulations.
    - [x] Add a `generate_diagram` method to the agent using Mermaid.js syntax for ecosystem flowcharts.
- [x] **Task: Sonification Parameter Generation**
    - [x] Update `EcoResilienceAgent` to output `Tone.js` parameters based on 12D state transitions.
    - [x] Connect the agent's output to the dashboard's audio engine for "Resonance Sonification".
- [x] **Task: "Resonance Mission" Execution Script**
    - [x] Create `scripts/test_resonance_mission.py` to run a full multi-agent scenario.
    - [x] Generate real assets (Images, Diagrams, Audio Params) during the script execution.
    - [x] Capture these assets in `src/web/anima_dashboard/public/generated/`.
- [x] **Task: Final Multimodal Dashboard Validation**
    - [x] Update `EcoResilienceView.tsx` to display generated images and diagrams.
    - [x] Perform a full "Night Run" validation to ensure all components resonate.
- [x] **Task: Conductor - User Manual Verification 'Phase 7: Rich Multimodal Synthesis' (Protocol in workflow.md)**



