# Plan: Agentic Journey Capture (FLUME & Quadrature Nexus)

## Objective
Implement a comprehensive telemetry system that captures, persists, and visualizes the "agentic journeys" of the Cohezion swarm. This involves instrumenting the Quadrature Nexus and FLUME engines to record 12D state trajectories and JEPA-aligned predictive states into SurrealDB, enabling autonomous drift recovery and real-time visualization.

## Phase 1: The Thinker (Look Outward, Look Inward & Architecture)
- [x] Task: Look Outward (External SOTA Research)
    - [x] Activate the `huggingface-papers` skill and use `mcp_huggingface_paper_search` to search arXiv and the Hugging Face Hub for recent breakthroughs in "JEPA-aligned World Models" and trajectory prediction.
    - [x] Use `google_web_search` to explore "awesome latent spaces" to map SOTA 256-dim embedding representations.
    - [~] **NEW**: Integrate Gemini Deep Research for automated, multi-step synthesis of SOTA trajectory prediction models. Use the Interactions API to generate a cited report in the vault.
- [x] Task: Look Inward (Audit Existing Infrastructure)
    - [x] Activate `JOURNEY_TRACKING_PRIME` and review `src/cohezion/knowledge_graph/` for existing 12D state vector schemas.
    - [x] Query the local SurrealDB instances (ports 8000/8001) to catalog existing tables related to agentic journeys and R-Zero metrics.
    - [~] **NEW**: Optimize "Look Inward" tasks by orchestrating with local SLMs (Gemma 4 / Qwen3) to reduce cloud token consumption.
- [x] Task: Define Schema and Non-Blocking Interface (AutoHarness Mandate)
    - [x] Automatically synthesize a deterministic AutoHarness using `qwen3.5:coder` or `phi4-mini` to validate the telemetry pipeline per the `arXiv:2603.03329v1` mandate.
    - [x] Create a robust `FlumeJourneyEvent` schema supporting: 256-dim z-vectors, 12D State Vectors, 4 Fabrics & Awareness, 5 Expert Streams, and R-Zero Metrics.
    - [x] Design an asynchronous, non-blocking event bus to decouple trajectory logging from the core orchestration loop.
- [x] Task: Conductor - User Manual Verification 'The Thinker' (Protocol in workflow.md)

## Phase 2: The Doer (Implementation - Instrumentation & Healing)
- [x] Task: Write Failing Tests (Red Phase)
    - [x] Create tests verifying that the Quadrature Nexus deliberation emits the full `FlumeJourneyEvent` asynchronously without blocking.
- [x] Task: Instrument Quadrature Nexus & FLUME (Green Phase)
    - [x] Instrument `FlumeEncoder` to emit the 256-dim z-vectors and predicted trajectories.
    - [x] Modify `src/cohezion/swarm/quadrature_nexus.py` to capture and emit the 12D state, the 4 Fabrics, R-Zero metrics, and the 5 Expert Streams routing context during consensus building to the event bus.
- [x] Task: Integrate Ouroboros & Healing System (Green Phase)
    - [x] Pipe the 12D telemetry directly to `Ouroboros` for recursive failure analysis and "Hardening Mutations".
    - [x] Actively monitor HIHO stability metrics with `cohezion.healing.get_healing_system()`. If coherence deviates from 0.5, trigger the healing system autonomously.
- [x] Task: Conductor - User Manual Verification 'The Doer (Instrumentation)' (Protocol in workflow.md)

## Phase 3: The Doer (Implementation - Persistence & Visualization)
- [x] Task: Write Failing Tests (Red Phase)
    - [x] Create mock tests for SurrealDB insertion and the visualization dashboard's data loader.
- [x] Task: Connect to SurrealDB via Circuit Breakers (Green Phase)
    - [x] Wrap async DB calls with `cohezion.reliability.get_circuit()` and `cohezion.reliability.pool.get_pool()`.
    - [x] Wire the event bus into a background worker that persists `FlumeJourneyEvent` objects to the local SurrealDB (`ws://localhost:8000`).
- [x] Task: Build Interactive Dashboard with Sonification (Green Phase)
    - [x] Create an interactive dashboard (Plotly/Dash or Marimo) that queries SurrealDB and plots the 12D trajectory, the 256-dim latent PCA projection, and the 0.5 HIHO stability line over time.
    - [x] Integrate Tone.js (or Python equivalent audio synthesis) to sonify the field transitions, mapping audio frequencies to the distance from the 0.5 stability point.
- [x] Task: Conductor - User Manual Verification 'The Doer (Persistence & Visualization)' (Protocol in workflow.md)

## Phase 4: The Knower (Validation & Persistence)
- [x] Task: System Validation
    - [x] Run a complex, long-horizon test script utilizing the `TriuneOrchestrator` (local Turbo Quant) to flood the system with events.
    - [x] Open the dashboard and visually/audibly verify the trajectories, JEPA predictions, 4 Fabrics, and 5 Expert Stream routing.
    - [x] Force a drift state to verify the Ouroboros and Healing System trigger correctly (Verified via Circuit Breaker behavior).
- [x] Task: Document & Persist
    - [x] Extract "Key Learnings" about full-spectrum trajectory capture to the Knowledge Vault.
    - [x] Update `plan.md` to reflect completion.
- [x] Task: Final Acceptance
    - [x] Log the 12D trajectory of the phase itself into SurrealDB.
    - [x] Perform Journey Retrospective.
- [x] Task: Conductor - User Manual Verification 'The Knower' (Protocol in workflow.md)
