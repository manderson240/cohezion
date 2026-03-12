---
type: antigravity-artifact
session_id: 7bba44ce-6ae2-4ddd-af67-824f717d45eb
date: 2026-03-04
title: "Implementation Plan Phase11"
aspect: doer
neural:
  activation: 0.335
  stage: embryo
  cluster: Agents
---

# Implementation Plan - Phase 11: Universe-Class UX Overhaul

## Goal
Transform the WebApp from a "clean website" into a **"Next-Gen Universe Simulation"**. 
Crucial User Feedback: "Too sparse", "Must feel like problem solving from disparate threads".

## Paradox to Solve
**Shadcn Cleanliness (Structure)** vs. **Universe Density (Chaos/Life)**.
Solution: **"The Cosmic Loom"**. A dense, HUD-like interface where every pixel reports status, yet structured by the "Lattice".

## Proposed Changes

### 1. The Layout: "Command Center" (High Density)
Replace the centered "Landing Page" container with a full-viewport **Holographic HUD**.
- **Perimeter**: Global Status Bar (Top), Mission Ticker (Bottom).
- **Grid**: A 12-column grid overlay.
- **Background**: `mcp-universe` Lattice visualization (Live).

### 2. Disparate Threads Visualization
Visualizing the "Solver" process.
- **Left Panel**: "Entropy Stream" (Problem Inputs / Chaos).
- **Right Panel**: "Negentropy Stream" (Solver Outputs / Order).
- **Center**: The "Crucible" (The Seed Crystal / Synthesis).
- **Connection**: Animated "Thread Lines" (SVG/Canvas) drawing connections between Left, Right, and Center.

### 3. Component Density
Existing Cards (`Pulse`, `Mission Ledger`) are too big/empty.
- **Factorize**: Break cards into smaller "Modules".
- **Telemetry**: Add Sparklines, CPU usage, Coherence score to *every* module.
- **Text**: Use condensed mono fonts (`JetBrains Mono` or similar) for high information density.

### 4. Code Structure
#### [NEW] `src/components/CommandCenter.tsx`
The new parent component.
#### [MODIFY] `src/components/LandingPage.tsx`
Refactor to use `CommandCenter` layout instead of simple flex column.
#### [NEW] `src/components/ui/ThreadRail.tsx`
A component that draws animated connection lines between other components.

## Verification Plan
1. **Visual Density Check**: Does the screen look "full" without looking "cluttered"?
2. **Theme Check**: Does it use `#00FF00` (Nexus Green) and `#0A0A0A` (Void) exclusively?
3.  **Connection Check**: Do "threads" visually connect the disparate parts?

## Related Vault Notes

- [[universe-simulation]]
