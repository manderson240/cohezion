# Morphospace Loom - User Guide

> **COHEZION = 0.5 HIHO** — The Half-In-Half-Out stability threshold drives everything.

## Quick Start

1. Open http://localhost:3001 in your browser
2. Click **Start** to begin the 25M cycle simulation
3. Watch the manifold evolve in real-time

## Controls

| Button | Action |
|--------|--------|
| **Start** | Begin/Resume simulation |
| **Pause** | Pause simulation |
| **Reset** | Reset to initial state |

## Navigation

- **Left-click + drag**: Rotate view
- **Right-click + drag**: Pan view
- **Scroll**: Zoom in/out

## Understanding the Display

### 3D Visualization
- **Green spheres**: Stability wells (high HIHO coherence)
- **Trajectory line**: Path through the 12D manifold (projected to 3D)
- **Octahedron**: Current state indicator
  - Green: Homeostatic (stable)
  - Blue: Morphogenic (transitioning)
  - Orange: Regenerative (restructuring)

### Stats HUD (Top Right)
- **Cycles**: Current / Total simulation cycles
- **Progress**: Percentage complete
- **Avg Stability**: Mean HIHO stability across all cycles
- **Wells Discovered**: Auto-detected stability regions

### Timeline (Bottom)
- Scrub through the trajectory
- View stability at any point
- See bioelectric pattern classification

## What to Look For

1. **Stability Convergence**: Watch the trajectory converge towards HIHO Origin (0.5, 0.5, 0.5)
2. **New Wells**: The simulation discovers new stability wells automatically (low probability)
3. **Pattern Transitions**: Observe morphogenic → regenerative → homeostatic transitions
4. **Stability Oscillation**: Notice how stability fluctuates before settling

## Technical Details

- **Simulation**: Runs in browser using requestAnimationFrame
- **Batch Size**: 10,000 cycles per frame (maintains 60fps)
- **Memory**: Last 5,000 trajectory points kept (older pruned)
- **Well Detection**: Any state with stability > 0.85 may spawn a well

## The COHEZION Principle

The simulation demonstrates the core COHEZION principle:
- All states are attracted towards HIHO = 0.5 coherence
- This is the natural stability point of the manifold
- Higher stability = closer to this attractor

Enjoy exploring the morphospace! 🌌
