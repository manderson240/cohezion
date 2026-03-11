---
type: antigravity-artifact
session_id: 1fbfc912-70e8-458b-a3e3-cc4ace0e8395
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.346
  stage: embryo
  cluster: Agents
---

# Walkthrough: Project Ouroboros - The Autonomic Nervous System

I have successfully implemented **Project Ouroboros**, a "Long Horizon" task that gives Cohezion a self-regulating stability loop.

## 1. The Sensorium (`src/cohezion/system/ouroboros.py`)
I implemented the Input Layer which aggregates:
- **Hardware Vitals**: CPU, RAM, VRAM (via `ResourceMonitor`).
- **Software Vitals**: HIHO Coherence (0.5 Target), Stability Score.
- **State Vector**: A 12-Dimensional representation of system health.

## 2. The Logic (`src/cohezion/system/ganglion.py`)
I implemented the Decision Layer ("The Ganglion") which triggers autonomic reflexes:

| State | Condition | Reaction | Function |
|-------|-----------|----------|----------|
| **Panic** | CPU/RAM > 95% | `panic_prune` | Kills processes to prevent lockup |
| **Chaos** | Stability < 0.3 | `stabilize` | Triggers `TestMycelium` to fix code |
| **Stasis** | Stability > 0.8 | `dream` | Triggers `ShadowScripter` to invent code |
| **Flow** | Stability ~ 0.5 | `synthesize` | Consolidates knowledge (Optional) |

## 3. The Pulse (Live WebSocket Stream)
I connected the 3D Interface to the living system via `websockets`:
- **Backend**: `start_ouroboros.py` broadcasts State Vector on `ws://localhost:8765`.
- **Frontend**: `useOuroboros.ts` consumes the stream, dynamically updating the 3D Hologram.
- **Visuals**: The Singularity Pulse and Swarm Color now reflect *real-time* system coherence and stability.

## 4. Real Sensors (`src/cohezion/system/sensors/git_health.py`)
I implemented real-time `GitHealthSensor` to replace mocked metrics:
- **Entropy**: Derived from `git status` (dirty state).
- **Momentum**: Derived from `git log` (commit velocity).
- **Novelty**: Derived from line insertions.

## 5. Ecosystem Enhancements
### TestMycelium
- Added `dry_run` and batching for safe autonomous operation.
- Verified with `tests/automated/test_mycelium_dryrun.py`.

### Knowledge Extraction
- Created `export_trajectories.py` to harvest verified Bug->Fix pairs.
- Seeded mock data to verify the pipeline.
- Exported `data/training/cohezion_instruct.jsonl` for local fine-tuning.

## Verification
- **Simulation**: `test_ouroboros_loop.py` verified logic limits.
- **Daemon**: `start_ouroboros.py` verified end-to-end sensing and actuation.
- **Data**: Mock seed and export verified via `export_trajectories.py`.

## Final Status
Project Ouroboros is **LIVE**.
- Run `uv run scripts/drivers/start_ouroboros.py` to start the heartbeat.
- Fine-tune local models using the generated `.jsonl` dataset.
