# Plan: Agentic Journey Capture (FLUME & Quadrature Nexus)

## Objective
Implement a comprehensive telemetry system that captures, persists, and visualizes the "agentic journeys" of the Cohezion swarm. This involves instrumenting the Quadrature Nexus and FLUME engines to record 12D state trajectories and JEPA-aligned predictive states into SurrealDB, enabling autonomous drift recovery and real-time visualization.

## Background & Motivation
The swarm requires real-time observability into its decision-making trajectories to detect HIHO divergence and autonomously trigger the healing system. Integrating Gemini Deep Research will synthesize external trajectory models, and local inference orchestration will minimize cloud token costs.

## Scope & Impact
- Instrument `FlumeEncoder` and `Quadrature Nexus`.
- Integrate `Ouroboros` and the Cohezion Healing System.
- Integrate Gemini Deep Research via the interactions API.
- Create an interactive visualization dashboard (Anima Dashboard).

## Proposed Solution
- Create a `FlumeJourneyEvent` schema.
- Implement an asynchronous telemetry bus connected to SurrealDB.
- Utilize local SLMs for internal reasoning validation.
- Trigger Deep Research for complex "Look Outward" tasks via the Gemini CLI.

## Alternatives Considered
- Direct logging to JSONL: Rejected due to lack of queryability for the Ouroboros system.
- Cloud-only research: Rejected due to high token costs; local SLMs will supplement.

## Implementation Plan
### Phase 1: The Thinker (Look Outward, Look Inward & Architecture)
- [x] Task: Look Outward (External SOTA Research)
    - [x] Activate `huggingface-papers` skill.
    - [x] Explore "awesome latent spaces".
    - [~] **NEW**: Integrate Gemini Deep Research for automated, multi-step synthesis of SOTA trajectory prediction models. Use the Interactions API to generate a cited report in the vault.
- [x] Task: Look Inward (Audit Existing Infrastructure)
    - [x] Activate `JOURNEY_TRACKING_PRIME`.
    - [x] Query local SurrealDB instances.
    - [~] **NEW**: Optimize "Look Inward" tasks by orchestrating with local SLMs (Gemma 4 / Qwen3) to reduce cloud token consumption.
- [x] Task: Define Schema and Non-Blocking Interface (AutoHarness Mandate)
    - [x] Synthesize deterministic AutoHarness.
    - [x] Create `FlumeJourneyEvent` schema.
    - [x] Design asynchronous event bus.

### Phase 2: The Doer (Implementation - Instrumentation & Healing)
- [x] Task: Write Failing Tests (Red Phase)
- [x] Task: Instrument Quadrature Nexus & FLUME (Green Phase)
- [x] Task: Integrate Ouroboros & Healing System (Green Phase)

### Phase 3: The Doer (Implementation - Persistence & Visualization)
- [x] Task: Write Failing Tests (Red Phase)
- [x] Task: Connect to SurrealDB via Circuit Breakers (Green Phase)
- [x] Task: Build Interactive Dashboard with Sonification (Green Phase)

### Phase 4: The Knower (Validation & Persistence)
- [x] Task: System Validation
- [x] Task: Document & Persist
- [x] Task: Final Acceptance

## Verification
- Run `uv run pytest tests/test_journey_instrumentation.py`
- Verify events are emitted to the telemetry bus and stored in SurrealDB.
- Visually verify trajectories in the Anima Dashboard.
- Verify Gemini Deep Research interaction initializes and logs a report.

## Migration & Rollback
- If the SurrealDB schema changes, implement a migration script.
- If Deep Research integration fails or exceeds the budget limit, disable the configuration flag and revert to standard web search tools.
