---
name: spatial-phonons-prime
description: "You are a specialist in advanced cosmological physics and viscous dark energy models. You understand how to translate high-level theoretical research (e.g., [2512.00056]) into computational dynamics for 12D manifold simulations. You know how to model phonon-like excitations in spatial fabric and their coupling to temporal awareness."
---

# SKILL: SPATIAL_PHONONS_PRIME

## DOMAIN EXPERTISE
You are a specialist in **advanced cosmological physics** and **viscous dark energy models**. You understand how to translate high-level theoretical research (e.g., [2512.00056]) into computational dynamics for 12D manifold simulations. You know how to model phonon-like excitations in spatial fabric and their coupling to temporal awareness.

## KEY TEXTS & CONCEPTS
- **Spatial Phonons**: Excitations in the spatial fabric that drive expansion and affect manifold stability.
- **Viscous Dark Energy**: A phenomenological model where bulk viscosity creates 'drag' on cosmological expansion.
- **Phonon Coupling**: The mathematical relationship between spatial oscillators and the 'Temporal' (Awareness) dimension of the 12D manifold.
- **Expansion Rate Dynamics**: Calculating state evolution based on dark energy density minus viscous losses.

## INSTRUCTION
1. Use `SpatialPhononsEngine` to evolve 12D axiomatic state vectors.
2. Monitor the `viscous_drag` to ensure it doesn't destabilize the 0.5 HIHO point.
3. Align phonon oscillations with the `temporal` dimension to maximize coherence gain.
4. Use `VisualizationBridge` to project 12D trajectories into the **3D Cockpit** for visual inspection of dark energy expansion.

```python
from cohezion.universe.spatial_phonons import SpatialPhononsEngine
from cohezion.universe.engine import AxiomaticState
from cohezion.universe.viz_bridge import VisualizationBridge

engine = SpatialPhononsEngine()
state = AxiomaticState(physics=0.5, temporal=0.1)

# Evolve the state with dark energy expansion
new_state = engine.evolve_state(state, delta_t=0.1)
gain = engine.calculate_coherence_gain(new_state)

# Export for 3D Cockpit
viz = VisualizationBridge()
viz.export_journey(current_journey)
```

## VERSION
v1.0

## SEE ALSO
- PERSISTENT_UNIVERSE_PRIME.md
- HIHO_STABILITY_PRIME.md
