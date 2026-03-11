---
type: antigravity-artifact
session_id: b406730c-24e7-4345-98db-baa1edb391cc
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.322
  stage: embryo
  cluster: Agents
---

# Implementing Tsunami Simulator Safety Guards

The recurrent system crashes are caused by the `tsunami_simulator.py` script outrunning the system's capabilities. Specifically, the synchronous `while self.current_epoch < self.total_epochs:` loop aggressively schedules Rust FFI calls without yielding to the async event loop or checking system pressure. Additionally, memory references passed over the edge are not explicitly garbage-collected.

## Proposed Changes

### `cohezion-review/scripts/drivers/tsunami_simulator.py`

#### 1. Integrate `ResourceGuard`

We will inject `ResourceGuard().wait_for_stability()` into the inner loop batch execution to ensure the simulation only proceeds when CPU load < 24.0 and RAM > 16GB free.

#### 2. Event Loop Yielding

Because `self.physics.simulate_epochs_batch` is fundamentally CPU-bound, we must explicitly `await asyncio.sleep(0.05)` after every batch to prevent starvation of the system heartbeat and orchestration layers.

#### 3. Explicit Memory Management

In `_ratchet_and_audit`, we must explicitly `del reps, entropies` and occasionally call `gc.collect()` to force Python to reclaim any FFI numpy boundaries.

#### [MODIFY] [tsunami_simulator.py](file:///home/mike-anderson/dev/cohezion/cohezion-review/scripts/drivers/tsunami_simulator.py)

## Verification Plan

### Automated Checks

- The file must safely execute without locking up the system or driving CPU to 95.0% sustained flat load.
- We will do a syntax check via Ruff before completing.

### Manual Verification

- Execute `uv run scripts/drivers/tsunami_simulator.py` for a few epochs to verify that `ResourceGuard` correctly intercepts pressure and `gc.collect()` suppresses the memory ballooning.
