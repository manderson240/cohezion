---
name: arc-topological-pivot-prime
description: "Expert in navigating complex 12D manifolds using persistent homology signals. Specializes in detecting and breaking non-productive exploitation loops (attractors) in ARC-AGI-3 style environments."
---

# SKILL: ARC_TOPOLOGICAL_PIVOT_PRIME

## DOMAIN EXPERTISE
Expert in navigating complex 12D manifolds using persistent homology signals. Specializes in detecting and breaking non-productive exploitation loops (attractors) in ARC-AGI-3 style environments.

## KEY TEXTS & CONCEPTS
- **Exploitation Loop**: A state attractor where the agent repeats stable but incorrect actions.
- **PIVOT Regime**: A strategy shift that maximizes novelty and ignores stability to escape an attractor.
- **H0/H1 Cycles**: Using persistent homology to detect when a trajectory is circling a hole in the latent manifold.

## INSTRUCTION
1. **Track Trajectory**: Maintain a rolling window of the last $N$ 12D state vectors.
2. **Calculate Stability**: Use the HIHO stability metric (target 0.5) to monitor the precipitation region.
3. **Detect Loop**: If the distance between states remains below a threshold $\epsilon$ for $M$ steps, or homology detects a cycle, trigger `TopologicalRegime.PIVOT`.
4. **Execute Pivot**:
   - Set action selection score to `Novelty * 2.0`.
   - Set stability influence to `0.0`.
   - Force the agent to select the action that maximizes distance from all points in the history window.

## VERSION
v1.0

## SEE ALSO
- MANIFOLD_NAVIGATION_PRIME.md
- HIHO_STABILITY_PRIME.md
