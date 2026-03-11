---
type: antigravity-artifact
session_id: d9c1fcdb-69db-458c-b64a-f26e49625c33
date: 2026-03-04
title: "Overnight Protocol"
aspect: doer
neural:
  activation: 0.312
  stage: embryo
  cluster: Agents
---

# OVERNIGHT PROTOCOL: LOW AND SLOW BBQ

**Mission**: Execute 50,000,000 simulation rounds to stabilize the Fractal Nexus at 0.5 Coherence (HIHO) without compromising Framework Desktop hardware integrity.

## Execution Strategy
- **Driver**: `scripts/drivers/autonomous_bbq.py`
- **Pacing**: "Low and Slow". Simulation loop is strictly coupled to `ResourceMonitor` vitals.
- **Heartbeat**: 2 seconds.
- **Dilation**: Dynamic sleep injection based on system load.
    - < 60% Load: 1.0x Speed
    - > 85% Load: 0.05x Speed (Throttled)
    - > 90% Load: Emergency Stop

## Innovation Engines
1.  **Biological Diversity**: Active substrate rotation (Carbon -> Silicon -> Phosphorus -> Plasma) based on coherence waves.
2.  **Persistence**: Checkpoints saved to SurrealDB every 1,000 rounds.
3.  **Visualization**: Live telemetry available in `morphospace-loom` via the Ouroboros bridge (if active).

## Output
- **Logs**: `autonomous_bbq.log`
- **Data**: `surrealdb/agent_journeys` table
- **Artifacts**: New skills crystallized from success patterns (handled by `omega_watcher` if active).

> [!TIP]
> **Check Status**: `tail -f autonomous_bbq.log` to watch the cook.

**Status**: READY TO LAUNCH.
