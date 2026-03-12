---
type: antigravity-artifact
session_id: 0c888e0d-6061-443c-a927-3d908cbf0d85
date: 2026-03-04
title: "Implementation Plan Desperation"
aspect: doer
neural:
  activation: 0.318
  stage: embryo
  cluster: Agents
---

# Desperation Mode: Non-Privileged System Damping

This phase implements a granular "Brake System" for Cohezion, preventing hard lockups by damping down non-essential computational activity when the system enters extreme pressure (90-95% load).

## User Review Required

> [!WARNING]
> Desperation Mode will pause background simulations (e.g., `fractal_universe.py`) without user intervention if CPU/RAM exceeds 93%. These will be automatically resumed once pressure drops.

## Proposed Changes

### [Reliability Layer]

#### [MODIFY] [monitor.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/monitor.py)
- Implement `_identify_secondary_processes()`: A method to find PIDs of non-priority agents and simulations.
- Implement `enter_desperation_mode()`:
    - Tier 1 (90%): Set `nice(19)` for secondary processes.
    - Tier 2 (93%): Send `SIGSTOP` to secondary processes.
- Implement `exit_desperation_mode()`:
    - Restore original `nice` values and send `SIGCONT`.
- Integrate into `_heartbeat_loop`.

### [Autonomic Layer]

#### [MODIFY] [ganglion.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/system/ganglion.py)
- Add "Damping" state to the `reflex` logic.
- Ensure `trigger_stabilizer` respects the damping state (e.g., fewer concurrent tests).

## Verification Plan

### Automated Tests
- `tests/automated/test_desperation_mode.py`: A stress test that simulates high CPU load and verifies that background processes are paused and resumed correctly.

### Manual Verification
- Monitor the HUD's "QUADRATURE DYNAMICS" section; "FRICTION" should spike when Desperation Mode is active.

## Related Vault Notes

- [[cohezion]]
