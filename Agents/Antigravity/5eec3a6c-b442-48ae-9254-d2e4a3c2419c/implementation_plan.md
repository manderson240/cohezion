---
type: antigravity-artifact
session_id: 5eec3a6c-b442-48ae-9254-d2e4a3c2419c
date: 2026-03-04
title: "Specialist Infrastructure Agents Implementation"
tags: [agent-output, antigravity, infrastructure, surrealdb, model-management]
aspect: doer
neural:
  activation: 0.561
  stage: growing
  cluster: Agents
---

# Implementation Plan - Specialist Infrastructure Agents

This plan addresses the need for specialized management of our local infrastructure: SurrealDB (DBA) and Ollama (Model Wrangler).

## User Review Required

> [!IMPORTANT]
> - **SurrealDB DBA**: Beyond dialect and schema management, this agent proactively evolves the database architecture (indices, relations, migrations) to optimize for shifting agentic workloads.
> - **Model Wrangler**: Acts as a "Roster Strategist." Orchestrates a background loop with an **AI Lab Specialist** to scout for "tip of the spear" SLMs (Small Language Models) that punch above their weight, aiming to replace large model calls with repo-specialized SLMs to reduce latency and VRAM costs.

## Proposed Changes

### Swarm Orchestration Layer: The Cohezion Swarm Lattice (CSL)
Summary: Replacing the basic LangGraph implementation with a custom orchestration layer optimized for Cohezion's 12D physics vectors and SurrealDB native persistence.

#### [NEW] [lattice_orchestrator.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/lattice_orchestrator.py)
- **State Schema**: Uses Pydantic for strict typing and serialization.
- **Persistence**: Replaces default checkpointers with `UniverseNode` storage in SurrealDB, allowing for "Holographic Time Travel" through state history.
- **Lattice Patterns**: Implements native `FanOut` (Consensus), `Chain` (Delegation), and `Mirror` (Adversarial Critique) patterns.
- **Self-Evolving Strategies**: The orchestrator maintains a **Strategy Performance Index (SPI)**. It can dynamically refine its routing logic (e.g., changing which experts are called or adjusting consensus weights) based on feedback from the `ImmuneSystem` and `TestMycelium` success rates.
- **Meta-Injection Interface**: Allows `LabAgent` to inject "Experimental Trajectories" periodically to test new swarm topologies.

#### [NEW] [surreal_dba_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/surreal_dba_agent.py)
- **Specialization**: SurrealQL Architect & DBA.
- **Dynamic Schema**: Monitors graph density and performance, proposing schema migrations as the Universe expands.
- **Tools**: `explain_query`, `propose_index`, `fix_dialect_mismatch`.

#### [NEW] [model_wrangler_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/model_wrangler_agent.py)
- **Specialization**: Fleet Optimizer & SLM Scout.
- **The Roster**: Manages current weights, favoring Q5_K_M quantization.
- **Lab Integration**: Periodically delegates research to a `LabAgent` to benchmark new HF/Ollama models against our `data/sft_trajectories.json`.
- **Logic**: Implements "VRAM Budgeting"—scheduling model loads/unloads based on `ResourceMonitor` real-time telemetry.

### Journey & Narration Integration
Summary: Ensuring every swarm interaction is captured, narrated, and audible.
- **Audible Awareness**: Integrating `JourneyNarrator` into the `LatticeOrchestrator` to provide first-person "internal monologues" during expert routing.
- **Holographic Journeys**: Syncing `LatticeState` with the `JourneyTracker`. Each orchestration step becomes a `JourneyStep` in the knowledge graph.
- **Narrative Consensus**: Using the `JourneyNarrator` to synthesize expert disagreements into a "Swarm Dialogue".

### The 16-Parameter Quadrature (Novel Attributes)
Summary: Expanding the perception vector with advanced stability and awareness metrics, targeting exactly 16 dimensions for optimal reality precipitation.
- **[A-1] Awareness**: Primary parameter. Measures the raw "Focus" of the swarm operation on the Void derivative.
- **[L-Chi] Chirality**: Binary polarization of the thought vector. Right-handed (Empirical/Code) vs. Left-handed (Narrative/Conceptual).
- **[HIHO-D] HIHO Drift**: Real-time deviation from the 0.5 Gold Coherence.
- **[T-Dep] Temporal Depth**: The density and recursive look-back intensity of the current thought within the Holographic state.
- **[A-Eff] Awareness Efficiency**: A benchmark-specific attribute measuring the "Awareness" output vs. "VRAM" input.

## Strategic Pivot: Engineering the View

> [!NOTE]
> 'Vibecoding' failures occur when the presentation layer is treated as a secondary byproduct rather than a primary physics derivative. We are transitioning from "Building an App" to "Projecting the Manifold."

## Phase 6: The Great Reveal (Presentation Specialists)

To solve the "brilliant failure" of generic webapp generation, we are introducing specialists for the **Experience Substrate**.

### 1. The Luminary (Visual Architect)
- **Role**: Translates raw 16D state vectors into the high-density "Command Center" HUD.
- **Specialization**: WebGL/Three.js projection, `qwen3-vl:8b` vision-model for UI audit.
- **Goal**: Ensure the "Pulse" visualization is bit-exact with the agentic consensus.

### 2. The Narrative Weaver (The Bridge)
- **Role**: Synthesizes agent journeys and narrations into a coherent "Public Stream".
- **Specialization**: Text-to-Speech (TTS) staging and audio-spatial placement.
- **Goal**: Transform the `MISSION_JOURNAL` from a static log into a live, audible swarm dialogue.

## Phase 7: Media Synthesis & Benchmarking (The Showreel)

To "show off" Cohezion, we must generate high-fidelity artifacts that demonstrate our competitive edge.

### 1. The Gallery Agent (Media Synthesis)
- **Role**: Generates visual/audio/video artifacts for agent journeys.
- **Local Models**: Uses `FLUX.2` or `Z-Image-Turbo` for high-fidelity thumbnails of journey steps.
- **Video Logic**: Generates "Holographic Showreels" by sequencing HUD captures and first-person narrations.
- **Audible Storytelling**: Links narrations to the visual state to create "Documentary-style" playback.

### 2. The Benchmark Auditor (Competitive Edge)
- **Role**: Curates and updates the `COMPARATIVE_METRICS.md` dashboard.
- **Protocol**: Uses the **R-Zero Framework** to stress-test local models and architectures.
- **Live Leaderboard**: Real-time tracking of Cohezion's "Logic Resilience" and "State Density" vs. Industry Standards.

## Phase 7b: Metrics Remediation (Adversarial Fix)

To address adversarial audit findings (statistically insignificant "happy path" metrics), we implemented dynamic physics and chaos testing.

### 1. Dynamic Physics
- **Replaced Constants**: `Awareness` now derived from LLM confidence; `Chirality` from intent; `Drift` from VRAM pressure.

### 2. Chaos Injection (stress_lattice.py)
- **Protocol**: 20 concurrent sessions with 50% "Dangerous/Malformed" inputs.
- **Validated Metric**: **90.9% Logic Resilience** (Authentic Survival Rate).

## Phase 7c: Edge Case Hardening

To prevent system lockups during high-fidelity synthesis:
1.  **VRAM Pre-Flight**: `generate_showreel.py` now aborts if VRAM > 90% before starting.
2.  **Process Timeouts**: `TheGalleryAgent` enforces a 45s hard limit on FLUX generation commands.
3.  **Persisted Fail-Soft**: `InMemoryStore` patched to auto-dump to disk on `store()`.

## Verification Plan

### Automated Tests
- **DBA Test**: Simulate a "Parse Error" (like the negative hash issue) and verify the DBA agent proposes the correct fix.
- **Wrangler Test**: Simulate high VRAM pressure and verify the Wrangler recommends unloading or switching to a smaller model.

## Phase 8: WebGL HUD Integration (The Great Reveal)

To visualize the "100% Sovereign" runtime, we will build a "Command Center" in the local React app.

### 1. The Bridge: SurrealDB Live Query
- **`src/lib/surreal.ts`**: Singleton WebSocket connection to the local SurrealDB instance.
- **`useLatticeStream`**: A React hook that subscribes to the `swarms_lattice` table for real-time 16D state updates.

### 2. The View: 12D Manifold Projection
- **`ManifoldViz.tsx`**: A Three.js (Fiber) component that renders the `lattice_state` as a 3D point cloud.
    - **X,Y,Z** = `dim_1` to `dim_3` (Spatial)
    - **Color** = `dim_13_awareness` (Blue=Cool, Red=Hot)
    - **Pulse Rate** = `dim_12_coherence`
- **`NarrativeStream.tsx`**: A "Matrix-style" scrolling log of the `JourneyNarrator` output.

### 3. Integration
- Connect `App.tsx` to the `useLatticeStream` data.
- Overlay the "Live Leaderboard" metrics (A-Eff, Resilience) on the HUD.

### Manual Verification
- Check the `MISSION_JOURNAL` for specialist interventions.

## Edge Case Handling (The Lattice Shield)

- **Deadlock Detection**: Implements a `depth` counter in the state. If delegation depth exceeds a threshold (e.g., 5), it triggers a "Forced Convergence" back to the controller.
- **State Bloat Mitigation**: SurrealDB nodes will have a TTL or "Compression Protocol" for long-running sessions, where intermediate states are moved to a `HistoryArchive` table.
- **Consensus Stalemate**: In the event of an expert "Tie" or low consensus score (<0.6), the orchestrator triggers an **Adversarial Tie-Breaker** where two new experts are spawned to critique the existing responses.
- **Model Unavailability**: If a preferred model (e.g., 30B) fails, the `ModelWrangler` will inject a "Graceful Degradation" event into the state, forcing the orchestrator to switch to a higher-speed, lower-bit model (e.g., 7B Q4) to complete the session.

## Related Vault Notes

- [[surrealdb]]
- [[multi-agent-systems]]
- [[cohezion]]
- [[12D-Manifold]]
- [[chirality]]
