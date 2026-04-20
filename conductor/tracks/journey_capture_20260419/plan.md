# Implementation Plan: Agentic Journey Capture (FLUME & Quadrature Nexus)

## Phase 1: The Thinker (Look Outward, Look Inward & Architecture)
- [ ] Task: Look Outward (External SOTA Research)
    - [ ] Activate the `huggingface-papers` skill and use `mcp_huggingface_paper_search` to search arXiv and the Hugging Face Hub for recent breakthroughs in "JEPA-aligned World Models" and trajectory prediction.
    - [ ] Use `google_web_search` to explore "awesome latent spaces" to map SOTA 256-dim embedding representations.
    - [ ] Synthesize external findings to inform our internal trajectory schema.
- [ ] Task: Look Inward (Audit Existing Infrastructure)
    - [ ] Activate `JOURNEY_TRACKING_PRIME` and review `src/cohezion/knowledge_graph/` for existing 12D state vector schemas.
    - [ ] Query the local SurrealDB instances (ports 8000/8001) to catalog existing tables related to agentic journeys and R-Zero metrics.
- [ ] Task: Define Schema and Non-Blocking Interface (AutoHarness Mandate)
    - [ ] Automatically synthesize a deterministic AutoHarness using `qwen3.5:coder` or `phi4-mini` to validate the telemetry pipeline per the `arXiv:2603.03329v1` mandate.
    - [ ] Create a robust `FlumeJourneyEvent` schema supporting: 256-dim z-vectors, 12D State Vectors, 4 Fabrics & Awareness, 5 Expert Streams, and R-Zero Metrics.
    - [ ] Design an asynchronous, non-blocking event bus to decouple trajectory logging from the core orchestration loop.
- [ ] Task: Conductor - User Manual Verification 'The Thinker' (Protocol in workflow.md)

## Phase 2: The Doer (Implementation - Instrumentation & Healing)
- [ ] Task: Write Failing Tests (Red Phase)
    - [ ] Create tests verifying that the Quadrature Nexus deliberation emits the full `FlumeJourneyEvent` asynchronously without blocking.
- [ ] Task: Instrument Quadrature Nexus & FLUME (Green Phase)
    - [ ] Instrument `FlumeEncoder` to emit the 256-dim z-vectors and predicted trajectories.
    - [ ] Modify `src/cohezion/swarm/quadrature_nexus.py` to capture and emit the 12D state, the 4 Fabrics, R-Zero metrics, and the 5 Expert Streams routing context during consensus building to the event bus.
- [ ] Task: Integrate Ouroboros & Healing System (Green Phase)
    - [ ] Pipe the 12D telemetry directly to `Ouroboros` for recursive failure analysis and "Hardening Mutations".
    - [ ] Actively monitor HIHO stability metrics with `cohezion.healing.get_healing_system()`. If coherence deviates from 0.5, trigger the healing system autonomously.
- [ ] Task: Conductor - User Manual Verification 'The Doer (Instrumentation)' (Protocol in workflow.md)

## Phase 3: The Doer (Implementation - Persistence & Visualization)
- [ ] Task: Write Failing Tests (Red Phase)
    - [ ] Create mock tests for SurrealDB insertion and the visualization dashboard's data loader.
- [ ] Task: Connect to SurrealDB via Circuit Breakers (Green Phase)
    - [ ] Wrap async DB calls with `cohezion.reliability.get_circuit()` and `cohezion.reliability.pool.get_pool()`.
    - [ ] Wire the event bus into a background worker that persists `FlumeJourneyEvent` objects to the local SurrealDB (`ws://localhost:8000`).
- [ ] Task: Build Interactive Dashboard with Sonification (Green Phase)
    - [ ] Create an interactive dashboard (Plotly/Dash or Marimo) that queries SurrealDB and plots the 12D trajectory, the 256-dim latent PCA projection, and the 0.5 HIHO stability line over time.
    - [ ] Integrate Tone.js (or Python equivalent audio synthesis) to sonify the field transitions, mapping audio frequencies to the distance from the 0.5 stability point.
- [ ] Task: Conductor - User Manual Verification 'The Doer (Persistence & Visualization)' (Protocol in workflow.md)

## Phase 4: The Knower (Validation & Persistence)
- [ ] Task: System Validation
    - [ ] Run a complex, long-horizon test script utilizing the `TriuneOrchestrator` (local Turbo Quant) to flood the system with events.
    - [ ] Open the dashboard and visually/audibly verify the trajectories, JEPA predictions, 4 Fabrics, and 5 Expert Stream routing.
    - [ ] Force a drift state to verify the Ouroboros and Healing System trigger correctly.
- [ ] Task: Document & Persist
    - [ ] Extract "Key Learnings" about full-spectrum trajectory capture to the Knowledge Vault.
    - [ ] Update `plan.md` to reflect 100% completion.
- [ ] Task: Final Acceptance
    - [ ] Log the 12D trajectory of the phase itself into SurrealDB.
    - [ ] Perform Journey Retrospective.
- [ ] Task: Conductor - User Manual Verification 'The Knower' (Protocol in workflow.md)