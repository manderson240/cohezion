# Improved Universe Simulations Implementation Plan

Created: 2026-02-18
Status: PENDING
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)
>
> - PENDING: Initial state, awaiting implementation
> - COMPLETE: All tasks implemented
> - VERIFIED: All checks passed
>
> **Approval Gate:** Implementation CANNOT proceed until `Approved: Yes`
> **Worktree:** Set at plan creation (from dispatcher). `Yes` uses git worktree isolation; `No` works directly on current branch

## Summary

**Goal:** Transform Cohezion's universe simulation into an agentic training environment aligned with Anthropic's Universes team research — building environments where agents (modeled as Exotic Vacuum Objects) navigate ambiguity, handle interruptions, maintain context, and exercise judgment. Wire together FLUME VAE encoding, Quadrature Nexus orchestration, Levin's bioelectric navigation, Mycelium regression defense, and Ouroboros self-healing into one end-to-end training pipeline with RL-based evaluation.

**Architecture:** An `AgenticScenarioEngine` generates training scenarios with configurable difficulty (ambiguity, interruptions, context length, judgment complexity). Agents execute scenarios as EVO (Exotic Vacuum Object) entities navigating 12D morphospace via bioelectric signals. The FLUME VAE encodes journey trajectories into 256D latent representations. The Quadrature Nexus dispatches scenarios across fabrics. An RL `CapabilityEvaluator` scores genuine agent capability beyond pattern matching. Ouroboros records flight data for replay and self-healing.

**Tech Stack:** Python 3.13+, numpy, existing FLUME/bioelectric/sandbox infrastructure, pytest

## Scope

### In Scope

- Agentic scenario generation engine (ambiguity, interruptions, context, judgment)
- EVO agent model (agents as exotic vacuum objects in morphospace)
- FLUME VAE integration into journey encoding pipeline
- Quadrature Nexus scenario dispatch and fabric routing
- RL capability evaluation framework (multi-dimensional reward modeling)
- Bioelectric navigation for agent decision-making in scenarios
- Ouroboros flight recorder integration for scenario replay
- Mycelium-style automated test synthesis hooks
- End-to-end pipeline connecting all components

### Out of Scope

- Docker sandbox changes (existing sandbox infrastructure is sufficient)
- SurrealDB schema migrations (existing schema handles new data)
- Frontend/UI changes
- Cloud deployment changes
- New PRIME skill definitions (can be created in follow-up)
- Training actual LLM models (we build the environment, not the training loop)

## Prerequisites

- Existing `src/cohezion/universe/` module with engine, sandbox, divergence detection
- Existing `src/cohezion/flume/` module with VAE encoder, bioelectric engine, LCSP
- Existing `src/cohezion/swarm/` module with QuadratureNexus, perception, topology
- Existing `src/cohezion/compound/journey_tracker.py`

## Context for Implementer

> This section is critical for cross-session continuity. Write it for an implementer who has never seen the codebase.

- **Patterns to follow:**
  - Sandbox execution pattern in `src/cohezion/universe/sandbox_manager.py:106` — circuit breaker + memory budget + backpressure
  - Journey tracking pattern in `src/cohezion/compound/journey_tracker.py:354` — `track_execution()` method
  - Bioelectric step pattern in `src/cohezion/flume/bioelectric.py:127` — `step()` returns (new_state, action_vector)
  - Perception event pattern in `src/cohezion/swarm/perception.py:120` — `perceive_step()` with manifold collapse
  - QuadratureNexus orchestration in `src/cohezion/swarm/executive.py:74` — `execute_mission()`

- **Conventions:**
  - All simulation modules use `logging.getLogger(__name__)`
  - Dataclasses for value objects, classes for stateful components
  - 12D vectors map to AxiomaticState dimensions: spatial_xyz, temporal, physics, biology, logic, quantum, field, control, novelty, precipitation
  - HIHO = 0.5 coherence target (Half-In-Half-Out)
  - Non-blocking try/except for all observability operations
  - Singleton pattern with `reset()` for testing (see SandboxManager)

- **Key files the implementer must read first:**
  - `src/cohezion/universe/engine.py` — Core universe simulation, AxiomaticState, UniverseJourney, trajectory evolution
  - `src/cohezion/flume/bioelectric.py` — BioelectricEngine, encode_signal/decode_action/step pattern
  - `src/cohezion/swarm/executive.py` — QuadratureNexus, fabric swarms, mission execution
  - `src/cohezion/swarm/perception.py` — JourneyPerception, CosmologicalPoint, EvoCoreSensing
  - `src/cohezion/compound/journey_tracker.py` — JourneyTracker, holographic_project, track_execution

- **Gotchas:**
  - `engine.py` imports `cohezion_core.cohezion_core_rs.FlumePhysics` (Rust) — may not be available in all environments, needs fallback
  - `engine.py` also imports `cohezion.core.multimodal_bridge` and `cohezion.core.routing.manifold_bridge` — lazy imports needed
  - The existing `SimpleEncoder` in engine.py is hash-based, not semantic — FLUME VAE replaces this
  - `OuroborosRecorder` is referenced in `__main__.py:590` as `from cohezion.system.ouroboros_recorder import OuroborosRecorder` — Task 7 creates this at the correct path
  - Tests must mock Rust extensions (`cohezion_core`) and Docker

- **Domain context:**
  - Agents = Exotic Vacuum Objects (EVOs): charge clusters that maintain coherence through HIHO stability at 0.5
  - Bioelectric signals encode gradient from current state toward target morphology
  - Morphospace = the 12D space agents navigate; StabilityWells are attractors
  - FLUME VAE encodes 2048D → 256D latent space for efficient similarity matching
  - Quadrature Nexus = 4-fabric orchestrator (Space, Field, Control, Precipitation)
  - Mycelium = automated test synthesis network (ShadowScripter pattern)
  - Ouroboros = system flight recorder for replay and self-healing

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [ ] Task 1: Agentic Scenario Engine
- [ ] Task 2: EVO Agent Model
- [ ] Task 3: FLUME VAE Journey Encoder
- [ ] Task 4: RL Capability Evaluator
- [ ] Task 5: Bioelectric Scenario Navigator
- [ ] Task 6: Quadrature Nexus Scenario Dispatch
- [ ] Task 7: Ouroboros Flight Recorder
- [ ] Task 8: End-to-End Pipeline Integration

**Total Tasks:** 8 | **Completed:** 0 | **Remaining:** 8

## Implementation Tasks

### Task 1: Agentic Scenario Engine

**Objective:** Create a scenario generator that produces training situations requiring agents to navigate ambiguity, handle interruptions, maintain context over extended interactions, and exercise judgment — the core capabilities Anthropic's Universes team evaluates.

**Dependencies:** None

**Files:**

- Create: `src/cohezion/universe/scenarios.py`
- Test: `tests/universe/test_scenarios.py`

**Key Decisions / Notes:**

- Scenarios are dataclass-based definitions with configurable difficulty dimensions:
  - `ambiguity_level` (0.0-1.0): How unclear the goal/instructions are
  - `interruption_count` (0-N): Number of context-switching interruptions
  - `context_depth` (1-N): How many prior steps must be remembered
  - `judgment_complexity` (0.0-1.0): Degree of nuanced evaluation needed
- `ScenarioGenerator` produces scenarios from templates with random perturbation
- Scenario types: `navigation` (find target in morphospace), `maintenance` (keep coherence under perturbation), `judgment` (choose between competing objectives), `interruption` (resume after context switch)
- Each scenario defines a `reward_function` that maps agent trajectory to score
- Follow the dataclass + engine pattern from `universe/engine.py`

**Definition of Done:**

- [ ] `ScenarioGenerator.generate()` produces valid `Scenario` objects with all fields populated
- [ ] At least 4 scenario types implemented (navigation, maintenance, judgment, interruption)
- [ ] Scenarios have configurable difficulty via `ScenarioDifficulty` dataclass
- [ ] Each scenario type has a corresponding reward function
- [ ] All tests pass: `uv run pytest tests/universe/test_scenarios.py -q`

**Verify:**

- `uv run pytest tests/universe/test_scenarios.py -q`

### Task 2: EVO Agent Model

**Objective:** Model agents as Exotic Vacuum Objects (EVOs) — charge clusters that maintain coherence through the HIHO 0.5 stability mechanism. Agents have internal state (12D morphospace position), perception (sensing local environment), and action (bioelectric-guided movement).

**Dependencies:** None

**Files:**

- Create: `src/cohezion/universe/evo_agent.py`
- Test: `tests/universe/test_evo_agent.py`

**Key Decisions / Notes:**

- `EVOAgent` dataclass wraps 12D AxiomaticState as agent's "charge cluster" state
- Implements `perceive()` (read local environment), `decide()` (select action), `act()` (apply bioelectric step)
- Agent tracks its own coherence history (EVO stability)
- `EVOPopulation` manages multiple agents with inter-agent field interactions (EVOs influence each other's morphospace)
- Coherence at 0.5 = stable EVO, deviation = charge cluster instability
- Follow the `StabilizerAgent` pattern from `simulation/fractal_universe.py:70` but with explicit EVO physics
- Memory buffer for extended context maintenance (agents remember prior interactions)

**Definition of Done:**

- [ ] `EVOAgent` has perceive/decide/act lifecycle methods
- [ ] Agent maintains coherence history and memory buffer
- [ ] `EVOPopulation` tracks multiple agents with field interactions
- [ ] HIHO coherence invariant tested: coherence tends toward 0.5 over time
- [ ] All tests pass: `uv run pytest tests/universe/test_evo_agent.py -q`

**Verify:**

- `uv run pytest tests/universe/test_evo_agent.py -q`

### Task 3: FLUME VAE Journey Encoder

**Objective:** Build a trajectory-to-latent encoder that serializes 12D trajectory sequences into text representations, then encodes them through the existing FLUME VAE to produce 256D journey embeddings. This provides a **parallel** representation alongside the existing 12D axiomatic space — 12D is used for step-by-step simulation, 256D is used for journey-level similarity matching and experience replay.

**Dependencies:** None

**Files:**

- Create: `src/cohezion/universe/vae_journey_encoder.py`
- Test: `tests/universe/test_vae_journey_encoder.py`

**Key Decisions / Notes:**

- **API mismatch resolution:** `FlumeVAEEncoder.encode()` takes TEXT input, not trajectory sequences. `VAEJourneyEncoder` solves this by: (1) serializing trajectory points to a structured text representation (e.g., `"step:0 coherence:0.85 dims:0.5,0.3,...|step:1 coherence:0.82 dims:0.4,0.3,..."`), then (2) passing that text to `FlumeVAEEncoder.encode()` for 256D embedding
- **Parallel representations:** The existing 12D axiomatic points (from `holographic_project`) continue to be used for per-step simulation and trajectory quality metrics. The new 256D VAE embeddings are a journey-level summary for similarity matching across complete journeys. They DO NOT replace the 12D representation.
- **No JourneyTracker modification needed:** The `VAEJourneyEncoder` operates independently on completed trajectory point lists. No `set_encoder()` on JourneyTracker is needed — the encoder is used by the pipeline (Task 8) after journey completion.
- Falls back to hash-based encoding if VAE checkpoint unavailable (matches existing pattern)
- Follow the `FlumeVAEEncoder` initialization pattern from `flume/vae_encoder.py:59`

**Definition of Done:**

- [ ] `VAEJourneyEncoder.encode_trajectory()` produces 256D vectors from trajectory point sequences via text serialization → VAE encoding
- [ ] Fallback to hash-based encoding works when VAE unavailable
- [ ] Encoder produces consistent embeddings for identical trajectories (deterministic)
- [ ] API contract tested: input is `list[TrajectoryPoint]`, output is `np.ndarray` of shape `(256,)`
- [ ] All tests pass: `uv run pytest tests/universe/test_vae_journey_encoder.py -q`

**Verify:**

- `uv run pytest tests/universe/test_vae_journey_encoder.py -q`

### Task 4: RL Capability Evaluator

**Objective:** Build a multi-dimensional evaluation framework that measures agent navigation capability in morphospace. For EVO agents, this measures gradient-following quality, stability maintenance, and recovery from perturbation. The framework is designed to be **extensible to LLM agents** in future — dimension names map to higher-order capabilities when the agent substrate changes.

**Dependencies:** Task 1 (needs Scenario definitions for reward functions)

**Files:**

- Create: `src/cohezion/universe/capability_evaluator.py`
- Test: `tests/universe/test_capability_evaluator.py`

**Key Decisions / Notes:**

- `CapabilityEvaluator` scores agent journeys across 6 dimensions:
  1. `task_completion` — Did the agent reach the target region in morphospace?
  2. `coherence_maintenance` — Did HIHO stability remain near 0.5?
  3. `context_retention` — Did the agent's trajectory show awareness of prior steps (path efficiency, not revisiting)?
  4. `ambiguity_handling` — How well did the agent navigate when target wells had noise/uncertainty?
  5. `interruption_recovery` — How quickly did the agent re-orient after forced state perturbation?
  6. `judgment_quality` — When presented with competing wells, did the agent select optimally?
- **Note:** For EVO agents, these dimensions measure morphospace navigation quality. When extended to LLM agents, the same dimensions map to reasoning, memory, and decision-making capabilities. The evaluation API is agent-substrate-agnostic.
- Each dimension scored 0.0-1.0, composite score = weighted average
- `CapabilityProfile` aggregates scores across scenarios for an agent's capability signature
- Reward functions defined per-scenario (from Task 1) are the ground truth
- Anti-gaming: reward shaping penalizes degenerate strategies (constant action, zero exploration)
- Follow the `compute_trajectory_quality()` pattern from `journey_tracker.py:436`

**Definition of Done:**

- [ ] `CapabilityEvaluator.evaluate()` scores a journey across all 6 dimensions
- [ ] `CapabilityProfile` aggregates scores across multiple scenario evaluations
- [ ] Anti-gaming checks detect degenerate strategies (constant action, zero exploration)
- [ ] Evaluation is deterministic for the same trajectory input
- [ ] All tests pass: `uv run pytest tests/universe/test_capability_evaluator.py -q`

**Verify:**

- `uv run pytest tests/universe/test_capability_evaluator.py -q`

### Task 5: Bioelectric Scenario Navigator

**Objective:** Integrate Levin's bioelectric navigation into the scenario execution pipeline. Agents use bioelectric signals to navigate morphospace toward scenario objectives, with the BioelectricEngine providing gradient-based action guidance.

**Dependencies:** Task 1 (Scenario), Task 2 (EVOAgent)

**Files:**

- Create: `src/cohezion/universe/bioelectric_navigator.py`
- Test: `tests/universe/test_bioelectric_navigator.py`

**Key Decisions / Notes:**

- `BioelectricNavigator` wraps the existing `BioelectricEngine` from `flume/bioelectric.py`
- Takes a `Scenario` and `EVOAgent`, produces a sequence of bioelectric-guided steps toward the objective
- **AxiomaticState <-> numpy conversion:** EVOAgent owns the conversion boundary. `EVOAgent.to_numpy()` extracts 12D numpy array for BioelectricEngine, `EVOAgent.update_from_numpy(arr)` applies the result back to AxiomaticState
- The navigator handles the scenario's interruptions by encoding context-switch signals as voltage spikes
- Ambiguity is modeled as noisy target wells (the bioelectric gradient is uncertain)
- Judgment scenarios present multiple competing stability wells — the agent must choose
- Each step generates a `BioelectricSignal` + `ActionVector` that updates the EVO agent's state
- **Degenerate morphospace validation:** Before navigation, validate that stability wells are not collapsed (wells must have pairwise distance > 0.1 in 12D space). If degenerate, regenerate scenario wells with random perturbation
- Follow the `simulate_morphogenesis()` pattern from `bioelectric.py:155`

**Definition of Done:**

- [ ] `BioelectricNavigator.navigate_scenario()` runs an agent through a complete scenario
- [ ] Interruption handling: navigator pauses, injects context switch, resumes
- [ ] Ambiguity: target wells have configurable noise proportional to scenario ambiguity_level
- [ ] Judgment: multiple competing wells presented, agent selects based on bioelectric gradient
- [ ] Navigation produces full trajectory (list of states + signals) for evaluation
- [ ] All tests pass: `uv run pytest tests/universe/test_bioelectric_navigator.py -q`

**Verify:**

- `uv run pytest tests/universe/test_bioelectric_navigator.py -q`

### Task 6: Quadrature Nexus Scenario Dispatch

**Objective:** Wire the QuadratureNexus into the simulation pipeline so it dispatches scenarios across the 4 Quadrature Fabrics (Space, Field, Control, Precipitation), each handling different scenario types suited to their domain.

**Dependencies:** Task 1 (Scenario), Task 2 (EVOAgent)

**Files:**

- Create: `src/cohezion/universe/nexus_dispatch.py`
- Test: `tests/universe/test_nexus_dispatch.py`

**Key Decisions / Notes:**

- `NexusScenarioDispatcher` implements its OWN scenario routing logic — it does NOT delegate to `QuadratureNexus.execute_mission()` which is currently a stub. Instead, it uses QuadratureNexus for topology management (creating fabric swarms, tracking nodes) while implementing the actual dispatch logic itself
- Routes scenarios to fabric-appropriate execution:
  - Space fabric: navigation scenarios (spatial exploration)
  - Field fabric: maintenance scenarios (coherence under perturbation)
  - Control fabric: judgment scenarios (decision-making under competing objectives)
  - Precipitation fabric: interruption scenarios (context recovery, reality manifestation)
- Each fabric's regional swarm can run multiple scenarios in parallel (up to resource limits)
- Uses perception layer to record dispatch events for observability
- Follow the `create_fabric_swarm()` pattern from `executive.py:43` for topology setup

**Definition of Done:**

- [ ] `NexusScenarioDispatcher.dispatch()` routes scenarios to correct fabric based on type
- [ ] All 4 fabrics have corresponding scenario type mappings
- [ ] Dispatch events are recorded via perception layer
- [ ] Multi-scenario parallel dispatch works within resource limits
- [ ] All tests pass: `uv run pytest tests/universe/test_nexus_dispatch.py -q`

**Verify:**

- `uv run pytest tests/universe/test_nexus_dispatch.py -q`

### Task 7: Ouroboros Flight Recorder

**Objective:** Implement the Ouroboros flight recorder for universe simulations — capturing complete scenario execution data for replay, analysis, and self-healing. The recorder is referenced in `__main__.py` but the implementation doesn't exist.

**Dependencies:** None

**Files:**

- Create: `src/cohezion/system/ouroboros_recorder.py` (matches existing import in `__main__.py:590`)
- Create: `src/cohezion/system/__init__.py` (if not exists)
- Test: `tests/universe/test_ouroboros_recorder.py`

**Key Decisions / Notes:**

- **Path choice:** Module lives at `cohezion/system/ouroboros_recorder.py` to satisfy the existing import in `__main__.py:590` (`from cohezion.system.ouroboros_recorder import OuroborosRecorder`). This avoids creating a naming conflict.
- `OuroborosRecorder` captures: scenario definition, agent states at each step, bioelectric signals, evaluation scores, divergence events
- Recordings stored as JSONL (append-friendly, line-delimited JSON) to `data/ouroboros/`
- Replay capability: `OuroborosRecorder.replay(recording_id)` yields events in order
- Self-healing integration: if a scenario execution diverges (DivergenceDetector), recorder logs the divergence point and the last-known-good state for recovery
- File size management: rotate files at 50MB, keep last 10 recordings
- Follow the JSONL persistence pattern from `data/guardian_events.jsonl`
- Non-blocking: all recording operations wrapped in try/except

**Definition of Done:**

- [ ] `OuroborosRecorder.record_event()` appends JSONL events to recording file
- [ ] `OuroborosRecorder.replay()` yields events from a completed recording
- [ ] Divergence events captured with last-known-good state for recovery
- [ ] File rotation at 50MB with configurable retention
- [ ] All tests pass: `uv run pytest tests/universe/test_ouroboros_recorder.py -q`

**Verify:**

- `uv run pytest tests/universe/test_ouroboros_recorder.py -q`

### Task 8: End-to-End Pipeline Integration

**Objective:** Connect all components into one cohesive `UniverseTrainingPipeline` that generates scenarios, dispatches through Nexus, runs agents through bioelectric navigation, encodes journeys via FLUME VAE, evaluates capability, and records everything via Ouroboros.

**Dependencies:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6, Task 7

**Files:**

- Create: `src/cohezion/universe/training_pipeline.py`
- Test: `tests/universe/test_training_pipeline.py`

**Key Decisions / Notes:**

- `UniverseTrainingPipeline` orchestrates the full loop:
  1. `ScenarioGenerator.generate()` → produces scenario batch
  2. `NexusScenarioDispatcher.dispatch()` → routes to fabric
  3. `BioelectricNavigator.navigate_scenario()` → agents execute scenarios
  4. `VAEJourneyEncoder.encode_trajectory()` → encode journey to 256D
  5. `CapabilityEvaluator.evaluate()` → score agent capability
  6. `OuroborosRecorder.record_event()` → capture everything
- Pipeline supports batch execution: run N scenarios across M agents
- Produces `TrainingReport` with aggregate capability profiles
- Experience replay: similar past journeys retrieved from VAE-encoded space
- **Mycelium interface:** Define a minimal `MyceliumSignal` dataclass and `emit_mycelium_signal()` function that logs pipeline completion events (scenario count, agent performance deltas, capability regressions). This is a signal emitter interface only — the actual ShadowScripter consumer can be implemented in a follow-up. No dependency on non-existent Mycelium code.
- Pipeline is async, non-blocking for observability operations
- Configuration via `TrainingConfig` dataclass (scenario count, difficulty range, agent count, **max_concurrent_scenarios**)
- **Concurrency control:** Process scenarios in batches of `max_concurrent_scenarios` (default: 4) to prevent memory spikes from holding all trajectory/embedding data simultaneously

**Definition of Done:**

- [ ] `UniverseTrainingPipeline.run()` executes complete generate→dispatch→navigate→encode→evaluate→record loop
- [ ] `TrainingReport` contains per-agent CapabilityProfiles and aggregate statistics
- [ ] Experience replay retrieves similar past journeys using VAE embeddings
- [ ] Mycelium signal emitted after pipeline completion (logs scenario count and capability deltas)
- [ ] Pipeline handles errors gracefully (individual scenario failures don't crash batch)
- [ ] All tests pass: `uv run pytest tests/universe/test_training_pipeline.py -q`

**Verify:**

- `uv run pytest tests/universe/test_training_pipeline.py -q`
- `uv run pytest tests/universe/ -q` — all universe tests pass

## Testing Strategy

- **Unit tests:** Each component tested in isolation with mock dependencies (mock bioelectric engine, mock VAE encoder, mock sandbox)
- **Integration tests:** Task 8 pipeline test verifies end-to-end flow with all real components (except external services)
- **HIHO invariant:** All simulation tests assert coherence tends toward 0.5
- **Determinism:** Tests use seed=42 for reproducibility
- **Mocking:** Mock `cohezion_core.cohezion_core_rs.FlumePhysics` (Rust), Docker, external APIs

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| FLUME VAE checkpoint not available at runtime | High | Med | Fallback to hash-based encoding (existing pattern in `vae_encoder.py:69`) |
| Rust `cohezion_core` not available in test/CI | Med | Med | All new code provides pure-Python fallbacks; tests mock Rust imports |
| Bioelectric navigation diverges (NaN/Inf) | Low | High | Use DivergenceDetector from `universe/divergence.py` at each step; clamp values |
| Scenario generation produces degenerate cases | Med | Low | Validate scenarios against minimum complexity thresholds before dispatch |
| Pipeline memory usage with large batch sizes | Low | Med | Use SandboxManager memory budget pattern; process scenarios in configurable batch windows (max_concurrent_scenarios=4) |
| Degenerate morphospace (all wells collapsed) | Low | Med | BioelectricNavigator validates well pairwise distance > 0.1 before navigation; regenerates with perturbation if degenerate |

## Open Questions

- None at this time — all critical design decisions resolved. See Deferred Ideas for future work.

### Deferred Ideas

- Actual RL training loop using evaluation scores as rewards (out of scope — we build the environment)
- Multi-model evaluation (running same scenarios against different LLMs)
- Real-time visualization dashboard for training pipeline
- New PRIME skill definitions for scenario types
- SurrealDB schema additions for evaluation scores persistence
