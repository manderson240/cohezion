---
type: antigravity-artifact
session_id: df1f3270-6223-43df-aec9-cff48f146303
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.62
  stage: embryo
  synapse_in: 0
  synapse_out: 2
---

# Implementation Plan: Enhanced Resource Stewardship

This phase focuses on integrating real-time hardware telemetry into the CommandCenter UI and implementing a "Desperation Mode" to protect critical system resources during heavy agentic loops.

## User Review Required

> [!IMPORTANT]
> **Throttling Mechanism**: "Desperation Mode" will use `psutil` to `SIGSTOP` or `renice` non-essential processes (git, npm, background simulations) when CPU/RAM exceeds 90%.

## Proposed Changes

### Core Reliability (Backend)

#### [MODIFY] [monitor.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/monitor.py)
- Integrate `SurrealClient` to persist `vitals` as `hardware_vitals` nodes in SurrealDB.
- Implement `_desperation_throttle()` within the heartbeat loop.
- Define "non-essential" process patterns (git, npm, non-priority simulations).

### Web Application (Frontend)

#### [NEW] [useHardwareVitals.ts](file:///home/mike-anderson/dev/cohezion/apps/webapp/src/hooks/useHardwareVitals.ts)
- New hook using SurrealDB `live` query on the `hardware_vitals` table.

#### [MODIFY] [CommandCenter.tsx](file:///home/mike-anderson/dev/cohezion/apps/webapp/src/hooks/CommandCenter.tsx) (Wait, path check needed)
- Integrate `useHardwareVitals` hook.
- Map `cpu`, `ram`, `vram`, and `llm_calls` to the UI display.

## Verification Plan

### Automated Tests
- `pytest tests/automated/test_priority_eviction.py` (Verify existing logic).
- `scripts/drivers/stress_test_throttle.py` [NEW]: Simulate high load and verify non-essential processes are throttled.

### Manual Verification
- Open CommandCenter UI and verify live vitals update every 10s.

## Related Vault Notes

- [[cohezion]]
- [[surrealdb]]
