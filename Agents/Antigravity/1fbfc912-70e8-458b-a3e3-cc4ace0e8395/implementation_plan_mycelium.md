---
type: antigravity-artifact
session_id: 1fbfc912-70e8-458b-a3e3-cc4ace0e8395
date: 2026-03-04
title: "Implementation Plan Mycelium"
aspect: doer
neural:
  activation: 0.309
  stage: embryo
  cluster: Agents
---

# Enhancement Plan: TestMycelium Robustness

## Goal
Ensure `TestMycelium` can run autonomously for hours without crashing due to DB glitches or ID format mismatches. This is critical for the Ouroboros `STABILIZE` phase.

## Proposed Changes

### 1. Robust ID Handling
- The current code does `fix_id = fix_node_data["id"].replace("universe_nodes:", "")`. This is fragile.
- We should use a helper method to parse SurrealDB record IDs safely.

### 2. Dry Run Mode
- Add `dry_run: bool` flag to `run_cycle`.
- If true, log actions but do not write to disk or DB.
- Allows Ouroboros to "Check" for stability without committing changes if needed.

### 3. Batched Processing
- Instead of processing all fresh trajectories at once, process in batches of 5 to avoid holding the `Ganglion` loop for too long.

## Verification
- Run `test_mycelium.py` with mock DB data to verify batching and dry-run logic.
