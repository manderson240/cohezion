---
name: neural-cellular-automata-prime
description: "Expertise in Neural Cellular Automata (NCA), Neural Particle Automata (NPA, 2026), morphogenetic self-healing, BraiNCA dynamic attention routing, and class-conditional self-repairing agent manifolds."
metadata:
  version: "v1.0"
  concepts: ["Neural Cellular Automata (NCA)", "Neural Particle Automata (NPA)", "Morphogenetic Self-Healing", "BraiNCA Attention Routing", "Growing NCA (GNCA)"]
  see_also: ["FRACTAL_COMPUTING_PRIME", "BIOELECTRIC_SWARM_PRIME", "HIHO_STABILITY_PRIME"]
  source: "src/cohezion/skills/NEURAL_CELLULAR_AUTOMATA_PRIME.md"
---

# SKILL: NEURAL_CELLULAR_AUTOMATA_PRIME

## DOMAIN EXPERTISE
Expertise in Neural Cellular Automata (NCA) and Lagrangian Neural Particle Automata (NPA). Enables decentralized self-organizing agent swarms that grow complex spatial topologies from a single seed and autonomously self-heal when up to 80% of node states are damaged or corrupted.

## KEY TEXTS & CONCEPTS
- **Growing Neural Cellular Automata (GNCA)**: Local update rule $s_{i}^{(t+1)} = s_{i}^{(t)} + \Delta s_i$, where $\Delta s_i = \text{NN}(\text{Perception}(s_{\mathcal{N}(i)}))$.
- **Neural Particle Automata (NPA, 2026)**: Lagrangian particle-based generalization using Smoothed Particle Hydrodynamics (SPH), removing fixed grid constraints.
- **BraiNCA (2026)**: Integrating long-range attention layers to dynamically route information across distant cell clusters, enhancing damage tolerance.
- **Functional Internal Fluctuations**: Utilizing non-equilibrium state fluctuations to drive dynamic self-repair rather than damping them as noise.

## INSTRUCTION
1. Define the decentralized NCA local perception filter (Sobel / Laplacian):
   ```python
   import numpy as np

   def nca_local_step(cell_grid, update_weights):
       # Local perception kernel
       dx = np.gradient(cell_grid, axis=0)
       dy = np.gradient(cell_grid, axis=1)
       perception = np.stack([cell_grid, dx, dy], axis=-1)
       # Lightweight feedforward update
       delta = np.tanh(perception @ update_weights)
       # Stochastic mask to enforce asynchronous updates
       mask = (np.random.rand(*cell_grid.shape) < 0.5).astype(float)
       return cell_grid + delta * mask
   ```
2. Verify autonomous regeneration after simulated damage (e.g. zeroing out half the grid).
3. Map NCA state trajectories into 2048D Poincaré space to verify topological invariant preservation ($C = 0.50$).

## VERSION
v1.0
