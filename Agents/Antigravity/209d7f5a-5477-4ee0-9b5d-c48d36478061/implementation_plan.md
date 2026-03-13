---
type: antigravity-artifact
session_id: 209d7f5a-5477-4ee0-9b5d-c48d36478061
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.61
  stage: embryo
  synapse_in: 0
  synapse_out: 1
---

# Implementation Plan - Ouroboros HUD Integration

The goal is to visualize the "Autonomic Layer" (Ouroboros) within the Cohezion Portal. This allows the user to see the system's "heartbeat" (Stability, Entropy, Coherence) alongside the Lattice data.

## User Review Required

> [!IMPORTANT]
> This integration introduces a new WebSocket connection to `ws://localhost:8765`. Ensure the Ouroboros driver is running (`scripts/drivers/start_ouroboros.py`).

## Proposed Changes

### Frontend (Webapp)

#### [MODIFY] [LatticeHUD.tsx](file:///home/mike-anderson/dev/cohezion/apps/webapp/src/components/LatticeHUD.tsx)
-   Import `useOuroboros` hook.
-   Add a new visual layer (e.g., a "Pulse Monitor" or "System Vitals" panel) to the HUD.
-   Display key metrics: Stability (Health Bar), Coherence (Color), and Entropy (Jitter).

#### [NEW] [AutonomicDisplay.tsx](file:///home/mike-anderson/dev/cohezion/apps/webapp/src/components/AutonomicDisplay.tsx)
-   Create a dedicated component for the Ouroboros metrics to keep `LatticeHUD` clean.
-   Design: "Minority Report" style transparent panel.
-   Metrics:
    -   **Stability**: 0-1 (Green to Red)
    -   **Drift**: Value readout
    -   **System Load**: CPU/RAM/VRAM bars

## Verification Plan

### Automated Tests
-   Verify WebSocket connection in browser console logs.
-   Check simple React render tests (if available).

### Manual Verification
-   **Step 1**: Start `start_ouroboros.py`.
-   **Step 2**: Open Webapp (`npm run dev`).
-   **Step 3**: Verify "System Vitals" panel appears.
-   **Step 4**: Observe values updating every ~10s (matching driver loop).
-   **Step 5**: Intentionally stress system (if possible) or wait for driver to report load to see cues change.

## Related Vault Notes

- [[cohezion]]
