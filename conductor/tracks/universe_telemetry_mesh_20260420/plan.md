# Implementation Plan: Universe Telemetry Mesh (Physics/Intent Unification)

## Phase 1: The Thinker (Correlation & Schema Design)
- [ ] Task: Define `UniverseStateEvent` Schema
    - [ ] Create schema in `src/cohezion/data_mesh/` that supports 12D vectors, HIHO stability, and the `trigger_journey_id`.
- [ ] Task: Design Geometric Overlap Logic
    - [ ] Implement the L2 distance calculation between down-projected latent states and axiomatic physical states.
- [ ] Task: Conductor - User Manual Verification 'The Thinker' (Protocol in workflow.md)

## Phase 2: The Doer (Implementation - Instrumentation)
- [ ] Task: Write Failing Tests (Red Phase)
    - [ ] Verify that a simulated physics shift emits the correct telemetry event.
- [ ] Task: Instrument Universe Core (Green Phase)
    - [ ] Modify `src/cohezion/universe/engine.py` to calculate stability shifts and emit events to the `TelemetryBus`.
- [ ] Task: Integrate Physics-as-a-Policy (Green Phase)
    - [ ] Update Ouroboros to consume physics events and detect "Physical Surprise."
- [ ] Task: Conductor - User Manual Verification 'The Doer (Instrumentation)' (Protocol in workflow.md)

## Phase 3: The Doer (Implementation - Holographic Dash)
- [ ] Task: Build Holographic Record Loader
    - [ ] Update the SurrealDB client to perform complex joins between `journey_transitions` and `physics_states`.
- [ ] Task: Build 3D Ghost Dashboard (Marimo)
    - [ ] Implement the Plotly overlay showing agent trajectories on physical manifolds.
    - [ ] Create the "Pressure Heatmap" showing where reasoning shifts the substrate.
- [ ] Task: Implement Dissonance Sonification (Tone.js)
    - [ ] Map field transitions to audio frequencies based on distance from the 0.5 stability point.
- [ ] Task: Conductor - User Manual Verification 'The Doer (Dashboard)' (Protocol in workflow.md)

## Phase 4: The Knower (Validation & Persistence)
- [ ] Task: System Validation (The Holographic Run)
    - [ ] Run a simulation where a swarm attempt to solve a problem that violates physical laws.
    - [ ] Verify that the dashboard shows "Pressure" and the audio engine emits "Dissonance."
- [ ] Task: Document & Persist
    - [ ] Extract "Learning 370" about physics/intent correlation.
    - [ ] Finalize Journey Retrospective and accept the track.
- [ ] Task: Conductor - User Manual Verification 'The Knower' (Protocol in workflow.md)
