---
type: antigravity-artifact
session_id: 1fbfc912-70e8-458b-a3e3-cc4ace0e8395
date: 2026-03-04
title: "Implementation Plan Sensors"
aspect: doer
neural:
  activation: 0.300
  stage: embryo
  cluster: Agents
---

# Implementation Plan: Git Metrics Sensor

## Goal
Replace mocked "Hidden Dimensions" in `OuroborosSense` with real telemetry from the Git repository.

## Proposed Changes

### 1. New Sensor Module
- **File**: `src/cohezion/system/sensors/git_health.py`
- **Class**: `GitHealthSensor`
- **Metrics**:
    - `entropy`: Calculated from number of modified/untracked files. (0.0 = clean, 1.0 = mess)
    - `momentum`: Calculated from commits in the last 24 hours.
    - `novelty`: Lines of code added in last 24h.

### 2. Integration
- Update `OuroborosSense` in `src/cohezion/system/ouroboros.py`.
- Instantiate `GitHealthSensor`.
- Await `sensor.read()`.

## Verification
- Run `start_ouroboros.py` locally and verify logs show dynamic values for entropy/momentum.
