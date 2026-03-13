---
type: antigravity-artifact
session_id: a9827b64-da91-4896-9abf-2c13e3cd453c
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.61
  stage: embryo
  synapse_in: 0
  synapse_out: 1
---

# Implement Memory Guardrails in Peaked Circuit Solver

## Problem Description
The IDE was closed due to an OOM (Out of Memory) kill event triggered by `python3`. Investigation points to `peaked_solver.py` which attempts an exact `to_mps()` conversion on a large quantum circuit, potentially exhausting all available RAM (128GB).

## User Review Required
> [!WARNING]
> I am changing the default behavior of `simulate_and_sample` to use `max_bond=64` for the initial MPS attempt instead of `max_bond=None` (exact). This trades exactness for stability. If exactness is required, the fallback to full tensor contraction (which is sliced and memory-safe) will still occur if the MPS approximation is deemed insufficient or if we skip MPS.

## Proposed Changes

### Physics
#### [MODIFY] [peaked_solver.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/physics/quantum/peaked_solver.py)
- Import `psutil` and `gc`.
- In `simulate_and_sample`:
    - Add a check for available memory.
    - Wrap `to_mps` in a `try/except` block catching `MemoryError`.
    - Change `self.circ.to_mps()` to `self.circ.to_mps(max_bond=64)` to prevents explosion.
    - Add explicit `gc.collect()` after large operations.

## Verification Plan

### Automated Tests
- Run the solver script directly:
    ```bash
    python3 src/cohezion/physics/quantum/peaked_solver.py
    ```
- Verify it completes or handles the circuit without crashing the system.
- Check logs to see if "Exact MPS conversion failed/too large" warning appears (expected if we limit bond).

### Manual Verification
- User can re-open the IDE and continue work without fear of random crashes.

## Related Vault Notes

- [[cohezion]]
