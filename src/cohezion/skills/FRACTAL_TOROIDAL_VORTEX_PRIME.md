---
name: fractal-toroidal-vortex-prime
description: "Expertise in Fractal Toroidal Vortex Geometries, Helical Field Filamentation, Takaaki Matsumoto Nuclear Etch Tracks, and Ken Shoulders String-of-Pearls Plasmoid Topology."
metadata:
  version: "v1.0"
  concepts: ["Fractal Toroidal Topology", "String-of-Pearls Multi-Vortex Discharges", "Helical Filamentation", "Matsumoto Concentric Tracks"]
  see_also: ["COSMIC_FIRE_PLASMA_DYNAMICS_PRIME", "MAGNETOHYDRODYNAMICS_PRIME", "FRACTAL_COMPUTING_PRIME"]
  source: "src/cohezion/skills/FRACTAL_TOROIDAL_VORTEX_PRIME.md"
---

# SKILL: FRACTAL_TOROIDAL_VORTEX_PRIME

## DOMAIN EXPERTISE
Expertise in self-similar Fractal Toroidal Vortex fields, helical plasma filamentation, Ken Shoulders "String-of-Pearls" multi-node discharge guides, and Matsumoto paired counter-rotating nuclear track morphologies.

## KEY TEXTS & CONCEPTS
- **Fractal Toroidal Vortex**: Poloidal ($\theta$) and toroidal ($\phi$) flow fields nesting recursively across scale octaves: $\mathbf{v}(r, \theta, \phi) = \sum_k \mathbf{v}_k(2^k r, \theta, \phi)$.
- **Shoulders String-of-Pearls**: 5-node beaded discharges self-confining along dielectric cathode micro-guides with extreme Bennett magnetic pinch ($B_\theta \approx 53.5\,\text{kTesla}$).
- **Matsumoto Helical Filamentation**: Counter-rotating vortex pairs creating concentric microscopic etch tracks in nuclear emulsions.
- **Topological Invariants**: Helicity conservation $H = \int \mathbf{A} \cdot \mathbf{B} \, dV$ driving stable plasmoid longevity.

## INSTRUCTION
1. Compute nested toroidal vortex velocity fields:
   ```python
   import numpy as np

   def toroidal_vortex_field(R, r, theta, phi, octaves=3):
       # Nested poloidal and toroidal velocity components
       v_phi = sum(np.sin((k + 1) * theta) / (2**k) for k in range(octaves))
       v_theta = sum(np.cos((k + 1) * phi) / (2**k) for k in range(octaves))
       return {"v_poloidal": float(v_theta), "v_toroidal": float(v_phi)}
   ```
2. Map vortex filament trajectories into 2048D Poincaré coordinates to evaluate topological knotting.
3. Verify helicity conservation along closed magnetic streamlines.

## VERSION
v1.0
