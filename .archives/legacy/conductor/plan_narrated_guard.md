# Implementation Plan: The Narrated Guard (Coherence 2.0)

## Background & Motivation
The Cohezion platform currently possesses an Autonomic Nervous System (`Ouroboros` and `SelfHealingSystem`) that proactively monitors and reactively heals the swarm. However, this system lacks an observable sensory output. To achieve "Coherence 2.0," we must bridge the objective manifold physics of anomaly detection with the subjective, human-perceivable "Voice" of the substrate. This plan implements "The Narrated Guard," giving the system the ability to vocally announce trajectory drift and autonomic corrections.

## Scope & Impact
1.  **Voiced Trajectory Alerts**: Connect the `AnomalyDetector` in `trajectory_guard.py` to the `CosmoNarrator`. When an active journey drifts from the HIHO 0.5 attractor, the system will audibly alert the operator and narrate the synthesis of the corrective patch.
2.  **System Health Narration**: Extend the `SelfHealingSystem` to vocally announce daemon heartbeat failures or extreme resource throttling (Desperation Mode).

## Specialist Team Execution Strategy (Strict V-Model Enforcement)

Since we are bypassing generic agents, I (the Primary Orchestrator) will act as the specialist implementer directly, utilizing `codebase_investigator` for surgical reconnaissance before executing changes.

### Phase 1: Audio Architects (System Architecture)
**Tasks**:
- Analyze `src/cohezion/audio/narrator.py` to understand the `CosmoNarrator` interface and the `narrate_custom()` asynchronous method.
- Determine the optimal, non-blocking way to integrate audio generation into the `trajectory_guard.py` and `immune_system.py` event loops without introducing latency.

### Phase 2: Physics Engineers (Detailed Design & Implementation)
**Tasks**:
- Modify `src/cohezion/healing/scripts/trajectory_guard.py`.
- Import `get_narrator` from `cohezion.audio.narrator`.
- In the `guard_trajectories()` loop, when `analysis["is_degraded"]` is true, trigger `await narrator.narrate_custom(...)` to announce the specific `journey_id` and the coherence drop.
- After the `HealerAgent` synthesizes a patch, trigger a second narration announcing the successful generation of the corrective prompt.

### Phase 3: Integrity Guards (System Validation)
**Tasks**:
- Modify `src/cohezion/healing/immune_system.py` (specifically `ActuatorSystem` and `SelfHealingSystem`).
- Add voiced alerts for critical events: e.g., when a daemon heartbeat fails, or when the system enters "Desperation Mode" due to high VRAM pressure.

## Verification & Testing
- **Phase 1**: Verify `CosmoNarrator` can be imported and executed in a background script without blocking the main event loop.
- **Phase 2**: Run `make health-guard` (which starts `trajectory_guard.py`) and artificially trigger an anomaly to verify the text-to-speech generation.
- **Phase 3**: Ensure that the `make ci` target continues to pass, validating that no new synchronous I/O violations were introduced by the audio integration.
