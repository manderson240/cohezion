# Implementation Plan: Universe Telemetry Mesh (Physics/Intent Unification)

## Phase 1: The Thinker (Correlation & Schema Design)
- [x] Task: Define `UniverseStateEvent` Schema
    - [x] Create schema in `src/cohezion/data_mesh/` that supports 12D vectors, HIHO stability, and the `trigger_journey_id`.
- [x] Task: Design Geometric Overlap Logic
    - [x] Implement the L2 distance calculation between down-projected latent states and axiomatic physical states.
- [x] Task: Conductor - User Manual Verification 'The Thinker' (Protocol in workflow.md)

## Phase 2: The Doer (Implementation - Instrumentation)
- [x] Task: Write Failing Tests (Red Phase)
    - [x] Verify that a simulated physics shift emits the correct telemetry event.
- [x] Task: Instrument Universe Core (Green Phase)
    - [x] Modify `src/cohezion/universe/engine.py` to calculate stability shifts and emit events to the `TelemetryBus`.
- [x] Task: Integrate Physics-as-a-Policy (Green Phase)
    - [x] Update Ouroboros to consume physics events and detect "Physical Surprise."
- [x] Task: Conductor - User Manual Verification 'The Doer (Instrumentation)' (Protocol in workflow.md)

## Phase 3: The Doer (Implementation - Holographic Dash)
- [x] Task: Build Holographic Record Loader
    - [x] Update the SurrealDB client to perform complex joins between `journey_transitions` and `physics_states`.
- [x] Task: Build 3D Ghost Dashboard (Marimo)
    - [x] Implement the Plotly overlay showing agent trajectories on physical manifolds.
    - [x] Create the "Pressure Heatmap" showing where reasoning shifts the substrate.
- [x] Task: Implement Dissonance Sonification (Tone.js)
    - [x] Map field transitions to audio frequencies based on distance from the 0.5 stability point.
- [x] Task: Conductor - User Manual Verification 'The Doer (Dashboard)' (Protocol in workflow.md)

## Phase 4: The Knower (Validation & Persistence)
- [x] Task: System Validation (The Holographic Run)
    - [x] Run a simulation where a swarm attempt to solve a problem that violates physical laws.
    - [x] Verify that the dashboard shows "Pressure" and the audio engine emits "Dissonance."
- [x] Task: Document & Persist
    - [x] Extract "Learning 370" about physics/intent correlation.
    - [x] Finalize Journey Retrospective and accept the track.
- [x] Task: Conductor - User Manual Verification 'The Knower' (Protocol in workflow.md)
